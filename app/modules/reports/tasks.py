"""Celery tasks for async report generation."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.infra.celery_app import celery_app
from app.infra.s3 import s3_client
from app.models.report_job import ReportStatus
from app.modules.analytics.repo import AnalyticsRepository
from app.modules.reports.repo import ReportRepository
from app.modules.transactions.repo import TransactionRepository
from app.utils.pdf_generator import PDFReportGenerator

logger = logging.getLogger(__name__)

# Per-worker database engine (created lazily)
_async_engine = None
_AsyncSessionLocal = None


def get_async_session():
    """Get async session factory, creating engine if needed."""
    global _async_engine, _AsyncSessionLocal

    if _async_engine is None:
        # Create engine per worker process
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _AsyncSessionLocal = sessionmaker(
            _async_engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Created async database engine for Celery worker")

    return _AsyncSessionLocal


class ReportTask(Task):
    """Base task with error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure.

        Note: We don't mark as failed here because the exception handler
        in _generate_report_async already handles this. This is just for logging.
        """
        job_id = args[0] if args else None
        if job_id:
            logger.error(f"Report task {job_id} failed: {exc}", exc_info=einfo)


@celery_app.task(base=ReportTask, bind=True, max_retries=3)
def generate_report_task(self, job_id: str, user_id: str, params_json: str):
    """
    Generate report (async wrapper).

    Args:
        job_id: Report job ID
        user_id: User ID
        params_json: JSON string of report parameters
    """
    return asyncio.run(_generate_report_async(self, job_id, user_id, params_json))


async def _generate_report_async(task, job_id: str, user_id: str, params_json: str):
    """Async report generation logic."""
    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as session:
        report_repo = ReportRepository(session)
        trans_repo = TransactionRepository(session)
        analytics_repo = AnalyticsRepository(session)

        # Update status to processing
        await report_repo.update_status(
            job_id, ReportStatus.PROCESSING, started_at=datetime.now(UTC)
        )
        await session.commit()

        try:
            # Parse parameters
            params = json.loads(params_json)
            report_type = params.get("report_type")
            start_date_str = params.get("start_date")
            end_date_str = params.get("end_date")

            # Parse dates
            if isinstance(start_date_str, str):
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            else:
                start_date = datetime.fromisoformat(start_date_str)

            if isinstance(end_date_str, str):
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            else:
                end_date = datetime.fromisoformat(end_date_str)

            logger.info(f"Generating report {job_id} for user {user_id}")

            # Fetch category breakdown data
            category_breakdown = await analytics_repo.get_category_breakdown(
                user_id, start_date, end_date, transaction_type=None
            )

            # Fetch transactions (use repository to ensure proper eager loading)
            transactions, _, _ = await trans_repo.list_with_filters(
                user_id=user_id, start_date=start_date, end_date=end_date, limit=1000
            )

            # Prepare summary data
            total_income = sum(
                float(item.get("amount", 0))
                for item in category_breakdown
                if item.get("type") == "income"
            )
            total_expense = sum(
                float(item.get("amount", 0))
                for item in category_breakdown
                if item.get("type") == "expense"
            )
            net_balance = total_income - total_expense

            summary_data = {
                "total_income": total_income,
                "total_expenses": total_expense,
                "net_balance": net_balance,
                "transaction_count": len(transactions),
            }

            # Prepare category data (expenses only)
            expense_categories = [
                item
                for item in category_breakdown
                if item.get("type") == "expense" and float(item.get("amount", 0)) > 0
            ]
            total_expense_amount = sum(float(cat.get("amount", 0)) for cat in expense_categories)

            category_data = []
            for cat in expense_categories:
                amount = float(cat.get("amount", 0))
                percentage = (
                    (amount / total_expense_amount * 100) if total_expense_amount > 0 else 0
                )
                category_data.append(
                    {
                        "name": cat.get("category_name", "Uncategorized"),
                        "amount": amount,
                        "percentage": percentage,
                    }
                )

            # Sort by amount descending
            category_data.sort(key=lambda x: x["amount"], reverse=True)

            # Prepare transaction data
            # Access all relationship data while still in session context
            # This is critical: we must access relationships while the session is active
            trans_data = []
            for trans in transactions[:100]:  # Limit to 100 for PDF
                # Access category name while session is still active
                # joinedload should have loaded it, but we access it explicitly here
                # to ensure it's available and prevent lazy loading errors
                try:
                    category_name = trans.category.name if trans.category else None
                except Exception as e:
                    # If lazy loading fails, log and continue
                    logger.warning(f"Could not access category for transaction {trans.id}: {e}")
                    category_name = None

                trans_data.append(
                    {
                        "date": trans.occurred_at,
                        "description": trans.description or "",
                        "category": category_name,
                        "amount": float(trans.amount),
                    }
                )

            # Generate PDF
            logger.info(f"Generating PDF for report {job_id}")
            generator = PDFReportGenerator(title="Expense Summary Report", author="Expense Tracker")

            pdf_buffer = generator.generate_expense_summary(
                user_name=f"User {user_id}",
                start_date=start_date,
                end_date=end_date,
                summary_data=summary_data,
                category_data=category_data,
                transactions=trans_data,
            )

            # Upload to S3
            file_key = f"reports/{user_id}/{job_id}.pdf"
            pdf_bytes = pdf_buffer.getvalue()
            file_size = len(pdf_bytes)

            logger.info(f"Uploading PDF to S3: {file_key}")
            import io

            pdf_file_obj = io.BytesIO(pdf_bytes)
            upload_success = await s3_client.upload_file(
                pdf_file_obj,
                file_key,
                "application/pdf",
                metadata={
                    "report_type": report_type or "expense_summary",
                    "user_id": user_id,
                    "job_id": job_id,
                },
            )

            if not upload_success:
                raise Exception("Failed to upload PDF to S3")

            # Mark as completed
            await report_repo.update_status(
                job_id,
                ReportStatus.COMPLETED,
                s3_key=file_key,
                finished_at=datetime.now(UTC),
            )
            await session.commit()

            logger.info(f"Report {job_id} completed successfully")

            return {
                "job_id": job_id,
                "status": "completed",
                "s3_key": file_key,
                "file_size": file_size,
            }

        except Exception as e:
            logger.error(f"Report generation failed for {job_id}: {e}", exc_info=True)
            await report_repo.update_status(
                job_id,
                ReportStatus.FAILED,
                error_message=str(e),
                finished_at=datetime.now(UTC),
            )
            await session.commit()
            raise
