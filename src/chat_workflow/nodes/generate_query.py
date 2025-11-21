"""Generate query node for SQL chat agent"""

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.chat_workflow.prompts import DATABASE_SCHEMA_PROMPT, WESTBRAND_SYSTEM_PROMPT
from src.chat_workflow.utils.db_wrapper import BLACK_LIST, get_sql_database
from src.chat_workflow.utils.tools import get_schema_tool, run_query_tool
from src.llm.client import get_llm_client
from src.models.chat_models import ChatState


def generate_query_node(state: ChatState) -> Dict[str, Any]:
    """
    Generate SQL query from user question using LLM.

    This node uses the LLM with tool binding to convert natural language
    questions into SQL queries.

    Args:
        state: Current chat state with user message

    Returns:
        Dict with AIMessage containing tool call or final response
    """
    try:
        # Get LLM client with default settings (gpt5-low)
        llm = get_llm_client()

        # Bind the run_query tool to LLM
        llm_with_tools = llm.bind_tools(  # type: ignore
            [
                run_query_tool,  # Execute a query
                get_schema_tool,  # Get database schema information
            ]
        )

        # Build messages for LLM
        # Include system prompt first
        system_message = SystemMessage(
            WESTBRAND_SYSTEM_PROMPT.format(
                black_list=",".join(BLACK_LIST),
                table_list=list_tables_node(),
                database_schema=DATABASE_SCHEMA_PROMPT,
            )
        )

        # Adjust guidance based on complexity setting
        max_queries = 30 if state.anticipate_complexity else 10
        complexity_guidance = (
            f"Be direct and efficient. Focus on answering the specific question asked. Maximum {max_queries} queries total."
            if not state.anticipate_complexity
            else f"Be thorough and exploratory. Investigate related aspects and provide comprehensive insights. Maximum {max_queries} queries total to explore the data deeply."
        )

        prompt = """
            This is the user question you must answer:
            {user_query}

            Here are supplementary questions that should be considered to understand the context and the reason why these questions are being asked:
            {enriched_query}

            Here are the previous queries and results of those queries. 
            {previous_queries_results}

            Here is the full previous conversation including both the user questions and the AI responses in chronological order from the start of the conversation to now:
            {previous_user_questions}
            
            COMPLEXITY GUIDANCE: {complexity_guidance}
            
            From these results decide whether to perform one of these three actions:
            - Generate new postgres SQL queries to use with the run_query_tool. If there are errors in the previous queries, learn from those errors to produce correct queries. Otherwise, use the previous queries to build more specific, accurate or investigative queries as needed to fully answer the user's question. 
            - Get more information from the database using the get_schema_tool. If more information about the database schema then query this tool
            - If the returned results fully answer the user's question, provide an evidenced based final answer and do not invoke any tools. Do not include any SQL in the final answer. The final output must be rendered in markdown. Avoid referencing specific table or column names in the final answer and replace any non-human results such as hashes and IDs with more understandable terms.
            
            IMPORTANT: Track your query count. You have executed {query_count} queries so far. Maximum allowed: {max_queries}. If approaching the limit, prioritize providing a final answer with available data.
            """

        human_message = prompt.format(
            user_query=str(state.user_question),
            enriched_query=state.enriched_query.model_dump_json(),
            previous_user_questions="\n".join(
                [
                    f"Question {n}: {msg.content}"
                    for n, msg in enumerate(state.messages[:-1], start=1)
                ]
            ),
            previous_queries_results="\n".join(
                [
                    f"QUERY: {query.query}\nRESULT: {query.raw_result or 'No result'}"
                    for query in state.executed_queries
                ]
            ),
            complexity_guidance=complexity_guidance,
            query_count=len(state.executed_queries),
            max_queries=max_queries,
        )

        # Convert state messages to format LLM expects
        messages = [system_message] + [HumanMessage(content=human_message)]

        # Generate the SQL query
        response = llm_with_tools.invoke(messages)

        if not response or not hasattr(response, "tool_calls") or not response.tool_calls:  # type: ignore
            # If there are no tool calls then we are done so append the final message
            return {
                "messages": [response],
                "query_result": response,
                "status_update": "Final answer generated. Generating explanations",
            }

        else:
            # Generate a human readable explanation about what is going on
            tool_call_names = list(set([tool.get("name", "") for tool in response.tool_calls]))  # type: ignore

            tool_call_message = f"We have run {len(state.executed_queries)} queries so far."
            if "get_schema_tool" in tool_call_names:
                tool_call_message += " Getting information about the data"
            if "run_query_tool" in tool_call_names:
                total_queries = len(
                    [tool for tool in response.tool_calls if tool.get("name") == "run_query_tool"]
                )
                tool_call_message += (
                    f" Running {total_queries} {'query' if total_queries == 1 else 'queries'}. "
                )

            return {
                "query_result": response,
                "status_update": tool_call_message,
            }

    except Exception as e:
        error_message = AIMessage(content=f"Error generating query: {str(e)}")
        return {"error": str(e), "messages": [error_message]}


def list_tables_node() -> str:
    """
    List all available database tables.

    This node is executed at the start of the workflow to provide
    the agent with context about available tables.

    Args:
        state: Current chat state

    Returns:
        Dict with updated state containing:
        - available_tables: List of table names
        - messages: AIMessage with table list
    """
    try:
        db = get_sql_database()
        tables = db.get_usable_table_names()

        # Create informative message about available tables
        table_list = ", ".join(tables)

        return table_list

    except Exception as e:
        # Handle errors gracefully
        return f"Error listing tables: {str(e)}"
