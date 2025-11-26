"""Pydantic models for email data structures"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.utils.compute_content_hash import compute_content_hash


class EmailMetadata(BaseModel):
    """Email metadata extracted from .msg files"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "<123@example.com>",
                "subject": "RE: RFQ for Fasteners",
                "sender": "john@example.com",
                "recipients": ["sales@westbrand.ca"],
                "cc": [],
                "date": "2025-01-15T10:30:00",
            }
        }
    )

    message_id: Optional[str] = Field(None, description="Unique message identifier")
    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Email sender address")
    recipients: List[str] = Field(default_factory=list, description="List of recipient addresses")
    cc: Optional[List[str]] = Field(default_factory=list, description="CC recipients")
    date: Optional[datetime] = Field(None, description="Email sent date")


class Email(BaseModel):
    """Complete email representation"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metadata": {
                    "subject": "RFQ Request",
                    "sender": "customer@example.com",
                    "recipients": ["sales@westbrand.ca"],
                    "date": "2025-01-15T10:30:00",
                },
                "body": "Please quote 100 pcs of grade 8 bolts...",
                "cleaned_body": "Please quote 100 pcs of grade 8 bolts",
                "attachments": [],
                "file_path": "/path/to/email.msg",
                "thread_hash": "abc123...",
            }
        }
    )

    metadata: EmailMetadata = Field(..., description="Email metadata")
    body: str = Field(..., description="Raw email body text")
    cleaned_body: Optional[str] = Field(None, description="Body with signatures removed")
    attachments: List[str] = Field(default_factory=list, description="List of attachment filenames")
    file_path: Optional[str] = Field(None, description="Original .msg file path")
    thread_hash: str = Field(
        default="",
        description="SHA256 hash of the entire email thread content for unique identification",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_file_info(cls, data: Any) -> Any:
        """Add thread_hash if missing"""
        if "thread_hash" not in data:
            data["thread_hash"] = compute_content_hash(data)  # Just to validate the file exists

        return data
