"""SQLAlchemy database models for WestBrand system"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class EmailProcessed(Base):
    """Tracks processed .msg email files"""

    __tablename__ = "emails_processed"

    thread_hash = Column(String(64), primary_key=True)  # SHA256 hash - natural PK
    file_path = Column(String(500), nullable=False)
    subject = Column(Text)
    sender = Column(String(255))
    date_sent = Column(DateTime)
    processed_at = Column(DateTime, default=func.now(), nullable=False)
    report_file = Column(String(500))  # Excel report path

    # Relationships
    product_mentions = relationship(
        "ProductMention", back_populates="email", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_email_file_path", "file_path"),
        Index("idx_email_processed_at", "processed_at"),
    )


class ProductMention(Base):
    """Products extracted from emails"""

    __tablename__ = "product_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_thread_hash = Column(
        String(64), ForeignKey("emails_processed.thread_hash"), nullable=False
    )

    # Product identification
    exact_product_text = Column(Text, nullable=False)
    product_name = Column(String(255), nullable=False)
    product_category = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 of all content

    # Properties stored as JSON: [{"name": "grade", "value": "8", "confidence": 0.95}]
    properties = Column(JSON, nullable=False, default=list)

    # Quantity and context
    quantity = Column(Float)
    unit = Column(String(50))
    context = Column(String(100))
    requestor = Column(String(255))
    date_requested = Column(String(50))  # Stored as string from extraction

    # Extraction metadata
    extraction_confidence = Column(Float)
    extracted_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    email = relationship("EmailProcessed", back_populates="product_mentions")
    inventory_matches = relationship(
        "InventoryMatch", back_populates="product_mention", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_product_name", "product_name"),
        Index("idx_product_category", "product_category"),
        Index("idx_email_thread_hash", "email_thread_hash"),
        Index("idx_product_content_hash", "content_hash"),
    )


class InventoryItem(Base):
    """Inventory items parsed from Excel"""

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_number = Column(String(100), nullable=False, unique=True)  # From "Item #"
    raw_description = Column(Text, nullable=False)  # From "Description" column

    # Parsed product information
    product_name = Column(String(255))
    product_category = Column(String(255))
    content_hash = Column(String(64), nullable=False)  # SHA256 of parsed content
    value_type = Column(String(50))  # e.g., "measurement", "description"
    priority = Column(Integer)  # Lower = higher priority

    # Properties stored as JSON: [{"name": "grade", "value": "8", "confidence": 0.95}]
    properties = Column(JSON, nullable=False, default=list)

    # Parsing metadata
    parse_confidence = Column(Float)
    needs_manual_review = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    matches = relationship(
        "InventoryMatch", back_populates="inventory_item", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_item_number", "item_number"),
        Index("idx_inventory_category", "product_category"),
        Index("idx_needs_review", "needs_manual_review"),
        Index("idx_inventory_content_hash", "content_hash"),
    )


class InventoryMatch(Base):
    """Matches between email product mentions and inventory items"""

    __tablename__ = "inventory_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_mention_id = Column(
        Integer, ForeignKey("product_mentions.id"), nullable=False
    )
    inventory_item_id = Column(
        Integer, ForeignKey("inventory_items.id"), nullable=False
    )

    # Match scoring
    match_score = Column(Float, nullable=False)  # 0.0 to 1.0
    rank = Column(Integer, nullable=False)  # 1 = best match
    content_hash = Column(String(64), nullable=False)  # SHA256 of match content

    # Match details
    matched_properties = Column(
        JSON, default=list
    )  # List of property names that matched
    missing_properties = Column(
        JSON, default=list
    )  # Properties in email but not inventory
    match_reasoning = Column(Text)  # Human-readable explanation

    # Metadata
    matched_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    product_mention = relationship("ProductMention", back_populates="inventory_matches")
    inventory_item = relationship("InventoryItem", back_populates="matches")

    # Indexes
    __table_args__ = (
        Index("idx_match_product_mention", "product_mention_id"),
        Index("idx_match_inventory_item", "inventory_item_id"),
        Index("idx_match_score", "match_score"),
        Index("idx_match_content_hash", "content_hash"),
    )


class MatchReviewFlag(Base):
    """Flags for matches requiring manual review"""

    __tablename__ = "match_review_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_mention_id = Column(
        Integer, ForeignKey("product_mentions.id"), nullable=False
    )

    # Flag details
    issue_type = Column(
        String(50), nullable=False
    )  # INSUFFICIENT_DATA, AMBIGUOUS_MATCH, LOW_CONFIDENCE, TOO_MANY_MATCHES
    match_count = Column(Integer)
    top_confidence = Column(Float)
    reason = Column(Text, nullable=False)
    action_needed = Column(Text)
    content_hash = Column(String(64), nullable=False)  # SHA256 of flag content

    # Resolution tracking
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolution_notes = Column(Text)

    # Metadata
    flagged_at = Column(DateTime, default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_flag_product_mention", "product_mention_id"),
        Index("idx_flag_is_resolved", "is_resolved"),
        Index("idx_flag_issue_type", "issue_type"),
        Index("idx_flag_content_hash", "content_hash"),
    )


def create_all_tables(engine):
    """
    Create all database tables.

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """
    Drop all database tables. Use with caution!

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)
