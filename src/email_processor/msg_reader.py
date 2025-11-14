"""Email parsing from .msg files using extract-msg library"""

import extract_msg
from pathlib import Path
from typing import List
from datetime import datetime

from tqdm import tqdm
from src.models.email import Email, EmailMetadata
from email.utils import parsedate_to_datetime
import logging

# Suppress INFO messages from extract_msg
logging.getLogger("extract_msg").setLevel(logging.ERROR)


def read_msg_file(file_path: Path) -> Email:
    """
    Read and parse a single .msg file.

    Args:
        file_path: Path to the .msg file

    Returns:
        Email object with parsed content

    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If the file cannot be parsed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Parse the .msg file using extract-msg
    msg = extract_msg.Message(str(file_path), skip_attachments=False)

    # Extract metadata
    metadata = EmailMetadata(
        message_id=msg.messageId,
        subject=msg.subject or "",
        sender=msg.sender or "",
        recipients=_extract_recipients(msg.to),
        cc=_extract_recipients(msg.cc) if msg.cc else [],
        date=_parse_email_date(msg.date),
    )

    # Extract body (try multiple formats)
    body = ""
    if msg.body:
        body = msg.body
    elif hasattr(msg, "htmlBody") and msg.htmlBody:
        # If HTML body exists, use it (will be cleaned later)
        body = msg.htmlBody
    elif hasattr(msg, "rtfBody") and msg.rtfBody:
        # Try to extract from RTF if available
        try:
            # extract-msg may have rtfBody, but it's complex to parse
            # For now, use whatever text we can get
            body = str(msg.rtfBody) if msg.rtfBody else ""
        except Exception:
            body = ""

    # If still no body, try getting it from the string representation
    if not body:
        body_str = str(msg)
        if body_str and body_str != str(msg.subject):
            body = body_str

    # Ensure body is a string (handle bytes/bytearray)
    if isinstance(body, (bytes, bytearray, memoryview)):
        try:
            body = bytes(body).decode("utf-8", errors="ignore")
        except Exception:
            body = str(body)

    # Ensure it's a string
    body = str(body) if body else ""

    # Extract attachment names
    attachments = []
    if msg.attachments:
        attachments = [
            att.longFilename or att.shortFilename or ""
            for att in msg.attachments
            if att.longFilename or att.shortFilename
        ]

    # Close the message
    msg.close()

    return Email(
        metadata=metadata,
        body=body,
        cleaned_body=None,  # Will be populated by signature cleaner
        attachments=attachments,
        file_path=str(file_path),
    )


def read_msg_files_from_directory(
    directory: Path, recursive: bool = False
) -> List[Email]:
    """
    Read all .msg files from a directory.

    Args:
        directory: Path to directory containing .msg files
        recursive: If True, search subdirectories recursively

    Returns:
        List of Email objects
    """
    emails = []

    # Get all .msg files
    if recursive:
        msg_files = list(directory.rglob("*.msg"))[:50]
    else:
        msg_files = list(directory.glob("*.msg"))

    for msg_file in tqdm(
        msg_files,
        desc="Reading .msg files",
    ):
        try:
            email = read_msg_file(msg_file)
            emails.append(email)
        except Exception as e:
            # Log error but continue processing other files
            print(f"Warning: Failed to parse {msg_file}: {e}")
            continue

    return emails


def _parse_email_date(date_value) -> datetime | None:
    """
    Parse email date from various formats.

    Args:
        date_value: Date value from extract-msg (can be datetime, string, or None)

    Returns:
        datetime object or None
    """
    if date_value is None:
        return None

    if isinstance(date_value, datetime):
        return date_value

    # If it's a string, try to parse it
    if isinstance(date_value, str):
        try:
            return parsedate_to_datetime(date_value)
        except Exception:
            return None

    return None


def _extract_recipients(recipient_string: str | None) -> List[str]:
    """
    Extract recipient email addresses from string.

    Args:
        recipient_string: Semicolon or comma separated email addresses

    Returns:
        List of email addresses
    """
    if not recipient_string:
        return []

    # Split by semicolon or comma
    recipients = []
    for part in recipient_string.replace(";", ",").split(","):
        part = part.strip()
        if part:
            # Extract email from "Name <email>" format if present
            if "<" in part and ">" in part:
                email = part[part.index("<") + 1 : part.index(">")]
                recipients.append(email)
            else:
                recipients.append(part)

    return recipients
