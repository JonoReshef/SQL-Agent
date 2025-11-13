"""Email ingestion workflow node"""

from pathlib import Path
from typing import List
from src.models.workflow import WorkflowState
from src.models.email import Email
from src.email_processor.msg_reader import read_msg_files_from_directory
from src.email_processor.signature_cleaner import clean_signature


def ingest_emails(state: WorkflowState) -> WorkflowState:
    """
    Ingestion node: Load and clean .msg files from directory.

    Args:
        state: Current workflow state with input_directory

    Returns:
        Updated state with emails list populated
    """
    try:
        input_dir = Path(state["input_directory"])

        # Read all .msg files from directory
        emails: List[Email] = read_msg_files_from_directory(input_dir, recursive=True)

        # Clean signatures from email bodies
        for email in emails:
            email.cleaned_body = clean_signature(email.body)

        state["emails"] = emails

        return state

    except Exception as e:
        # Capture error and continue workflow
        state["errors"].append(f"Ingestion error: {str(e)}")
        return state
