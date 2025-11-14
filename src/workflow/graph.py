"""LangGraph workflow graph construction"""

from typing import cast
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from src.models.workflow import WorkflowState
from src.workflow.nodes.ingestion import ingest_emails
from src.workflow.nodes.extraction import extract_products
from src.workflow.nodes.reporting import generate_report
from langchain_core.globals import set_llm_cache
from langchain_redis import RedisCache


def create_workflow_graph() -> CompiledStateGraph:
    """
    Create the email analysis workflow graph.

    Workflow:
    1. Ingestion: Load and clean .msg files from directory
    2. Extraction: Extract product mentions using LLM
    3. Reporting: Generate Excel report

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create state graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("ingestion", ingest_emails)
    workflow.add_node("extraction", extract_products)
    workflow.add_node("reporting", generate_report)

    # Define edges (linear workflow)
    workflow.add_edge("ingestion", "extraction")
    workflow.add_edge("extraction", "reporting")
    workflow.add_edge("reporting", END)

    # Set entry point
    workflow.set_entry_point("ingestion")

    redis_cache = RedisCache(redis_url="redis://localhost:6379")
    set_llm_cache(redis_cache)

    graph = workflow.compile().with_config({"recursion_limit": 50})

    # Compile and return
    return graph


GRAPH = create_workflow_graph()


def run_workflow(input_directory: str, output_path: str) -> WorkflowState:
    """
    Execute the complete email analysis workflow.

    Args:
        input_directory: Path to directory containing .msg files
        output_path: Path where Excel report should be generated

    Returns:
        Final workflow state with results
    """
    # Initialize state
    initial_state = WorkflowState(
        input_directory=input_directory,
        report_path=output_path,
    )
    # Create and run workflow
    workflow_graph = create_workflow_graph()
    result = workflow_graph.invoke(initial_state)
    final_state = WorkflowState.model_validate(result)

    return final_state
