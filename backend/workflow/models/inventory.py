"""Pydantic models for inventory data structures"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from workflow.models.product import ProductItem, ProductProperty


class InventoryItem(ProductItem):
    """Inventory item extending base ProductItem"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_number": "ITEM-12345",
                "raw_description": '1/2-13 x 2" Grade 8 Hex Bolt, Zinc Plated',
                "exact_product_text": '1/2-13 x 2" Grade 8 Hex Bolt',
                "product_name": "Hex Bolt",
                "product_category": "Fasteners",
                "properties": [
                    {"name": "grade", "value": "8", "confidence": 0.95},
                    {"name": "size", "value": "1/2-13", "confidence": 0.90},
                ],
                "parse_confidence": 0.92,
                "needs_manual_review": False,
            }
        }
    )

    item_number: str = Field(
        ..., description="Unique inventory item number from Excel"
    )  # NOTE this is a duplication of the product_id in ProductItem
    raw_description: str = Field(
        ..., description="Original description from Excel"
    )  # NOTE this is a duplication of the exact_product_text in ProductItem
    parse_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in parsed data"
    )
    needs_manual_review: bool = Field(
        default=False, description="Flag for low confidence or ambiguous parsing"
    )


class InventoryMatch(BaseModel):
    """A match between an email product and inventory item"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "inventory_item_number": "ITEM-12345",
                "inventory_description": '1/2-13 x 2" Grade 8 Hex Bolt',
                "match_score": 0.92,
                "rank": 1,
                "matched_properties": ["grade", "size", "length"],
                "missing_properties": ["finish"],
                "match_reasoning": "Exact match on grade, size, and length. Missing finish specification.",
            }
        }
    )

    inventory_item_number: str = Field(..., description="Matched inventory item number")
    inventory_description: str = Field(..., description="Inventory item description")
    inventory_properties: List[ProductProperty] = Field(
        default_factory=list, description="Inventory item properties"
    )
    match_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this match"
    )
    rank: int = Field(..., ge=1, description="Rank among all matches (1 = best)")
    matched_properties: List[str] = Field(
        default_factory=list, description="Properties that matched"
    )
    missing_properties: List[str] = Field(
        default_factory=list, description="Properties in email but not in inventory"
    )
    match_reasoning: str = Field(
        default="", description="Human-readable explanation of match"
    )


class ProductWithMatches(BaseModel):
    """Product mention with all its inventory matches"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_text": "100 pcs of 1/2-13 Grade 8 bolts",
                "product_name": "Hex Bolt",
                "product_category": "Fasteners",
                "matches": [],
                "needs_review": False,
                "review_reason": None,
            }
        }
    )

    product_text: str = Field(..., description="Original product text from email")
    product_name: str = Field(..., description="Normalized product name")
    product_category: str = Field(..., description="Product category")
    properties: List[ProductProperty] = Field(
        default_factory=list, description="Extracted properties"
    )
    matches: List[InventoryMatch] = Field(
        default_factory=list, description="All matches for this product"
    )
    needs_review: bool = Field(
        default=False, description="Flag if manual review needed"
    )
    review_reason: Optional[str] = Field(
        None, description="Reason why review is needed"
    )


class ReviewFlag(BaseModel):
    """Flag for products requiring manual review"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_text": "Grade 8 bolts",
                "issue_type": "INSUFFICIENT_DATA",
                "match_count": 0,
                "top_confidence": None,
                "reason": "Product has no size specification - cannot narrow down inventory matches",
                "action_needed": "Request clarification from customer about bolt size",
            }
        }
    )

    product_text: str = Field(..., description="Product text from email")
    product_name: str = Field(..., description="Product name")
    product_category: str = Field(..., description="Product category")
    issue_type: str = Field(
        ...,
        description="Type of issue: INSUFFICIENT_DATA, AMBIGUOUS_MATCH, LOW_CONFIDENCE, TOO_MANY_MATCHES",
    )
    match_count: int = Field(..., description="Number of matches found")
    top_confidence: Optional[float] = Field(
        None, description="Confidence of best match"
    )
    reason: str = Field(..., description="Detailed explanation of the issue")
    action_needed: str = Field(..., description="Recommended action")
