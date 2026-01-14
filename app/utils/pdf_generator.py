"""PDF report generator utility with charts."""

from datetime import datetime
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import logging

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Generate PDF reports with charts."""

    def __init__(self, title: str, author: str = "Expense Tracker"):
        """
        Initialize PDF report generator.

        Args:
            title: Report title
            author: Report author (default: "Expense Tracker")
        """
        self.title = title
        self.author = author
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Setup custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2C3E50"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#34495E"),
                spaceAfter=12,
                spaceBefore=12,
            )
        )

    def generate_expense_summary(
        self,
        user_name: str,
        start_date: datetime,
        end_date: datetime,
        summary_data: dict,
        category_data: list[dict],
        transactions: list[dict],
    ) -> BytesIO:
        """
        Generate expense summary PDF.

        Args:
            user_name: Name of user
            start_date: Report start date
            end_date: Report end date
            summary_data: Summary statistics dict
            category_data: Category breakdown list
            transactions: Transaction list

        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
            title=self.title,
            author=self.author,
        )

        story = []

        # Title
        story.append(Paragraph(self.title, self.styles["CustomTitle"]))
        story.append(Spacer(1, 0.2 * inch))

        # Period and user info
        period_text = (
            f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        )
        story.append(Paragraph(period_text, self.styles["Normal"]))
        story.append(Paragraph(f"Generated for: {user_name}", self.styles["Normal"]))
        story.append(
            Paragraph(
                f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

        # Summary section
        story.append(Paragraph("Financial Summary", self.styles["SectionHeader"]))
        summary_table_data = [
            ["Metric", "Amount"],
            ["Total Income", f"${summary_data.get('total_income', 0):.2f}"],
            ["Total Expenses", f"${summary_data.get('total_expenses', 0):.2f}"],
            ["Net Balance", f"${summary_data.get('net_balance', 0):.2f}"],
            ["Transaction Count", str(summary_data.get("transaction_count", 0))],
        ]
        summary_table = Table(summary_table_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498DB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 0.4 * inch))

        # Category breakdown chart
        if category_data:
            story.append(Paragraph("Expenses by Category", self.styles["SectionHeader"]))
            chart_img = self._create_pie_chart(category_data)
            if chart_img:
                story.append(chart_img)
                story.append(Spacer(1, 0.3 * inch))

        # Category table
        if category_data:
            category_table_data = [["Category", "Amount", "Percentage"]]
            for cat in category_data:
                category_table_data.append(
                    [
                        cat["name"],
                        f"${float(cat['amount']):.2f}",
                        f"{float(cat.get('percentage', 0)):.1f}%",
                    ]
                )

            cat_table = Table(category_table_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E74C3C")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(cat_table)
            story.append(PageBreak())

        # Recent transactions
        if transactions:
            story.append(Paragraph("Recent Transactions", self.styles["SectionHeader"]))
            trans_table_data = [["Date", "Description", "Category", "Amount"]]
            for trans in transactions[:50]:  # Limit to 50
                trans_date = trans["date"]
                if isinstance(trans_date, datetime):
                    date_str = trans_date.strftime("%m/%d")
                else:
                    date_str = str(trans_date)[:10]

                trans_table_data.append(
                    [
                        date_str,
                        str(trans["description"])[:30],
                        str(trans.get("category", "N/A"))[:20],
                        f"${float(trans['amount']):.2f}",
                    ]
                )

            trans_table = Table(
                trans_table_data, colWidths=[0.8 * inch, 2.5 * inch, 1.5 * inch, 1 * inch]
            )
            trans_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#9B59B6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.lavender),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(trans_table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_pie_chart(self, category_data: list[dict]) -> Image | None:
        """
        Create pie chart for category breakdown.

        Args:
            category_data: Category data list with 'name' and 'amount' keys

        Returns:
            ReportLab Image object or None if generation fails
        """
        try:
            fig, ax = plt.subplots(figsize=(6, 6))
            labels = [cat["name"] for cat in category_data[:10]]  # Top 10
            sizes = [float(cat["amount"]) for cat in category_data[:10]]
            colors_list = plt.cm.Set3.colors

            ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors_list)
            ax.axis("equal")

            # Save to buffer
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
            img_buffer.seek(0)
            plt.close(fig)

            return Image(img_buffer, width=4 * inch, height=4 * inch)
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return None
