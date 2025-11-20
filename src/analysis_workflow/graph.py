"""LangGraph workflow graph construction"""

from langchain_core.globals import set_llm_cache
from langchain_redis import RedisCache
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.analysis_workflow.nodes.extraction.extraction import extract_products
from src.analysis_workflow.nodes.ingestion.ingestion import ingest_emails
from src.analysis_workflow.nodes.matching.matching import match_products
from src.analysis_workflow.nodes.persistence.persistence import persist_to_database
from src.analysis_workflow.nodes.reporting.reporting import generate_report
from src.models.workflow import WorkflowState


def create_workflow_graph(enable_matching: bool = False) -> CompiledStateGraph:
    """
    Create the email analysis workflow graph.

    Workflow:
    1. Ingestion: Load and clean .msg files from directory
    2. Extraction: Extract product mentions using LLM
    3. Matching: Match products against inventory (optional)
    4. Reporting: Generate Excel report

    Args:
        enable_matching: Whether to enable inventory matching (requires database)

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create state graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("ingestion", ingest_emails)
    workflow.add_node("extraction", extract_products)
    workflow.add_node("matching", match_products)
    workflow.add_node("persistence", persist_to_database)
    workflow.add_node("reporting", generate_report)

    # Define edges
    workflow.add_edge("ingestion", "extraction")

    if enable_matching:
        # With matching: extraction -> matching -> persistence -> reporting
        workflow.add_edge("extraction", "matching")
        workflow.add_edge("matching", "persistence")
    else:
        # Without matching: extraction -> persistence -> reporting
        workflow.add_edge("extraction", "persistence")

    workflow.add_edge("persistence", "reporting")
    workflow.add_edge("reporting", END)

    # Set entry point
    workflow.set_entry_point("ingestion")

    redis_cache = RedisCache(redis_url="redis://localhost:6379")
    set_llm_cache(redis_cache)

    graph = workflow.compile().with_config({"recursion_limit": 50})

    # Compile and return
    return graph


GRAPH = create_workflow_graph()


def run_workflow(
    input_directory: str, output_path: str, enable_matching: bool = False
) -> WorkflowState:
    """
    Execute the complete email analysis workflow.

    Args:
        input_directory: Path to directory containing .msg files
        output_path: Path where Excel report should be generated
        enable_matching: Whether to enable inventory matching

    Returns:
        Final workflow state with results
    """
    # Initialize state
    initial_state = WorkflowState(
        input_directory=input_directory,
        report_path=output_path,
        matching_enabled=enable_matching,
    )
    # Create and run workflow
    workflow_graph = create_workflow_graph(enable_matching=enable_matching)
    result = workflow_graph.invoke(initial_state)
    final_state = WorkflowState.model_validate(result)

    return final_state
