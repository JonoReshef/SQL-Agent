"""Report generation workflow node"""

from pathlib import Path
from src.models.workflow import WorkflowState
from src.report.excel_generator import generate_excel_report


def generate_report(state: WorkflowState) -> WorkflowState:
    """
    Reporting node: Generate Excel report from extracted products.

    Args:
        state: Current workflow state with extracted_products and emails

    Returns:
        Updated state with report_path set to generated file location
    """
    try:
        # Generate Excel report
        output_path = Path(state.report_path)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result_path = generate_excel_report(
            products=state.extracted_products,
            emails=state.emails,
            output_path=output_path,
        )

        # Update state with actual path
        state.report_path = str(result_path)

        return state

    except Exception as e:
        # Capture error and continue workflow
        state.errors.append(f"Report generation error: {str(e)}")
        return state
