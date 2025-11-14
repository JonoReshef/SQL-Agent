"""Main CLI entry point for email analysis workflow"""

import sys
from pathlib import Path
from src.workflow.graph import run_workflow


def main(input_dir: str, output_path: str):
    """
    Main CLI entry point.

    Usage:
        python -m src.main <input_directory> <output_path>

    Args:
        input_directory: Directory containing .msg files to analyze
        output_path: Path where Excel report should be generated
    """

    # Validate input directory
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        sys.exit(1)

    # Create output directory if needed
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Run workflow
    print(f"Starting email analysis workflow...")
    print(f"  Input directory: {input_dir}")
    print(f"  Output path: {output_path}")
    print()

    try:
        final_state = run_workflow(input_dir, output_path)

        # Report results
        print("Workflow completed!")
        print(f"  Emails processed: {len(final_state.emails)}")
        print(f"  Products extracted: {len(final_state.extracted_products)}")
        print(f"  Report generated: {final_state.report_path}")

        # Report any errors
        if final_state.errors:
            print("\nErrors encountered:")
            for error in final_state.errors:
                print(f"  - {error}")
            sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime

    src_email = "data/selected"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_report = f"output/report_{timestamp}.xlsx"

    # Parse CLI arguments
    if len(sys.argv) == 3:
        # Both arguments provided
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        # Only input directory provided, use default output with timestamp
        main(sys.argv[1], output_report)
    elif len(sys.argv) == 1:
        # No arguments, use defaults
        main(src_email, output_report)
    else:
        print("Usage: python -m src.main [input_directory] [output_path]")
        print("  input_directory: Directory containing .msg files (default: data/)")
        print(
            "  output_path: Path for Excel report (default: output/report_<timestamp>.xlsx)"
        )
        sys.exit(1)
