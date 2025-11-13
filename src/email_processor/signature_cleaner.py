"""Email signature and footer cleaning utilities"""

from copy import deepcopy
import re
from bs4 import BeautifulSoup
from typing import Optional


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
