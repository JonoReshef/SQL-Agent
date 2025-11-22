"""Email ingestion workflow node"""

from pathlib import Path
from typing import List

from src.analysis_workflow.utils import clean_signature, read_msg_files_from_directory
from src.models.analysis_workflow import WorkflowState
from src.models.email import Email
from src.utils.compute_content_hash import compute_content_hash


def ingest_emails(state: WorkflowState) -> WorkflowState:
    """
    Ingestion node: Load and clean .msg files from directory.

    Args:
        state: Current workflow state with input_directory

    Returns:
        Updated state with emails list populated
    """
    try:
        input_dir = Path(state.input_directory)

        # Read all .msg files from directory
        emails: List[Email] = read_msg_files_from_directory(input_dir, recursive=True)

        # Clean signatures from email bodies and compute content hash
        for email in emails:
            email.cleaned_body = clean_signature(email.body)
            email.thread_hash = compute_content_hash(email)

        state.emails = emails

        return state

    except Exception as e:
        # Capture error and continue workflow
        state.errors.append(f"Ingestion error: {str(e)}")
        return state
