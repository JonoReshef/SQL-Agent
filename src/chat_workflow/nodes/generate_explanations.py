"""
Based on the entire search process, explain why and how the querying worked
"""

from concurrent.futures import ThreadPoolExecutor
from typing import List

from src.chat_workflow.prompts import EXPLANATION_PROMPT
from src.llm.client import get_llm_client
from src.models.chat_models import ChatState, QueryExecution, QueryExplanation

LLM = get_llm_client(type="gpt4.1")
LLM_STRUCTURED = get_llm_client(type="gpt4.1", output_structure=QueryExplanation)


def _generate_query_explanation_and_summary(query: QueryExecution) -> QueryExecution:
    """
    Generate human-readable explanation and result summary for a SQL query.

    Args:
        query: The SQL query that was executed
        result: The result returned from the query

    Returns:
        Tuple of (explanation, result_summary)
    """
    try:
        response = QueryExplanation.model_validate(
            LLM_STRUCTURED.invoke(
                EXPLANATION_PROMPT.format(query=query.query, result=query.raw_result)
            )
        )
        # Update the query execution with the explanation
        query.query_explanation = response

    except Exception as e:
        # Fallback to generic messages if LLM fails
        print(f"   Warning: Failed to generate query explanation - {str(e)}")
        query.query_explanation = QueryExplanation(
            description="Unable to generate explanation",
            result_summary=None,
        )
    return query


def _generate_overall_explanation(executed_queries: List[QueryExecution]) -> str:
    """
    Generate overall explanation of the search process based on executed queries.

    Args:
        executed_queries: List of QueryExecution objects

    Returns:
        Overall explanation string
    """
    try:
        explanations = "\n".join(
            [
                f"Query: {q.query}\n\
                Explanation: {q.query_explanation.description if q.query_explanation else 'N/A'}\n\
                Result Summary: {q.query_explanation.result_summary if q.query_explanation else 'N/A'}\n\
                Raw results: {q.raw_result}\n"
                for q in executed_queries
            ]
        )

        overall_prompt = """
            Based on the following executed queries, their explanations and results provide a concise 1-2 line summary of the overall search process. Only output the summary no additional text: {explanations}
        """

        overall_summary = LLM.invoke(
            overall_prompt.format(explanations=explanations),
        )

        return str(overall_summary.content)

    except Exception as e:
        print(f"   Warning: Failed to generate overall explanation - {str(e)}")
        return "Unable to generate overall explanation."


def generate_explanations_node(state: ChatState):
    """
    Explanation node: Generate explanations for all executed queries.

    Args:
        state: Current chat state with executed queries
    Returns:
        Updated state with explanations added to each QueryExecution
    """

    # Parallelized the explanation generation
    executed_queries_with_explanations = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for query in state.executed_queries:
            futures.append(
                executor.submit(
                    _generate_query_explanation_and_summary,
                    query,
                )
            )

        for future in futures:
            executed_queries_with_explanations.append(future.result())

    # Based on all executed queries, generate overall explanation
    overall_summary = _generate_overall_explanation(executed_queries_with_explanations)
    return {
        "overall_summary": overall_summary,
        "executed_queries_enriched": executed_queries_with_explanations,
        "status_update": None,
    }
