"""Unit tests for .msg file parsing using mail-parser"""

from datetime import datetime
from pathlib import Path

import pytest

from workflow.analysis_workflow.utils import (
    read_msg_file,
    read_msg_files_from_directory,
)
from workflow.models.email import Email, EmailMetadata


class TestMsgReader:
    """Test suite for .msg file parsing functionality"""

    @pytest.mark.unit
    def test_read_msg_file_basic_fields(self):
        """Test that basic email fields are extracted correctly"""
        # Test with actual .msg file from the data directory
        msg_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg"
        )

        if not msg_path.exists():
            pytest.skip(f"Test file not found: {msg_path}")

        email = read_msg_file(msg_path)

        # Verify basic structure
        assert isinstance(email, Email)
        assert isinstance(email.metadata, EmailMetadata)

        # Verify required fields are populated
        assert email.metadata.subject is not None
        assert len(email.metadata.subject) > 0
        assert email.metadata.sender is not None
        assert email.body is not None
        assert len(email.body) > 0
        assert email.file_path == str(msg_path)

    @pytest.mark.unit
    def test_read_msg_file_metadata_fields(self):
        """Test that metadata fields are extracted with correct types"""
        msg_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg"
        )

        if not msg_path.exists():
            pytest.skip(f"Test file not found: {msg_path}")

        email = read_msg_file(msg_path)

        # Check metadata types
        assert isinstance(email.metadata.subject, str)
        assert isinstance(email.metadata.sender, str)
        assert isinstance(email.metadata.recipients, list)

        # Check optional date field
        if email.metadata.date is not None:
            assert isinstance(email.metadata.date, datetime)

        # Check recipients list
        if len(email.metadata.recipients) > 0:
            assert all(isinstance(r, str) for r in email.metadata.recipients)

    @pytest.mark.unit
    def test_read_msg_file_body_extraction(self):
        """Test that email body is extracted and non-empty"""
        msg_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg"
        )

        if not msg_path.exists():
            pytest.skip(f"Test file not found: {msg_path}")

        email = read_msg_file(msg_path)

        # Body should be extracted
        assert email.body is not None
        assert len(email.body) > 0
        assert isinstance(email.body, str)

        # Body should contain some text content (not just whitespace)
        assert email.body.strip() != ""

    @pytest.mark.unit
    def test_read_msg_file_attachments(self):
        """Test that attachments list is present (empty or populated)"""
        msg_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg"
        )

        if not msg_path.exists():
            pytest.skip(f"Test file not found: {msg_path}")

        email = read_msg_file(msg_path)

        # Attachments should be a list
        assert isinstance(email.attachments, list)

        # If attachments exist, they should be strings
        if len(email.attachments) > 0:
            assert all(isinstance(a, str) for a in email.attachments)

    @pytest.mark.unit
    def test_read_msg_file_nonexistent(self):
        """Test handling of nonexistent file"""
        msg_path = Path("data/nonexistent_file.msg")

        with pytest.raises(FileNotFoundError):
            read_msg_file(msg_path)

    @pytest.mark.unit
    def test_read_msg_file_invalid_path_type(self):
        """Test handling of invalid path type"""
        with pytest.raises((TypeError, AttributeError)):
            read_msg_file(None)  # type: ignore

    @pytest.mark.unit
    def test_read_msg_files_from_directory(self):
        """Test reading multiple .msg files from a directory"""
        directory = Path("data/sales@westbrand.ca/Recoverable-Items/Deletions")

        if not directory.exists():
            pytest.skip(f"Test directory not found: {directory}")

        emails = read_msg_files_from_directory(directory)

        # Should return a list
        assert isinstance(emails, list)

        # Should find at least some .msg files
        msg_files = list(directory.glob("*.msg"))
        if len(msg_files) > 0:
            assert len(emails) > 0

            # All items should be Email objects
            assert all(isinstance(e, Email) for e in emails)

            # Each should have valid metadata
            for email in emails:
                assert email.metadata.subject is not None
                assert email.metadata.sender is not None
                assert email.body is not None

    @pytest.mark.unit
    def test_read_msg_files_recursive(self):
        """Test recursive reading of .msg files from nested directories"""
        base_directory = Path("data/sales@westbrand.ca")

        if not base_directory.exists():
            pytest.skip(f"Test directory not found: {base_directory}")

        emails = read_msg_files_from_directory(base_directory, recursive=True)

        # Should return a list
        assert isinstance(emails, list)

        # Count actual .msg files recursively
        msg_files = list(base_directory.rglob("*.msg"))
        if len(msg_files) > 0:
            assert len(emails) > 0
            # Should find emails from nested directories
            assert len(emails) <= len(msg_files)

    @pytest.mark.unit
    def test_read_msg_files_empty_directory(self):
        """Test reading from a directory with no .msg files"""
        directory = Path("output")  # This should have no .msg files

        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

        emails = read_msg_files_from_directory(directory)

        # Should return empty list, not error
        assert isinstance(emails, list)
        assert len(emails) == 0

    @pytest.mark.unit
    def test_email_pydantic_validation(self):
        """Test that parsed emails validate against Pydantic models"""
        msg_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg"
        )

        if not msg_path.exists():
            pytest.skip(f"Test file not found: {msg_path}")

        email = read_msg_file(msg_path)

        # Test serialization (validates model)
        email_dict = email.model_dump()
        assert isinstance(email_dict, dict)
        assert "metadata" in email_dict
        assert "body" in email_dict

        # Test deserialization
        email_restored = Email(**email_dict)
        assert email_restored.metadata.subject == email.metadata.subject
        assert email_restored.body == email.body

    @pytest.mark.unit
    def test_read_msg_file_forwards_and_replies(self):
        """Test handling of forwarded and reply emails"""
        # Test FW: prefix
        fw_path = Path("data/sales@westbrand.ca/Recoverable-Items/Deletions/FW RFQ.msg")
        if fw_path.exists():
            email = read_msg_file(fw_path)
            assert (
                "FW" in email.metadata.subject.upper()
                or "RE" in email.metadata.subject.upper()
            )

        # Test RE: prefix
        re_path = Path(
            "data/sales@westbrand.ca/Recoverable-Items/Deletions/RE Pricing.msg"
        )
        if re_path.exists():
            email = read_msg_file(re_path)
            assert (
                "RE" in email.metadata.subject.upper()
                or "FW" in email.metadata.subject.upper()
            )


class TestMsgReaderErrorHandling:
    """Test error handling in msg_reader"""

    @pytest.mark.unit
    def test_corrupted_msg_file(self):
        """Test handling of corrupted .msg file"""
        # Create a fake .msg file
        fake_msg = Path("tests/fixtures/corrupted.msg")
        fake_msg.parent.mkdir(parents=True, exist_ok=True)
        fake_msg.write_text("This is not a valid .msg file")

        try:
            with pytest.raises(Exception):  # Should raise some parsing error
                read_msg_file(fake_msg)
        finally:
            # Cleanup
            if fake_msg.exists():
                fake_msg.unlink()

    @pytest.mark.unit
    def test_directory_with_mixed_files(self):
        """Test that non-.msg files are ignored in directory reading"""
        test_dir = Path("tests/fixtures/mixed")
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create some non-.msg files
        (test_dir / "test.txt").write_text("Not an email")
        (test_dir / "data.json").write_text("{}")

        try:
            emails = read_msg_files_from_directory(test_dir)
            # Should return empty list, not error on non-.msg files
            assert isinstance(emails, list)
            assert len(emails) == 0
        finally:
            # Cleanup
            for f in test_dir.iterdir():
                f.unlink()
            test_dir.rmdir()
