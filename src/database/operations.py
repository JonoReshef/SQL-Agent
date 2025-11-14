"""Database operations for persisting workflow data"""

from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

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
                # Calculate file hash (simple hash of file path for now)
                import hashlib

                file_hash = hashlib.sha256(email.file_path.encode()).hexdigest()

                # Check if email already exists
                stmt = select(EmailProcessed).where(
                    EmailProcessed.file_path == email.file_path
                )
                existing = session.execute(stmt).scalar_one_or_none()

                if existing:
                    # Update existing email
                    existing.file_hash = file_hash
                    existing.subject = sanitize_for_db(email.metadata.subject)
                    existing.sender = sanitize_for_db(email.metadata.sender)
                    existing.date_sent = email.metadata.date
                    existing.processed_at = datetime.utcnow()
                    updated += 1
                else:
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

                # Check if product mention already exists
                stmt = select(DBProductMention).where(
                    DBProductMention.email_id == email_id,
                    DBProductMention.exact_product_text == product.exact_product_text,
                )
                existing = session.execute(stmt).scalar_one_or_none()

                # Convert properties to JSON
                properties_json = [prop.model_dump() for prop in product.properties]

                if existing:
                    # Update existing mention
                    existing.product_name = product.product_name
                    existing.product_category = product.product_category
                    existing.properties = properties_json
                    existing.quantity = product.quantity
                    existing.unit = product.unit
                    existing.context = product.context
                    existing.date_requested = product.date_requested
                    existing.requestor = product.requestor
                    updated += 1
                else:
                    # Insert new mention
                    db_product = DBProductMention(
                        email_id=email_id,
                        exact_product_text=product.exact_product_text,
                        product_name=product.product_name,
                        product_category=product.product_category,
                        properties=properties_json,
                        quantity=product.quantity,
                        unit=product.unit,
                        context=product.context,
                        date_requested=product.date_requested,
                        requestor=product.requestor,
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
                    # Check if match already exists
                    stmt = select(DBInventoryMatch).where(
                        DBInventoryMatch.product_mention_id == product_mention_id,
                        DBInventoryMatch.inventory_item_id == inventory_item_id,
                        DBInventoryMatch.rank == match.rank,
                    )
                    existing = session.execute(stmt).scalar_one_or_none()

                    if existing:
                        # Update existing match
                        existing.match_score = match.match_score
                        existing.matched_properties = match.matched_properties
                        existing.missing_properties = match.missing_properties
                        existing.match_reasoning = match.match_reasoning
                        updated += 1
                    else:
                        # Insert new match
                        db_match = DBInventoryMatch(
                            product_mention_id=product_mention_id,
                            inventory_item_id=inventory_item_id,
                            match_score=match.match_score,
                            rank=match.rank,
                            matched_properties=match.matched_properties,
                            missing_properties=match.missing_properties,
                            match_reasoning=match.match_reasoning,
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
                # Check if flag already exists
                stmt = select(MatchReviewFlag).where(
                    MatchReviewFlag.product_mention_id == product_mention_id,
                    MatchReviewFlag.issue_type == flag.issue_type,
                )
                existing = session.execute(stmt).scalar_one_or_none()

                if existing:
                    # Update existing flag
                    existing.match_count = flag.match_count
                    existing.top_confidence = flag.top_confidence
                    existing.reason = flag.reason
                    existing.action_needed = flag.action_needed
                    existing.flagged_at = datetime.utcnow()
                    updated += 1
                else:
                    # Insert new flag
                    db_flag = MatchReviewFlag(
                        product_mention_id=product_mention_id,
                        issue_type=flag.issue_type,
                        match_count=flag.match_count,
                        top_confidence=flag.top_confidence,
                        reason=flag.reason,
                        action_needed=flag.action_needed,
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
