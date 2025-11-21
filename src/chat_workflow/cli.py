"""CLI interface for testing SQL chat agent"""

import uuid

from langchain_core.messages import HumanMessage

from src.chat_workflow.graph import create_chat_graph
from src.models.chat_models import ChatState


def run_cli_chat():
    """
    CLI interface for testing the SQL chat agent.

    This provides a simple interactive interface for testing
    without needing to start the FastAPI server.
    """
    try:
        graph = create_chat_graph()
        thread_id = str(uuid.uuid4())[:8]

        print("=" * 70)
        print("🤖 WestBrand SQL Chat Agent - CLI Interface")
        print("=" * 70)
        print(f"Thread ID: {thread_id}")
        print("Type 'exit' or 'quit' to end the session")
        print("Type 'history' to view conversation history")
        print("=" * 70)
        print()

        while True:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "history":
                print("\n📜 Conversation History:")
                config = {"configurable": {"thread_id": thread_id}}
                for i, state in enumerate(graph.get_state_history(config), 1):  # type: ignore
                    print(f"\n--- Checkpoint {i} ---")
                    for msg in state.values.get("messages", []):
                        msg_type = msg.__class__.__name__
                        content = msg.content if hasattr(msg, "content") else str(msg)
                        print(f"{msg_type}: {content[:100]}...")
                print()
                continue

            # Process query
            config = {"configurable": {"thread_id": thread_id}}

            try:
                print("\n🔄 Processing...\n")

                # Track last event for SQL query display
                last_event = None

                # Stream the response
                for event in graph.stream(
                    {"user_question": user_input},
                    config,  # type: ignore
                    stream_mode="values",
                ):
                    last_event = event
                    if "messages" in event and event["messages"]:
                        last_msg = event["messages"][-1]

                        # Only print AI messages (skip tool messages)
                        if (
                            hasattr(last_msg, "content")
                            and last_msg.__class__.__name__ == "AIMessage"
                        ):
                            content = last_msg.content
                            if content and content.strip():
                                print(f"🤖 Agent: {content}\n")

                # Display executed SQL queries for transparency
                if (
                    last_event
                    and "executed_queries" in last_event
                    and last_event["executed_queries"]
                ):
                    final_state = ChatState.model_validate(last_event)
                    if final_state.overall_summary:
                        print("\\n " + "=" * 70)
                        print("Process summary:")
                        print(f"💡 {final_state.overall_summary}")

                    print("\\n" + "=" * 70)
                    print("📊 SQL Queries Executed:")
                    print("=" * 70)
                    for i, query_exec in enumerate(final_state.executed_queries, 1):
                        if query_exec.query_explanation:
                            print(f"\nQuery explanation {i}:")
                            print(f"  💡 {query_exec.query_explanation.description}")
                            print(f"  📈 Result: {query_exec.query_explanation.result_summary}")
                        print("\n  SQL:")
                        # Indent SQL for readability
                        for line in query_exec.query.split("\n"):
                            print(f"    {line}")
                    print("\n" + "=" * 70 + "\n")

            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        print("Make sure:")
        print("1. PostgreSQL is running (docker-compose up -d)")
        print("2. DATABASE_URL is set in .env")
        print("3. AZURE_LLM_API_KEY and AZURE_LLM_ENDPOINT are set")
        return


if __name__ == "__main__":
    run_cli_chat()
