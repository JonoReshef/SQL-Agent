"""LangGraph workflow state models"""

from typing import TypedDict, List
from src.models.email import Email
from src.models.product import ProductMention, ProductAnalytics


class WorkflowState(TypedDict):
    """
    State for the email analysis workflow.

    This TypedDict is used by LangGraph to track state across workflow nodes.
    """

    # Input directory containing .msg files
    input_directory: str

    # Input data
    emails: List[Email]

    # Processing results
    extracted_products: List[ProductMention]

    # Analytics
    analytics: List[ProductAnalytics]

    # Output path
    report_path: str

    # Errors encountered during processing
    errors: List[str]
