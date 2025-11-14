-- ============================================================================
-- WestBrand Email Analysis System - Database Initialization Script
-- ============================================================================
-- Version: 2.0
-- Date: November 14, 2025
-- Description: Complete database schema for email product extraction and 
--              inventory matching system using PostgreSQL 17 with pgvector
--
-- This script creates all tables, indexes, constraints, and extensions
-- required for the WestBrand system to function.
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "vector";    -- For pgvector support

-- ============================================================================
-- TABLE: emails_processed
-- Purpose: Tracks processed .msg email files to avoid reprocessing
-- ============================================================================
CREATE TABLE IF NOT EXISTS emails_processed (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_hash VARCHAR(64) NOT NULL,  -- SHA256 hash for deduplication
    subject TEXT,
    sender VARCHAR(255),
    date_sent TIMESTAMP,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    report_file VARCHAR(500)  -- Path to generated Excel report
);

-- Create indexes for emails_processed
CREATE INDEX IF NOT EXISTS idx_email_file_hash ON emails_processed(file_hash);
CREATE INDEX IF NOT EXISTS idx_email_processed_at ON emails_processed(processed_at);

-- ============================================================================
-- TABLE: product_mentions
-- Purpose: Products extracted from emails via LLM
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_mentions (
    id SERIAL PRIMARY KEY,
    email_id INTEGER NOT NULL,
    
    -- Product identification
    exact_product_text TEXT NOT NULL,  -- Exact text snippet from email
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(255) NOT NULL,
    
    -- Properties stored as JSON array of objects
    -- Format: [{"name": "grade", "value": "8", "confidence": 0.95}, ...]
    properties JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Quantity and context
    quantity DOUBLE PRECISION,
    unit VARCHAR(50),
    context VARCHAR(100),
    requestor VARCHAR(255),
    date_requested VARCHAR(50),  -- Stored as string from extraction
    
    -- Extraction metadata
    extraction_confidence DOUBLE PRECISION,
    extracted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_product_email 
        FOREIGN KEY (email_id) 
        REFERENCES emails_processed(id) 
        ON DELETE CASCADE
);

-- Create indexes for product_mentions
CREATE INDEX IF NOT EXISTS idx_product_name ON product_mentions(product_name);
CREATE INDEX IF NOT EXISTS idx_product_category ON product_mentions(product_category);
CREATE INDEX IF NOT EXISTS idx_email_id ON product_mentions(email_id);
CREATE INDEX IF NOT EXISTS idx_product_properties ON product_mentions USING gin(properties);

-- ============================================================================
-- TABLE: inventory_items
-- Purpose: Inventory items parsed from Excel with LLM-extracted properties
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventory_items (
    id SERIAL PRIMARY KEY,
    item_number VARCHAR(100) NOT NULL UNIQUE,  -- From "Item #" column
    raw_description TEXT NOT NULL,  -- From "Description" column
    
    -- Parsed product information
    product_name VARCHAR(255),
    product_category VARCHAR(255),
    
    -- Properties stored as JSON array of objects
    -- Format: [{"name": "grade", "value": "8", "confidence": 0.95}, ...]
    properties JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Parsing metadata
    parse_confidence DOUBLE PRECISION,
    needs_manual_review BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for inventory_items
CREATE INDEX IF NOT EXISTS idx_item_number ON inventory_items(item_number);
CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(product_category);
CREATE INDEX IF NOT EXISTS idx_needs_review ON inventory_items(needs_manual_review);
CREATE INDEX IF NOT EXISTS idx_inventory_properties ON inventory_items USING gin(properties);

-- ============================================================================
-- TABLE: inventory_matches
-- Purpose: Fuzzy matches between email product mentions and inventory items
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventory_matches (
    id SERIAL PRIMARY KEY,
    product_mention_id INTEGER NOT NULL,
    inventory_item_id INTEGER NOT NULL,
    
    -- Match scoring (rapidfuzz Levenshtein distance)
    match_score DOUBLE PRECISION NOT NULL,  -- 0.0 to 1.0
    rank INTEGER NOT NULL,  -- 1 = best match, 2 = second best, etc.
    
    -- Match details stored as JSON arrays
    matched_properties JSONB DEFAULT '[]'::jsonb,  -- Properties that matched
    missing_properties JSONB DEFAULT '[]'::jsonb,  -- Properties in email but not inventory
    match_reasoning TEXT,  -- Human-readable explanation
    
    -- Metadata
    matched_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign keys
    CONSTRAINT fk_match_product_mention 
        FOREIGN KEY (product_mention_id) 
        REFERENCES product_mentions(id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_match_inventory_item 
        FOREIGN KEY (inventory_item_id) 
        REFERENCES inventory_items(id) 
        ON DELETE CASCADE
);

-- Create indexes for inventory_matches
CREATE INDEX IF NOT EXISTS idx_match_product_mention ON inventory_matches(product_mention_id);
CREATE INDEX IF NOT EXISTS idx_match_inventory_item ON inventory_matches(inventory_item_id);
CREATE INDEX IF NOT EXISTS idx_match_score ON inventory_matches(match_score);

-- ============================================================================
-- TABLE: match_review_flags
-- Purpose: Flags for matches requiring manual review (quality issues)
-- ============================================================================
CREATE TABLE IF NOT EXISTS match_review_flags (
    id SERIAL PRIMARY KEY,
    product_mention_id INTEGER NOT NULL,
    
    -- Flag details
    issue_type VARCHAR(50) NOT NULL,  -- INSUFFICIENT_DATA, AMBIGUOUS_MATCH, LOW_CONFIDENCE, NO_MATCH, etc.
    match_count INTEGER,  -- Number of matches found
    top_confidence DOUBLE PRECISION,  -- Highest match score
    reason TEXT NOT NULL,  -- Human-readable explanation
    action_needed TEXT,  -- Suggested action
    
    -- Resolution tracking
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    resolution_notes TEXT,
    
    -- Metadata
    flagged_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_flag_product_mention 
        FOREIGN KEY (product_mention_id) 
        REFERENCES product_mentions(id) 
        ON DELETE CASCADE
);

-- Create indexes for match_review_flags
CREATE INDEX IF NOT EXISTS idx_flag_product_mention ON match_review_flags(product_mention_id);
CREATE INDEX IF NOT EXISTS idx_flag_is_resolved ON match_review_flags(is_resolved);
CREATE INDEX IF NOT EXISTS idx_flag_issue_type ON match_review_flags(issue_type);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================
-- Grant all privileges to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "WestBrandService";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "WestBrandService";

-- Ensure future tables are also granted
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "WestBrandService";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "WestBrandService";

-- ============================================================================
-- VERIFICATION QUERIES (for testing)
-- ============================================================================
-- Uncomment to verify the schema was created correctly:
-- \dt
-- \d emails_processed
-- \d product_mentions
-- \d inventory_items
-- \d inventory_matches
-- \d match_review_flags

-- Count tables:
-- SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';

-- ============================================================================
-- END OF INITIALIZATION SCRIPT
-- ============================================================================
