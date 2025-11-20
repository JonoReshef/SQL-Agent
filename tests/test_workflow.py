"""Tests for LangGraph workflow nodes"""

from pathlib import Path
from unittest.mock import patch

from src.analysis_workflow.nodes.extraction.extraction import extract_products
from src.analysis_workflow.nodes.ingestion.ingestion import ingest_emails
from src.analysis_workflow.nodes.reporting.reporting import generate_report
from src.models.analysis_workflow import WorkflowState
from src.models.email import Email, EmailMetadata
from src.models.product import ProductMention, ProductProperty


class TestIngestionNode:
    """Test email ingestion workflow node"""

    def test_ingest_emails_basic(self, tmp_path):
        """Test basic email ingestion from directory"""
        # Create a sample state with directory path
        state = WorkflowState(
            input_directory=str(tmp_path),
        )

        # Mock the msg reader to return sample emails
        with patch(
            "src.analysis_workflow.nodes.ingestion.read_msg_files_from_directory"
        ) as mock_read:
            sample_email = Email(
                metadata=EmailMetadata(
                    message_id=None,
                    subject="Test Subject",
                    sender="test@example.com",
                    recipients=["recipient@example.com"],
                    date=None,
                ),
                body="Test body content",
                cleaned_body="Test body content",
                attachments=[],
                file_path=str(tmp_path / "test.msg"),
            )
            mock_read.return_value = [sample_email]

            # Execute ingestion node
            result = ingest_emails(state)

            # Verify emails were loaded
            assert len(result.emails) == 1
            assert result.emails[0].metadata.subject == "Test Subject"
            assert len(result.errors) == 0

    def test_ingest_emails_with_cleaning(self, tmp_path):
        """Test ingestion applies signature cleaning"""
        state = WorkflowState(
            input_directory=str(tmp_path),
        )

        with patch(
            "src.analysis_workflow.nodes.ingestion.read_msg_files_from_directory"
        ) as mock_read:
            email_with_signature = Email(
                metadata=EmailMetadata(
                    message_id=None,
                    subject="Test",
                    sender="test@example.com",
                    recipients=[],
                    date=None,
                ),
                body="Main content\n--\nSignature here",
                cleaned_body="",
                attachments=[],
                file_path=str(tmp_path / "test.msg"),
            )
            mock_read.return_value = [email_with_signature]

            result = ingest_emails(state)

            # Verify cleaned_body was updated
            assert result.emails[0].cleaned_body == "Main content"

    def test_ingest_emails_handles_errors(self, tmp_path):
        """Test ingestion captures errors gracefully"""
        state = WorkflowState(
            input_directory=str(tmp_path),
        )

        with patch(
            "src.analysis_workflow.nodes.ingestion.read_msg_files_from_directory"
        ) as mock_read:
            mock_read.side_effect = Exception("Failed to read directory")

            result = ingest_emails(state)

            # Verify error was captured
            assert len(result.errors) == 1
            assert "Failed to read directory" in result.errors[0]
            assert len(result.emails) == 0


class TestExtractionNode:
    """Test product extraction workflow node"""

    def test_extract_products_basic(self):
        """Test basic product extraction from emails"""
        sample_email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Product Quote",
                sender="sales@example.com",
                recipients=[],
                date=None,
            ),
            body="Need 100 pcs of M10 bolts",
            cleaned_body="Need 100 pcs of M10 bolts",
            attachments=[],
            file_path="/test/email.msg",
        )

        state = WorkflowState(
            emails=[sample_email],
        )

        with patch("src.analysis_workflow.nodes.extraction.extract_products_batch") as mock_extract:
            sample_product = ProductMention(
                exact_product_text="100 pcs of M10 bolts",
                product_name="M10 Bolt",
                product_category="Fasteners",
                properties=[ProductProperty(name="size", value="M10", confidence=0.9)],
                quantity=100.0,
                unit="pcs",
                context="quote_request",
                requestor="sales@example.com",
                date_requested=None,
                email_subject="Product Quote",
                email_sender="sales@example.com",
                email_date=None,
                email_file="/test/email.msg",
            )
            mock_extract.return_value = [sample_product]

            result = extract_products(state)

            # Verify products were extracted
            assert len(result.extracted_products) == 1
            assert result.extracted_products[0].product_name == "M10 Bolt"

    def test_extract_products_handles_errors(self):
        """Test extraction captures LLM errors"""
        sample_email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Test",
                sender="test@example.com",
                recipients=[],
                date=None,
            ),
            body="Test body",
            cleaned_body="Test body",
            attachments=[],
            file_path="/test/email.msg",
        )

        state = WorkflowState(
            emails=[sample_email],
        )

        with patch("src.analysis_workflow.nodes.extraction.extract_products_batch") as mock_extract:
            mock_extract.side_effect = Exception("LLM API error")

            result = extract_products(state)

            # Verify error was captured
            assert len(result.errors) == 1
            assert "LLM API error" in result.errors[0]


class TestReportingNode:
    """Test Excel report generation workflow node"""

    def test_generate_report_basic(self, tmp_path):
        """Test basic report generation"""
        sample_product = ProductMention(
            exact_product_text="100 pcs of M10 bolts",
            product_name="M10 Bolt",
            product_category="Fasteners",
            properties=[],
            quantity=100.0,
            unit="pcs",
            context="quote_request",
            requestor="test@example.com",
            date_requested=None,
            email_subject="Test",
            email_sender="test@example.com",
            email_date=None,
            email_file="/test/email.msg",
        )

        sample_email = Email(
            metadata=EmailMetadata(
                message_id=None,
                subject="Test",
                sender="test@example.com",
                recipients=[],
                date=None,
            ),
            body="Test",
            cleaned_body="Test",
            attachments=[],
            file_path="/test/email.msg",
        )

        state = WorkflowState(
            emails=[sample_email],
            extracted_products=[sample_product],
            report_path=str(tmp_path / "report.xlsx"),
        )

        result = generate_report(state)

        # Verify report path is set
        assert result.report_path != ""
        assert Path(result.report_path).exists()

    def test_generate_report_handles_errors(self, tmp_path):
        """Test reporting captures generation errors"""
        state = WorkflowState(
            report_path=str(tmp_path / "report.xlsx"),
        )

        with patch("src.analysis_workflow.nodes.reporting.generate_excel_report") as mock_generate:
            mock_generate.side_effect = Exception("Excel generation failed")

            result = generate_report(state)

            # Verify error was captured
            assert len(result.errors) == 1
            assert "Excel generation failed" in result.errors[0]
