"""
This node enriches the user's question with context before generating a SQL query.
"""

from typing import Any, Dict

from langchain_core.messages import HumanMessage

from src.chat_workflow.prompts import DATABASE_SCHEMA_PROMPT
from src.llm.client import get_llm_client
from src.models.chat_models import ChatState, QuestionEnrichment

LLM = get_llm_client(output_structure=QuestionEnrichment)


def enrich_question_node(state: ChatState) -> Dict[str, Any]:
    """
    Enrich the user's question with additional context.

    This node can add clarifying details, constraints, or examples
    to help the LLM generate a more accurate SQL query.

    Args:
        state: Current chat state with user message

    Returns:
        Dict with enriched AIMessage
    """

    # Example enrichment: add clarifying details
    enriched_content = """
        You are an expert SQL and research assistant.

        We have access to a database with the following schema:
        {schema}

        This is the current user question: 
        {user_question}

        This question may be ambiguous, lack detail or not fully capture the user's intent.

        This is the conversation history so far:
        {previous_queries}

        Using the provided schema and prior conversation history, expand the user question into up to 3 statements which will be answered by an SQL data analyst expert to more completely answer the users intent. 

        For example: 
        User Question: "What were the sales last quarter?"
        Enriched Questions:
        1. "Total sales figures for each month in the last quarter"
        2. "Breakdown sales by product category for the last quarter"
        3. "Any significant sales trends or anomalies in the last quarter"

        Who was the most active customer last month?
        1. "Total number of purchases made by each customer last month"
        2. "Total spending by each customer last month"
        3. "Frequency of purchases by customer segments last month"

        Output the enriched questions as a list of strings.
        Explain what the intended goal of these questions are.
        """

    response = QuestionEnrichment.model_validate(
        LLM.invoke(
            enriched_content.format(
                user_question=state.user_question,
                schema=DATABASE_SCHEMA_PROMPT,  # Placeholder for actual schema
                previous_queries=state.messages[:-1],  # Placeholder for actual previous queries
            )
        )
    )

    question = HumanMessage(
        content=f"""
            This is the original question from a user who is an expert in sales and marketing data analysis:
            {state.user_question}

            These are the enriched question(s) to help generate the SQL queries:
            {response.additional_questions}

            This is the value added by using the enriched question(s):
            {response.intended_goal}
        """
    )

    return {"enriched_query": response, "messages": [question]}
