"""Workflow node for database persistence"""

from src.database.operations import (
    store_emails,
    store_inventory_matches,
    store_product_mentions,
    store_review_flags,
)
from src.models.analysis_workflow import WorkflowState


def persist_to_database(state: WorkflowState) -> WorkflowState:
    """
    Persist workflow data to database.

    This node:
    1. Stores emails to emails_processed table
    2. Stores product mentions to product_mentions table
    3. If matching enabled, stores matches and review flags

    Args:
        state: Current workflow state

    Returns:
        Updated workflow state with persistence statistics
    """
    print("\n💾 Persisting data to database...")

    # Store emails
    if state.emails:
        try:
            result = store_emails(state.emails)
            print(f"   Emails: {result['inserted']} inserted, {result['updated']} updated")
            if result["errors"]:
                print(f"   ⚠️  {result['errors']} email errors")
                state.errors.extend(result["error_details"])
        except Exception as e:
            error_msg = f"Failed to store emails: {e}"
            print(f"   ❌ {error_msg}")
            state.errors.append(error_msg)

    # Store product mentions
    if state.extracted_products:
        try:
            result = store_product_mentions(state.extracted_products, state.emails)
            print(f"   Products: {result['inserted']} inserted, {result['updated']} updated")
            if result["errors"]:
                print(f"   ⚠️  {result['errors']} product errors")
                state.errors.extend(result["error_details"])
        except Exception as e:
            error_msg = f"Failed to store products: {e}"
            print(f"   ❌ {error_msg}")
            state.errors.append(error_msg)

    # Store inventory matches if matching was enabled
    if state.matching_enabled and state.product_matches:
        try:
            result = store_inventory_matches(state.product_matches, state.extracted_products)
            print(
                f"   Matches: {result['inserted']} inserted, {result['updated']} updated, {result['skipped']} skipped"
            )
            if result["errors"]:
                print(f"   ⚠️  {result['errors']} match errors")
                state.errors.extend(result["error_details"])
        except Exception as e:
            error_msg = f"Failed to store matches: {e}"
            print(f"   ❌ {error_msg}")
            state.errors.append(error_msg)

    # Store review flags if matching was enabled
    if state.matching_enabled and state.review_flags:
        try:
            result = store_review_flags(state.review_flags, state.extracted_products)
            print(f"   Flags: {result['inserted']} inserted, {result['updated']} updated")
            if result["errors"]:
                print(f"   ⚠️  {result['errors']} flag errors")
                state.errors.extend(result["error_details"])
        except Exception as e:
            error_msg = f"Failed to store flags: {e}"
            print(f"   ❌ {error_msg}")
            state.errors.append(error_msg)

    print("✅ Database persistence completed")
    return state
