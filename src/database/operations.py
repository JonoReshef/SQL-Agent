"""Database operations for persisting workflow data"""

from typing import List

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
from src.utils.compute_content_hash import compute_content_hash


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
    Uses upsert to avoid duplicates based on email content hash.

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
                # Use the content hash from the email object
                # This hash is computed based on email metadata + body content
                thread_hash = email.thread_hash
                if not thread_hash:
                    # Fallback: compute hash if not present
                    thread_hash = compute_content_hash(email)

                # Check if email already exists by thread_hash
                stmt = select(EmailProcessed).where(EmailProcessed.thread_hash == thread_hash)
                existing = session.execute(stmt).scalar_one_or_none()

                if not existing:
                    # Insert new email
                    db_email = EmailProcessed(
                        thread_hash=thread_hash,
                        file_path=email.file_path,
                        subject=sanitize_for_db(email.metadata.subject),
                        sender=sanitize_for_db(email.metadata.sender),
                        date_sent=email.metadata.date,
                    )
                    session.add(db_email)
                    inserted += 1
                else:
                    # Email already exists, skip
                    pass

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
    Links products to their source emails via email_id foreign key using content hash.

    Args:
        products: List of ProductMention objects
        emails: List of Email objects (needed to look up email_id)

    Returns:
        Dictionary with statistics: inserted, updated, errors
    """
    inserted = 0
    updated = 0
    errors = []

    with get_db_session() as session:
        # Now process products
        for product in products:
            try:
                # Get thread_hash for this product
                thread_hash = product.thread_hash
                if not thread_hash:
                    errors.append(
                        f"Product '{product.exact_product_text[:50]}': Missing thread_hash"
                    )
                    continue

                # Verify email exists in database
                stmt = select(EmailProcessed).where(EmailProcessed.thread_hash == thread_hash)
                db_email = session.execute(stmt).scalar_one_or_none()
                if not db_email:
                    errors.append(
                        f"Product '{product.exact_product_text[:50]}': Email not found in database"
                    )
                    continue

                # Compute content hash for this product mention within the email
                content_hash = compute_content_hash(
                    thread_hash,
                    product,
                )

                # Check if product mention already exists by content hash
                stmt = select(DBProductMention).where(DBProductMention.content_hash == content_hash)
                existing = session.execute(stmt).scalar_one_or_none()

                if not existing:
                    # Insert new mention
                    db_product = DBProductMention(
                        email_thread_hash=thread_hash,
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
    skipped = 0
    errors = []

    with get_db_session() as session:
        # Build mapping of product text to product_mention_id
        # Note: Uses first() to handle duplicate products (same text in different contexts)
        product_hash_to_id = {}
        for product in products:
            stmt = select(DBProductMention).where(
                DBProductMention.exact_product_text == product.exact_product_text
            )
            db_product = session.execute(stmt).scalars().first()
            if db_product:
                # NOTE should actually store the hash value rather than recreating it
                product_hash_to_id[compute_content_hash(product)] = db_product.id

        # Build mapping of inventory item_number to inventory_item_id
        from src.database.models import InventoryItem as DBInventoryItem

        item_number_to_id = {}
        for product_hash, matches in product_matches.items():
            for match in matches:
                if match.inventory_item_number not in item_number_to_id:
                    stmt = select(DBInventoryItem).where(
                        DBInventoryItem.item_number == match.inventory_item_number
                    )
                    db_inventory = session.execute(stmt).scalar_one_or_none()
                    if db_inventory:
                        item_number_to_id[match.inventory_item_number] = db_inventory.id

        # Now insert/update matches
        for product_hash, matches in list(product_matches.items()):
            product_mention_id = product_hash_to_id.get(product_hash)
            if not product_mention_id:
                errors.append(f"Match for '{product_hash}': Product not found in database")
                continue

            for match in matches:
                inventory_item_id = item_number_to_id.get(match.inventory_item_number)
                if not inventory_item_id:
                    errors.append(
                        f"Match {product_hash[:30]} -> {match.inventory_item_number}: Inventory item not found"
                    )
                    continue

                try:
                    # Compute content hash for this match
                    content_hash = compute_content_hash(product, match)

                    # Check if match already exists by content hash
                    stmt = select(DBInventoryMatch).where(
                        DBInventoryMatch.content_hash == content_hash
                    )
                    existing = session.execute(stmt).first()

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

                    else:
                        # Match already exists, skip
                        skipped += 1

                    # Commit every 50 matches
                    if (inserted + updated) % 50 == 0 and (inserted + updated) > 0:
                        session.commit()

                except Exception as e:
                    errors.append(
                        f"Match {product_hash[:30]} -> {match.inventory_item_number}: {e}"
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
        "skipped": skipped,
        "errors": len(errors),
        "error_details": errors,
    }


def store_review_flags(review_flags: List[ReviewFlag], products: List[ProductMention]) -> dict:
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
                errors.append(f"Flag for '{flag.product_text[:50]}': Product not found in database")
                continue

            try:
                # Compute content hash for this flag
                content_hash = compute_content_hash(product_mention_id, flag)

                # Check if flag already exists by content hash
                stmt = select(MatchReviewFlag).where(MatchReviewFlag.content_hash == content_hash)
                existing = session.execute(stmt).first()

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
