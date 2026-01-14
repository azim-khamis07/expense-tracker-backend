"""Unit tests for reports service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.report_job import ReportJob
from app.modules.reports.schemas import (
    ReportFormat,
    ReportRequest,
    ReportResponse,
    ReportStatus,
    ReportType,
)
from app.modules.reports.service import ReportService


class TestReportService:
    """Test reports service methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create reports service instance."""
        return ReportService(mock_db)

    @pytest.mark.asyncio
    async def test_request_report_success(self, service, mock_db):
        """Test successful report request."""
        mock_report_job = ReportJob(
            id="job123",
            user_id="user123",
            status=ReportStatus.PENDING,
            params_json=json.dumps(
                {
                    "report_type": "expense_summary",
                    "format": "pdf",
                    "start_date": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
                    "end_date": datetime(2024, 1, 31, tzinfo=UTC).isoformat(),
                }
            ),
            created_at=datetime.now(UTC),
        )

        service.repo.create = AsyncMock(return_value=mock_report_job)
        mock_db.commit = AsyncMock()

        with patch("app.modules.reports.service.generate_report_task.delay") as mock_task:
            request = ReportRequest(
                report_type=ReportType.EXPENSE_SUMMARY,
                format=ReportFormat.PDF,
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
            )

            result = await service.request_report("user123", request)

            assert isinstance(result, ReportResponse)
            assert result.id == "job123"
            mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_report_status_success(self, service):
        """Test getting report status."""
        mock_report_job = ReportJob(
            id="job123",
            user_id="user123",
            status=ReportStatus.COMPLETED,
            params_json=json.dumps(
                {
                    "report_type": "expense_summary",
                    "format": "pdf",
                }
            ),
            s3_key="reports/job123.pdf",
            created_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )

        service.repo.get_by_id = AsyncMock(return_value=mock_report_job)

        with patch("app.modules.reports.service.s3_client") as mock_s3:
            mock_s3.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/download"
            )

            result = await service.get_report_status("job123", "user123")

            assert isinstance(result, ReportResponse)
            assert result.id == "job123"
            assert result.status == ReportStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_report_status_not_found(self, service):
        """Test getting status for non-existent report."""
        service.repo.get_by_id = AsyncMock(return_value=None)

        result = await service.get_report_status("job123", "user123")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_reports(self, service):
        """Test listing user reports."""
        mock_report1 = ReportJob(
            id="job1",
            user_id="user123",
            status=ReportStatus.COMPLETED,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )

        mock_report2 = ReportJob(
            id="job2",
            user_id="user123",
            status=ReportStatus.PENDING,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )

        service.repo.get_all_by_user = AsyncMock(return_value=[mock_report1, mock_report2])

        with patch("app.modules.reports.service.s3_client") as mock_s3:
            mock_s3.generate_presigned_url = AsyncMock(return_value=None)

            result = await service.list_reports("user123", limit=10)

            assert len(result.items) == 2
            assert result.items[0].id == "job1"

    @pytest.mark.asyncio
    async def test_delete_report_success(self, service, mock_db):
        """Test successful report deletion."""
        mock_report_job = ReportJob(
            id="job123",
            user_id="user123",
            s3_key="reports/job123.pdf",
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )
        service.repo.get_by_id = AsyncMock(return_value=mock_report_job)
        service.repo.delete = AsyncMock(return_value=True)

        with patch("app.modules.reports.service.s3_client") as mock_s3:
            mock_s3.delete_file = AsyncMock(return_value=True)
            mock_db.commit = AsyncMock()

            result = await service.delete_report("job123", "user123")

            assert result is True
            mock_s3.delete_file.assert_called_once()
            service.repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_download_url_success(self, service):
        """Test getting download URL."""
        mock_report_job = ReportJob(
            id="job123",
            user_id="user123",
            status=ReportStatus.COMPLETED,
            s3_key="reports/job123.pdf",
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )
        service.repo.get_by_id = AsyncMock(return_value=mock_report_job)

        with patch("app.modules.reports.service.s3_client") as mock_s3:
            mock_s3.generate_presigned_url = AsyncMock(
                return_value="https://s3.example.com/download"
            )

            result = await service.get_report_download_url("job123", "user123")

            assert result == "https://s3.example.com/download"
            mock_s3.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_download_url_not_completed(self, service):
        """Test getting download URL for incomplete report."""
        mock_report_job = ReportJob(
            id="job123",
            user_id="user123",
            status=ReportStatus.PENDING,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )
        service.repo.get_by_id = AsyncMock(return_value=mock_report_job)

        result = await service.get_report_download_url("job123", "user123")

        assert result is None  # Returns None for incomplete reports
