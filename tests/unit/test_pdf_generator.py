"""Unit tests for PDF generator."""

from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.utils.pdf_generator import PDFReportGenerator


class TestPDFReportGenerator:
    """Test PDF generator utility."""

    @pytest.fixture
    def generator(self):
        """Create PDF generator instance."""
        return PDFReportGenerator(title="Test Report", author="Test Author")

    def test_generate_expense_summary(self, generator):
        """Test generating expense summary report."""
        summary_data = {
            "total_income": Decimal("5000.00"),
            "total_expenses": Decimal("2000.00"),  # Note: total_expenses not total_expense
            "net_balance": Decimal("3000.00"),  # Note: net_balance not net
            "transaction_count": 25,
        }

        category_data = [
            {"name": "Food", "amount": Decimal("500.00"), "percentage": 25.0},
            {"name": "Transport", "amount": Decimal("300.00"), "percentage": 15.0},
        ]

        transactions = [
            {
                "description": "Grocery shopping",
                "amount": Decimal("100.00"),
                "type": "expense",
                "category": "Food",
                "date": datetime(2024, 1, 15, tzinfo=UTC),  # Note: date not occurred_at
            }
        ]

        result = generator.generate_expense_summary(
            user_name="Test User",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            summary_data=summary_data,
            category_data=category_data,
            transactions=transactions,
        )

        assert isinstance(result, BytesIO)
        # Check buffer size (PDF should be at least a few KB)
        result.seek(0, 2)  # Seek to end
        size = result.tell()
        assert size > 0  # File was written
        result.seek(0)
        content = result.read()
        assert b"PDF" in content[:10]  # PDF magic bytes

    def test_generate_expense_summary_empty_data(self, generator):
        """Test generating report with empty data."""
        summary_data = {
            "total_income": Decimal("0.00"),
            "total_expenses": Decimal("0.00"),
            "net_balance": Decimal("0.00"),
            "transaction_count": 0,
        }

        result = generator.generate_expense_summary(
            user_name="Test User",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            summary_data=summary_data,
            category_data=[],
            transactions=[],
        )

        # Check buffer size
        result.seek(0, 2)  # Seek to end
        size = result.tell()
        assert size > 0  # Should still generate PDF even with empty data

    def test_custom_styles_setup(self, generator):
        """Test that custom styles are set up correctly."""
        assert "CustomTitle" in generator.styles.byName
        assert "SectionHeader" in generator.styles.byName

    def test_generate_with_charts(self, generator):
        """Test generating report with charts."""
        summary_data = {
            "total_income": Decimal("5000.00"),
            "total_expenses": Decimal("2000.00"),
            "net_balance": Decimal("3000.00"),
            "transaction_count": 25,
        }

        category_data = [
            {"name": "Food", "amount": Decimal("500.00"), "percentage": 25.0},
            {"name": "Transport", "amount": Decimal("300.00"), "percentage": 15.0},
        ]

        with patch("app.utils.pdf_generator.plt") as mock_plt:
            mock_fig = MagicMock()
            mock_plt.figure.return_value = mock_fig
            mock_plt.savefig = MagicMock()

            result = generator.generate_expense_summary(
                user_name="Test User",
                start_date=datetime(2024, 1, 1, tzinfo=UTC),
                end_date=datetime(2024, 1, 31, tzinfo=UTC),
                summary_data=summary_data,
                category_data=category_data,
                transactions=[],
            )

            # Should still generate PDF
            result.seek(0, 2)  # Seek to end
            size = result.tell()
            assert size > 0
