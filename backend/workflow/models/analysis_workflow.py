"""LangGraph workflow state models"""

from typing import Dict, List

from pydantic import BaseModel, Field

from workflow.models.email import Email
from workflow.models.inventory import InventoryItem, InventoryMatch, ReviewFlag
from workflow.models.product import ProductAnalytics, ProductMention


class WorkflowState(BaseModel):
    """
    State for the email analysis workflow.

    This Pydantic model is used by LangGraph to track state across workflow nodes.
    """

    # Input directory containing .msg files
    input_directory: str = Field(
        default="data/selected",
        description="Directory containing .msg files to analyze",
    )

    # Input data
    emails: List[Email] = Field(default_factory=list)

    # Processing results
    extracted_products: List[ProductMention] = Field(default_factory=list)
    unique_property_products: List[ProductMention] = Field(default_factory=list)

    # Analytics
    analytics: List[ProductAnalytics] = Field(default_factory=list)

    # Inventory matching (new fields for Stage 5)
    inventory_items: List[InventoryItem] = Field(
        default_factory=list,
        description="Loaded inventory items from database",
    )

    product_matches: Dict[str, List[InventoryMatch]] = Field(
        default_factory=dict,
        description="Matches for each product (keyed by product exact_product_text)",
    )

    review_flags: List[ReviewFlag] = Field(
        default_factory=list,
        description="Products flagged for manual review",
    )

    matching_enabled: bool = Field(
        default=False,
        description="Whether inventory matching is enabled for this run",
    )

    # Output path
    report_path: str = Field(
        default="output/product_report.xlsx",
        description="Path to generate the Excel report",
    )

    # Errors encountered during processing
    errors: List[str] = Field(default_factory=list)
