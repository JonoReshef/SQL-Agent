"""Email ingestion workflow node"""

from pathlib import Path
from typing import List

from workflow.analysis_workflow.utils import read_msg_files_from_directory_batch
from workflow.models.analysis_workflow import WorkflowState
from workflow.models.email import Email


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
        emails: List[Email] = read_msg_files_from_directory_batch(
            input_dir, recursive=True
        )

        state.emails = emails

        return state

    except Exception as e:
        # Capture error and continue workflow
        state.errors.append(f"Ingestion error: {str(e)}")
        return state
