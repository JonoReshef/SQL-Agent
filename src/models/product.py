"""Pydantic models for product data structures"""

from datetime import datetime
from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

QuoteContext = Literal[
    "quote_request",
    "price_request",
    "order",
    "inquiry",
    "rfi",
    "rfq",
    "purchase_order",
    "quote_response",
]

ValueTypes = Literal[
    "measurement",
    "description",
    "name",
    "other",
]


class ProductProperty(BaseModel):
    """A single property of a product"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "grade",
                "value": "8",
                "confidence": 0.95,
                "value_type": "measurement",
                "priority": 1,
            }
        }
    )

    name: str = Field(
        ..., description="Property name (e.g., 'grade', 'size', 'material')"
    )
    value_type: ValueTypes = Field(
        default="description",
        description="Property type (e.g., 'measurement', 'description')",
    )
    priority: int = Field(
        default=10,
        description="Priority for hierarchical filtering (lower = higher priority)",
    )
    value: str = Field(..., description="Property value")
    confidence: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0, description="Extraction confidence score"
    )


class ProductItem(BaseModel):
    """Base product item model"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exact_product_text": "100 pcs of grade 8 hex bolts",
                "product_id": "HB-12345",
                "product_name": "Hex Bolt",
                "product_category": "Fasteners",
                "properties": [
                    {
                        "name": "grade",
                        "value": "8",
                        "value_type": "measurement",
                        "confidence": 0.95,
                    },
                    {
                        "name": "size",
                        "value": "1/2-13",
                        "value_type": "measurement",
                        "confidence": 0.90,
                    },
                    {
                        "name": "material",
                        "value": "steel",
                        "value_type": "description",
                        "confidence": 1.0,
                    },
                ],
            }
        }
    )
    exact_product_text: str = Field(
        ..., description="The exact text which originally describes a product"
    )
    product_id: Optional[str | None] = Field(
        default=None, description="Optional unique identifier for the product"
    )
    product_name: str = Field(description="Name of the product")
    product_category: str = Field(description="Category of the product")
    properties: list[ProductProperty] = Field(
        default_factory=list, description="Product properties as key-value pairs"
    )


class ProductItemResult(ProductItem):
    items: List[ProductItem] = Field(
        default_factory=list, description="List of extracted products"
    )


class ProductExtractionItem(ProductItem):
    """Single product extraction from email"""

    # Get the example schema from the base ProductItem model (not a field)
    model_schema: ClassVar[dict] = ProductItem.model_config.get("json_schema_extra", {})  # type: ignore
    model_config_inherit: ClassVar[dict] = model_schema.get("example", {})

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                **model_config_inherit,
                "quantity": 100,
                "unit": "pcs",
                "context": "quote_request",
                "requestor": "john.doe@example.com",
                "date_requested": "2025-02-15",
            }
        }
    )

    quantity: Optional[float] = Field(None, description="Quantity mentioned")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    context: QuoteContext | str = Field(
        description="Context of the mention (e.g., quote_request, order). If not one of the predefined contexts, use 'other' and specify."
    )
    requestor: Optional[str] = Field(
        None,
        description="Person or entity requesting the product. Default to email address otherwise use any available PII.",
    )
    date_requested: Optional[str] = Field(
        None, description="Date mentioned in email related to the product request"
    )


class ProductExtractionResult(BaseModel):
    """Result of product extraction from an email"""

    products: List[ProductExtractionItem] = Field(
        default_factory=list, description="List of extracted products"
    )


class ProductMention(ProductExtractionItem):
    """A product mentioned in an email"""

    email_subject: str = Field(..., description="Subject of email containing mention")
    email_sender: str = Field(..., description="Sender of email")
    email_file: Optional[str] = Field(None, description="Source .msg file path")
    thread_hash: Optional[str] = Field(
        None, description="SHA256 hash of source email thread for unique identification"
    )


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
    people_involved: List[str] = Field(
        default_factory=list, description="All requestors who mentioned the product"
    )
    contexts: List[str] = Field(
        default_factory=list, description="All contexts mentioned"
    )
