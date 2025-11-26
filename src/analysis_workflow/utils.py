"""Email parsing from .msg files using extract-msg library"""

import logging
import re
from copy import deepcopy
from datetime import datetime
from email.utils import parsedate_to_datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Dict, List, Optional

import extract_msg
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.models.email import Email, EmailMetadata
from utils.compute_content_hash import compute_content_hash

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


def _read_msg_files_from_directory(msg_file: Path) -> Email | None:
    """
    Read all .msg files from a directory.

    Args:
        directory: Path to directory containing .msg files
        recursive: If True, search subdirectories recursively

    Returns:
        List of Email objects
    """
    try:
        email = read_msg_file(msg_file)
        email.cleaned_body = clean_signature(email.body)
        email.thread_hash = compute_content_hash(email)
    except Exception as e:
        print(f"Warning: Failed to read {msg_file}: {e}")
        return None
    return email


def read_msg_files_from_directory_batch(directory: Path, recursive: bool = False) -> List[Email]:
    """
    Read all .msg files from a directory in parallel.

    Args:
        directory: Path to directory containing .msg files
        recursive: If True, search subdirectories recursively
    Returns:
        List of Email objects
    """
    emails: Dict[str, Email] = {}

    # Get all .msg files
    if recursive:
        msg_files = list(directory.rglob("*.msg"))
    else:
        msg_files = list(directory.glob("*.msg"))

    try:
        # Use multiprocessing instead of threading
        num_workers = min(cpu_count() - 2, len(msg_files))

        with Pool(processes=num_workers) as pool:
            results = list(
                tqdm(
                    pool.imap(_read_msg_files_from_directory, msg_files),
                    total=len(msg_files),
                    desc="Processing emails",
                )
            )

        for email in results:
            if email is None:
                continue

            key = str(email.metadata.subject).lower().strip()

            # Avoid duplicates based on subject. Store the largest cleaned body.
            if emails.get(key) is None:
                emails[key] = email
            else:
                # Store the email with the longest body for duplicate subjects
                if len(email.cleaned_body or "") > len(emails[key].cleaned_body or ""):
                    emails[key] = email

    except Exception as e:
        # Log error but continue processing other files
        print(f"Warning: Failed: {e}")

    return list(emails.values())


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


def clean_signature(original_body: Optional[str]) -> str:
    """
    Clean email signatures, footers, and quoted text from email body.

    Args:
        body: Raw email body (may be HTML or plain text)

    Returns:
        Cleaned email body text
    """
    body = deepcopy(original_body)
    if not body:
        return ""

    # Strip HTML tags first if present
    if "<html" in body.lower() or "<body" in body.lower() or "<p>" in body.lower():
        body = strip_html_tags(body)

    # Remove common signature separators
    signature_patterns = [
        r"\n--+\s*\n.*",  # -- separator
        r"\n_{20,}.*",  # Long underscore lines
        r"\n=+\s*\n.*",  # Equals separator
        r"\n\*+\s*\n.*",  # Asterisk separator
    ]

    for pattern in signature_patterns:
        body = re.sub(pattern, "", body, flags=re.DOTALL)

    # Remove forwarded message headers
    body = re.sub(
        r"(-+\s*Forwarded message\s*-+.*?)(?=\n\n|\Z)",
        "",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove quoted reply text (lines starting with >)
    lines = body.split("\n")
    cleaned_lines = []
    in_quote = False

    for line in lines:
        stripped = line.strip()
        # Check if this is a quote line
        if stripped.startswith(">"):
            in_quote = True
            continue
        # Check for "On [date], [person] wrote:" pattern
        elif re.match(r"On .+? wrote:", stripped, re.IGNORECASE):
            in_quote = True
            continue
        # If we were in a quote and hit a non-quote line, reset
        elif in_quote and stripped:
            in_quote = False

        # Keep non-quote lines
        if not in_quote:
            cleaned_lines.append(line)

    body = "\n".join(cleaned_lines)

    # Clean up excessive whitespace
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = body.strip()

    return body


def strip_html_tags(html: str) -> str:
    """
    Strip HTML tags and return plain text.

    Args:
        html: HTML string

    Returns:
        Plain text content
    """
    if not html:
        return ""

    try:
        # Use BeautifulSoup to parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "head"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text
    except Exception:
        # Fallback to regex if BeautifulSoup fails
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def clean_email_body(body: Optional[str]) -> str:
    """
    Complete cleaning of email body - HTML stripping and signature removal.

    Args:
        body: Raw email body

    Returns:
        Cleaned plain text
    """
    return clean_signature(body)
