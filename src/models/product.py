"""Pydantic models for product data structures"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class ProductProperty(BaseModel):
    """A single property of a product"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "grade", "value": "8", "confidence": 0.95}
        }
    )

    name: str = Field(
        ..., description="Property name (e.g., 'grade', 'size', 'material')"
    )
    value: str = Field(..., description="Property value")
    confidence: float = Field(
        1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )


class ProductMention(BaseModel):
    """A product mentioned in an email"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Hex Bolt",
                "product_category": "Fasteners",
                "properties": [
                    {"name": "grade", "value": "8", "confidence": 0.95},
                    {"name": "size", "value": "1/2-13", "confidence": 0.90},
                ],
                "quantity": 100,
                "unit": "pcs",
                "context": "quote_request",
                "date_requested": "2025-01-20T00:00:00",
                "email_subject": "RFQ for Bolts",
                "email_sender": "customer@example.com",
                "email_date": "2025-01-15T10:30:00",
            }
        }
    )

    product_name: str = Field(..., description="Product name or identifier")
    product_category: str = Field(..., description="Product category/type")
    properties: List[ProductProperty] = Field(
        default_factory=list, description="Product properties"
    )
    quantity: Optional[int] = Field(None, description="Quantity mentioned")
    unit: Optional[str] = Field(None, description="Unit of measurement (pcs, kg, etc.)")
    context: str = Field(..., description="Context of mention (quote, order, inquiry)")
    date_requested: Optional[datetime] = Field(
        None, description="Date mentioned in email"
    )
    email_subject: str = Field(..., description="Subject of email containing mention")
    email_sender: str = Field(..., description="Sender of email")
    email_date: Optional[datetime] = Field(None, description="Date of email")
    email_file: Optional[str] = Field(None, description="Source .msg file path")


class ProductAnalytics(BaseModel):
    """Aggregated analytics for a product across multiple mentions"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Hex Bolt",
                "product_category": "Fasteners",
                "total_mentions": 5,
                "first_mention": "2025-01-15T10:30:00",
                "last_mention": "2025-02-10T14:20:00",
                "total_quantity": 500,
                "properties_summary": {
                    "grade": ["8", "5"],
                    "size": ["1/2-13", "3/4-10"],
                },
                "contexts": ["quote_request", "order", "inquiry"],
            }
        }
    )

    product_name: str = Field(..., description="Product name")
    product_category: str = Field(..., description="Product category")
    total_mentions: int = Field(..., description="Total number of mentions")
    first_mention: Optional[datetime] = Field(None, description="First time mentioned")
    last_mention: Optional[datetime] = Field(None, description="Most recent mention")
    total_quantity: Optional[int] = Field(None, description="Sum of all quantities")
    properties_summary: Dict[str, List[str]] = Field(
        default_factory=dict, description="Summary of properties with all unique values"
    )
    contexts: List[str] = Field(
        default_factory=list, description="All contexts mentioned"
    )
