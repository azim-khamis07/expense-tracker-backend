"""Unit tests for reports repository."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.report_job import ReportJob, ReportStatus
from app.modules.reports.repo import ReportRepository


@pytest.mark.unit
@pytest.mark.asyncio
class TestReportRepository:
    """Test reports repository methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_db):
        """Create reports repository instance."""
        return ReportRepository(mock_db)

    async def test_create(self, repo, mock_db):
        """Test creating a report job."""
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create job using the repo
        params_json = json.dumps({"report_type": "expense_summary"})
        job = await repo.create("user123", params_json)

        # Verify database operations were called
        assert job is not None
        mock_db.add.assert_called_once()
        assert isinstance(mock_db.add.call_args[0][0], ReportJob)
        assert mock_db.add.call_args[0][0].user_id == "user123"
        assert mock_db.add.call_args[0][0].params_json == params_json
        assert mock_db.add.call_args[0][0].status == ReportStatus.PENDING
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once()

    async def test_get_by_id_found(self, repo, mock_db):
        """Test getting report by ID when found."""
        mock_job = ReportJob(
            id="job123",
            user_id="user123",
            status=ReportStatus.PENDING,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id("job123", "user123")

        assert result == mock_job
        mock_db.execute.assert_called_once()

    async def test_get_by_id_not_found(self, repo, mock_db):
        """Test getting report by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id("job123", "user123")

        assert result is None
        mock_db.execute.assert_called_once()

    async def test_get_all_by_user(self, repo, mock_db):
        """Test listing user's reports."""
        mock_job1 = ReportJob(
            id="job1",
            user_id="user123",
            status=ReportStatus.COMPLETED,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )

        mock_job2 = ReportJob(
            id="job2",
            user_id="user123",
            status=ReportStatus.PENDING,
            params_json=json.dumps({"report_type": "expense_summary"}),
            created_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job1, mock_job2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_all_by_user("user123", limit=50)

        assert len(result) == 2
        assert result[0].id == "job1"
        assert result[1].id == "job2"
        mock_db.execute.assert_called_once()

    async def test_update_status(self, repo, mock_db):
        """Test updating report status."""
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())

        await repo.update_status(
            "job123",
            ReportStatus.COMPLETED,
            s3_key="reports/user123/job123.pdf",
            finished_at=datetime.now(UTC),
        )

        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_update_status_with_error(self, repo, mock_db):
        """Test updating report status with error message."""
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())

        await repo.update_status(
            "job123",
            ReportStatus.FAILED,
            error_message="Test error",
        )

        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_delete_found(self, repo, mock_db):
        """Test deleting report when found."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await repo.delete("job123", "user123")

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_delete_not_found(self, repo, mock_db):
        """Test deleting report when not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await repo.delete("job123", "user123")

        assert result is False
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()
