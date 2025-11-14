"""LangGraph workflow state models"""

from typing import List
from pydantic import BaseModel, Field
from src.models.email import Email
from src.models.product import ProductMention, ProductAnalytics


class WorkflowState(BaseModel):
    """
    State for the email analysis workflow.

    This Pydantic model is used by LangGraph to track state across workflow nodes.
    """

    # Input directory containing .msg files
    input_directory: str = ""

    # Input data
    emails: List[Email] = Field(default_factory=list)

    # Processing results
    extracted_products: List[ProductMention] = Field(default_factory=list)

    # Analytics
    analytics: List[ProductAnalytics] = Field(default_factory=list)

    # Output path
    report_path: str = ""

    # Errors encountered during processing
    errors: List[str] = Field(default_factory=list)
