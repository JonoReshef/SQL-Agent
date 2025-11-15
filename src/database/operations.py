"""Database operations for persisting workflow data"""

import hashlib
import json
from datetime import datetime
from typing import List

from pydantic import BaseModel
from sqlalchemy import select

from src.database.connection import get_db_session
from src.database.models import (
    EmailProcessed,
    MatchReviewFlag,
)
from src.database.models import (
    InventoryMatch as DBInventoryMatch,
)
from src.database.models import (
    ProductMention as DBProductMention,
)
from src.models.email import Email
from src.models.inventory import InventoryMatch, ReviewFlag
from src.models.product import ProductMention


def compute_content_hash(*args) -> str:
    """
    Compute SHA256 hash of content for duplicate detection.

    Args:
        *args: Variable arguments to include in hash

    Returns:
        Hex string of SHA256 hash
    """
    # Create a deterministic string representation
    content_parts = []
    for arg in args:
        if arg is None:
            content_parts.append("NULL")
        elif isinstance(arg, BaseModel):
            # For Pydantic models, use their dict representation
            content_parts.append(json.dumps(arg.model_dump(), sort_keys=True))
        elif isinstance(arg, (dict, list)):
            # For JSON-serializable objects, use sorted JSON
            content_parts.append(json.dumps(arg, sort_keys=True))
        else:
            content_parts.append(str(arg))

    content_str = "|".join(content_parts)
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()


def sanitize_for_db(text: str | None) -> str | None:
    """
    Sanitize text for PostgreSQL storage.
    Removes NUL bytes which PostgreSQL text fields cannot contain.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text safe for PostgreSQL
    """
    if text is None:
        return None
    # Remove NUL bytes
    return text.replace("\x00", "")


def store_emails(emails: List[Email]) -> dict:
    """
    Store processed emails to database.
    Uses upsert to avoid duplicates based on email file path.

    Args:
        emails: List of Email objects

    Returns:
        Dictionary with statistics: inserted, updated, errors
    """
    inserted = 0
    updated = 0
    errors = []

    with get_db_session() as session:
        for email in emails:
            try:
                # Calculate file hash based on file path only (unique identifier)
                # For actual content change detection, read file if needed
                file_hash = compute_content_hash(email)

                # Check if email already exists by file_hash
                stmt = select(EmailProcessed).where(
                    EmailProcessed.file_hash == file_hash
                )
                existing = session.execute(stmt).scalar_one_or_none()

                existing = EmailProcessed(
                    file_path=email.file_path,
                    file_hash=file_hash,
                    subject=sanitize_for_db(email.metadata.subject),
                    sender=sanitize_for_db(email.metadata.sender),
                    date_sent=email.metadata.date,
                )

                if not existing:
                    # Insert new email
                    db_email = EmailProcessed(
                        file_path=email.file_path,
                        file_hash=file_hash,
                        subject=sanitize_for_db(email.metadata.subject),
                        sender=sanitize_for_db(email.metadata.sender),
                        date_sent=email.metadata.date,
                    )
                    session.add(db_email)
                    inserted += 1

                # Commit every 10 emails
                if (inserted + updated) % 10 == 0:
                    session.commit()

            except Exception as e:
                errors.append(f"Email {email.file_path}: {e}")
                session.rollback()
                continue

        # Final commit
        try:
            session.commit()
        except Exception as e:
            errors.append(f"Final commit failed: {e}")
            session.rollback()

    return {
        "inserted": inserted,
        "updated": updated,
        "errors": len(errors),
        "error_details": errors,
    }


def store_product_mentions(products: List[ProductMention], emails: List[Email]) -> dict:
    """
    Store product mentions to database.
    Links products to their source emails via email_id foreign key.

    Args:
        products: List of ProductMention objects
        emails: List of Email objects (needed to look up email_id)

    Returns:
        Dictionary with statistics: inserted, updated, errors
    """
    inserted = 0
    updated = 0
    errors = []

    # Create mapping of file_path to email_id
    email_path_to_id = {}

    with get_db_session() as session:
        # First get all email IDs
        for email in emails:
            stmt = select(EmailProcessed).where(
                EmailProcessed.file_path == email.file_path
            )
            db_email = session.execute(stmt).scalar_one_or_none()
            if db_email:
                email_path_to_id[email.file_path] = db_email.id

        # Now process products
        for product in products:
            try:
                # Get email_id for this product
                email_id = email_path_to_id.get(product.email_file)
                if not email_id:
                    errors.append(
                        f"Product '{product.exact_product_text[:50]}': Email not found in database"
                    )
                    continue

                # Compute content hash for this product mention within the email
                content_hash = compute_content_hash(
                    email_id,
                    product,
                )

                # Check if product mention already exists by content hash
                stmt = select(DBProductMention).where(
                    DBProductMention.content_hash == content_hash
                )
                existing = session.execute(stmt).scalar_one_or_none()

                if not existing:
                    # Insert new mention
                    db_product = DBProductMention(
                        email_id=email_id,
                        exact_product_text=product.exact_product_text,
                        product_name=product.product_name,
                        product_category=product.product_category,
                        properties=product.model_dump().get("properties", []),
                        quantity=product.quantity,
                        unit=product.unit,
                        context=product.context,
                        date_requested=product.date_requested,
                        requestor=product.requestor,
                        content_hash=content_hash,
                    )
                    session.add(db_product)
                    inserted += 1

                # Commit every 20 products
                if (inserted + updated) % 20 == 0:
                    session.commit()

            except Exception as e:
                errors.append(f"Product '{product.exact_product_text[:50]}...': {e}")
                session.rollback()
                continue

        # Final commit
        try:
            session.commit()
        except Exception as e:
            errors.append(f"Final commit failed: {e}")
            session.rollback()

    return {
        "inserted": inserted,
        "updated": updated,
        "errors": len(errors),
        "error_details": errors,
    }


def store_inventory_matches(
    product_matches: dict[str, List[InventoryMatch]],
    products: List[ProductMention],
) -> dict:
    """
    Store inventory matches to database.
    Uses product_mention_id and inventory_item_id foreign keys.

    Args:
        product_matches: Dictionary mapping product text to list of matches
        products: List of ProductMention objects to look up IDs

    Returns:
        Dictionary with statistics: inserted, updated, errors
    """
    inserted = 0
    updated = 0
    errors = []

    with get_db_session() as session:
        # Build mapping of product text to product_mention_id
        # Note: Uses first() to handle duplicate products (same text in different contexts)
        product_text_to_id = {}
        for product in products:
            stmt = select(DBProductMention).where(
                DBProductMention.exact_product_text == product.exact_product_text
            )
            db_product = session.execute(stmt).scalars().first()
            if db_product:
                product_text_to_id[product.exact_product_text] = db_product.id

        # Build mapping of inventory item_number to inventory_item_id
        from src.database.models import InventoryItem as DBInventoryItem

        item_number_to_id = {}

        for product_text, matches in product_matches.items():
            for match in matches:
                if match.inventory_item_number not in item_number_to_id:
                    stmt = select(DBInventoryItem).where(
                        DBInventoryItem.item_number == match.inventory_item_number
                    )
                    db_inventory = session.execute(stmt).scalar_one_or_none()
                    if db_inventory:
                        item_number_to_id[match.inventory_item_number] = db_inventory.id

        # Now insert/update matches
        for product_text, matches in product_matches.items():
            product_mention_id = product_text_to_id.get(product_text)
            if not product_mention_id:
                errors.append(
                    f"Match for '{product_text[:50]}': Product not found in database"
                )
                continue

            for match in matches:
                inventory_item_id = item_number_to_id.get(match.inventory_item_number)
                if not inventory_item_id:
                    errors.append(
                        f"Match {product_text[:30]} -> {match.inventory_item_number}: Inventory item not found"
                    )
                    continue

                try:
                    # Compute content hash for this match
                    content_hash = compute_content_hash(
                        product_mention_id, inventory_item_id, match
                    )

                    # Check if match already exists by content hash
                    stmt = select(DBInventoryMatch).where(
                        DBInventoryMatch.content_hash == content_hash
                    )
                    existing = session.execute(stmt).scalar_one_or_none()

                    if not existing:
                        # Insert new match
                        db_match = DBInventoryMatch(
                            product_mention_id=product_mention_id,
                            inventory_item_id=inventory_item_id,
                            match_score=match.match_score,
                            rank=match.rank,
                            matched_properties=match.matched_properties,
                            missing_properties=match.missing_properties,
                            match_reasoning=match.match_reasoning,
                            content_hash=content_hash,
                        )
                        session.add(db_match)
                        inserted += 1

                    # Commit every 50 matches
                    if (inserted + updated) % 50 == 0:
                        session.commit()

                except Exception as e:
                    errors.append(
                        f"Match {product_text[:30]} -> {match.inventory_item_number}: {e}"
                    )
                    session.rollback()
                    continue

        # Final commit
        try:
            session.commit()
        except Exception as e:
            errors.append(f"Final commit failed: {e}")
            session.rollback()

    return {
        "inserted": inserted,
        "updated": updated,
        "errors": len(errors),
        "error_details": errors,
    }


def store_review_flags(
    review_flags: List[ReviewFlag], products: List[ProductMention]
) -> dict:
    """
    Store review flags to database.
    Uses product_mention_id foreign key.

    Args:
        review_flags: List of ReviewFlag objects
        products: List of ProductMention objects to look up IDs

    Returns:
        Dictionary with statistics: inserted, updated, errors
    """
    inserted = 0
    updated = 0
    errors = []

    with get_db_session() as session:
        # Build mapping of product text to product_mention_id
        # Note: Uses first() to handle duplicate products (same text in same email)
        product_text_to_id = {}
        for product in products:
            stmt = select(DBProductMention).where(
                DBProductMention.exact_product_text == product.exact_product_text
            )
            db_product = session.execute(stmt).scalars().first()
            if db_product:
                product_text_to_id[product.exact_product_text] = db_product.id

        for flag in review_flags:
            product_mention_id = product_text_to_id.get(flag.product_text)
            if not product_mention_id:
                errors.append(
                    f"Flag for '{flag.product_text[:50]}': Product not found in database"
                )
                continue

            try:
                # Compute content hash for this flag
                content_hash = compute_content_hash(product_mention_id, flag)

                # Check if flag already exists by content hash
                stmt = select(MatchReviewFlag).where(
                    MatchReviewFlag.content_hash == content_hash
                )
                existing = session.execute(stmt).scalar_one_or_none()

                if not existing:
                    # Insert new flag
                    db_flag = MatchReviewFlag(
                        product_mention_id=product_mention_id,
                        issue_type=flag.issue_type,
                        match_count=flag.match_count,
                        top_confidence=flag.top_confidence,
                        reason=flag.reason,
                        action_needed=flag.action_needed,
                        content_hash=content_hash,
                    )
                    session.add(db_flag)
                    inserted += 1

                # Commit every 20 flags
                if (inserted + updated) % 20 == 0:
                    session.commit()

            except Exception as e:
                errors.append(f"Flag '{flag.product_text[:50]}': {e}")
                session.rollback()
                continue

        # Final commit
        try:
            session.commit()
        except Exception as e:
            errors.append(f"Final commit failed: {e}")
            session.rollback()

    return {
        "inserted": inserted,
        "updated": updated,
        "errors": len(errors),
        "error_details": errors,
    }
