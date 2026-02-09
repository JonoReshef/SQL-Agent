"""Mock data factories using Mimesis for realistic industrial supply data."""

import hashlib
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from mimesis import Address, Datetime, Numeric, Person, Text
from mimesis.locales import Locale


class MockDataFactory:
    """Base factory with shared utilities."""

    def __init__(self, seed: int | None = None):
        self.person = Person(Locale.EN, seed=seed)
        self.address = Address(Locale.EN, seed=seed)
        self.dt = Datetime(seed=seed)
        self.text = Text(Locale.EN, seed=seed)
        self.numeric = Numeric(seed=seed)
        self.rng = random.Random(seed)

        # Load archetypes
        archetypes_path = Path(__file__).parent / "archetypes.yaml"
        with open(archetypes_path) as f:
            self.archetypes = yaml.safe_load(f)

    def compute_hash(self, content: str) -> str:
        """Generate SHA256 hash for content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def fake_email(self) -> str:
        """Generate fake business email."""
        first = self.person.first_name().lower()
        last = self.person.last_name().lower()
        companies = [
            "acmesupply",
            "industrialparts",
            "bolthouse",
            "steelworks",
            "pipelineco",
            "valvesupply",
            "flangemart",
            "fastenerdepot",
            "metalworks",
            "heavyindustry",
            "oilfieldparts",
            "constructionsupply",
        ]
        company = self.rng.choice(companies)
        return f"{first}.{last}@{company}.example.com"

    def fake_company_name(self) -> str:
        """Generate fake industrial company name."""
        prefixes = [
            "Acme",
            "Industrial",
            "Western",
            "Northern",
            "Pacific",
            "Atlantic",
            "National",
            "Premier",
        ]
        types = [
            "Supply",
            "Parts",
            "Distribution",
            "Industries",
            "Manufacturing",
            "Solutions",
            "Services",
        ]
        return f"{self.rng.choice(prefixes)} {self.rng.choice(types)}"


class EmailFactory(MockDataFactory):
    """Factory for emails_processed records."""

    SUBJECT_TEMPLATES = [
        "RE: Quote Request - {product}",
        "FW: PO {po_number}",
        "RE: {product} Inquiry",
        "New order PO#{po_number}",
        "RE: Sales Order Acknowledgment for WO# {wo_number}",
        "FW: {product} Material",
        "RE: Quote {quote_number}",
        "RE: Freight Estimate",
        "{product} Quote Request",
        "FW: Order PO {po_number}",
    ]

    def create(self, index: int) -> dict[str, Any]:
        """Create a single email record."""
        products = ["Gasket", "Bolt", "Stud Kit", "Washer", "Threaded Rod", "Nut"]
        product = self.rng.choice(products)

        subject = self.rng.choice(self.SUBJECT_TEMPLATES).format(
            product=product,
            po_number=f"{self.numeric.integer_number(1000000, 9999999)}",
            wo_number=f"{self.numeric.integer_number(100000, 999999)}",
            quote_number=f"01-{self.numeric.integer_number(100000, 999999)}",
        )

        # Generate date within last 2 years
        date_sent = self.dt.datetime(start=2024, end=2026)

        # Generate file path
        fake_user = f"{self.person.first_name().lower()}@mockcompany.example.com"
        sanitized_subject = subject.replace(":", "").replace("/", "-")[:50]
        file_path = f"data/mock/{fake_user}/{sanitized_subject}.msg"

        thread_hash = self.compute_hash(f"{file_path}{subject}{index}")

        return {
            "thread_hash": thread_hash,
            "file_path": file_path,
            "subject": subject,
            "sender": self.fake_email(),
            "date_sent": date_sent,
            "processed_at": datetime.now(),
            "report_file": None,
        }


class InventoryItemFactory(MockDataFactory):
    """Factory for inventory_items records."""

    def __init__(self, seed: int | None = None):
        super().__init__(seed)
        self._item_counter = 0

    def create(self, category: str, index: int) -> dict[str, Any]:
        """Create a single inventory item for a category."""
        cat_config = self.archetypes["categories"].get(category, {})

        # Select item prefix and generate unique number using counter
        prefix = self.rng.choice(cat_config.get("item_prefixes", ["MOCK-"]))
        self._item_counter += 1
        item_number = f"{prefix}{self._item_counter:05d}"

        # Select product name
        product_name = self.rng.choice(cat_config.get("product_names", ["Unknown"]))

        # Generate properties
        properties = []
        for prop_name, prop_config in cat_config.get("properties", {}).items():
            if self.rng.random() > 0.2:  # 80% chance to include property
                properties.append(
                    {
                        "name": prop_name,
                        "value": self.rng.choice(
                            prop_config.get("values", ["unknown"])
                        ),
                        "value_type": prop_config.get("value_type", "description"),
                        "priority": prop_config.get("priority", 5),
                        "confidence": round(self.rng.uniform(0.85, 1.0), 2),
                    }
                )

        # Build raw description from properties
        desc_parts = []
        for prop in sorted(properties, key=lambda p: p.get("priority", 99)):
            desc_parts.append(prop["value"])
        desc_parts.append(product_name.upper())
        raw_description = " ".join(desc_parts)

        content_hash = self.compute_hash(f"{item_number}{raw_description}")

        return {
            "item_number": item_number,
            "raw_description": raw_description,
            "product_name": product_name,
            "product_category": category.replace("_", " ").title(),
            "properties": properties,
            "content_hash": content_hash,
            "parse_confidence": round(self.rng.uniform(0.85, 1.0), 2),
            "needs_manual_review": self.rng.random() < 0.05,
            "created_at": datetime.now(),
        }


class ProductMentionFactory(MockDataFactory):
    """Factory for product_mentions records."""

    CONTEXT_DISTRIBUTION = [
        ("quote_request", 0.38),
        ("quote_response", 0.16),
        ("price_request", 0.13),
        ("pricing_request", 0.09),
        ("purchase_order", 0.07),
        ("inquiry", 0.07),
        ("order", 0.06),
        ("rfq", 0.04),
    ]

    UNITS = ["pcs", "ea", "EA", "each", "PC", "pc", "kits", "kit", "pieces", "ft"]

    def create(
        self, email_thread_hash: str, category: str, index: int
    ) -> dict[str, Any]:
        """Create a product mention linked to an email."""
        cat_config = self.archetypes["categories"].get(category, {})
        product_name = self.rng.choice(cat_config.get("product_names", ["Unknown"]))

        # Build properties
        properties = []
        for prop_name, prop_config in cat_config.get("properties", {}).items():
            if self.rng.random() > 0.3:
                properties.append(
                    {
                        "name": prop_name,
                        "value": self.rng.choice(
                            prop_config.get("values", ["unknown"])
                        ),
                        "confidence": round(self.rng.uniform(0.7, 1.0), 2),
                    }
                )

        # Generate exact product text
        prop_values = " ".join([p["value"] for p in properties[:3]])
        quantity = self.rng.choice([10, 20, 25, 50, 100, 200, 500])
        unit = self.rng.choice(self.UNITS)
        exact_text = f"QTY {quantity} - {prop_values} {product_name}"

        # Select context based on distribution
        r = self.rng.random()
        cumulative = 0
        context = "inquiry"
        for ctx, prob in self.CONTEXT_DISTRIBUTION:
            cumulative += prob
            if r <= cumulative:
                context = ctx
                break

        content_hash = self.compute_hash(f"{email_thread_hash}{exact_text}{index}")

        return {
            "email_thread_hash": email_thread_hash,
            "exact_product_text": exact_text,
            "product_name": product_name,
            "product_category": category.replace("_", " ").title(),
            "properties": properties,
            "content_hash": content_hash,
            "quantity": float(quantity),
            "unit": unit,
            "context": context,
            "requestor": self.fake_email()
            if self.rng.random() > 0.3
            else self.person.full_name(),
            "date_requested": self.dt.date(start=2024, end=2026).isoformat(),
            "extraction_confidence": round(self.rng.uniform(0.7, 1.0), 2)
            if self.rng.random() > 0.2
            else None,
            "extracted_at": datetime.now(),
        }


class InventoryMatchFactory(MockDataFactory):
    """Factory for inventory_matches records."""

    # Real distribution: 30% at 0.50-0.60, 35% at 0.60-0.70, 17% at 0.70-0.80, 13% at 0.80-0.90, 6% at 0.90-1.0
    SCORE_DISTRIBUTION = [
        ((0.50, 0.60), 0.30),
        ((0.60, 0.70), 0.35),
        ((0.70, 0.80), 0.17),
        ((0.80, 0.90), 0.13),
        ((0.90, 1.00), 0.06),
    ]

    PROPERTY_NAMES = [
        "grade",
        "size",
        "length",
        "material",
        "finish",
        "pressure_rating",
        "type",
        "standard",
    ]

    def create(
        self, product_mention_id: int, inventory_item_id: int, rank: int
    ) -> dict[str, Any]:
        """Create an inventory match record."""
        # Select score based on distribution
        r = self.rng.random()
        cumulative = 0
        score_range = (0.50, 0.60)
        for range_, prob in self.SCORE_DISTRIBUTION:
            cumulative += prob
            if r <= cumulative:
                score_range = range_
                break

        score = round(self.rng.uniform(*score_range), 4)

        # Generate matched/missing properties
        all_props = self.rng.sample(
            self.PROPERTY_NAMES, min(5, len(self.PROPERTY_NAMES))
        )
        split_point = self.rng.randint(0, len(all_props))
        matched = all_props[:split_point]
        missing = all_props[split_point:]

        # Generate reasoning
        name_sim = round(self.rng.uniform(0.7, 1.0), 2)
        reasoning = f"Name similarity: {name_sim}. Category match: 1.00."
        if missing:
            reasoning += f" Missing properties: {', '.join(missing)}."

        content_hash = self.compute_hash(
            f"{product_mention_id}{inventory_item_id}{rank}"
        )

        return {
            "product_mention_id": product_mention_id,
            "inventory_item_id": inventory_item_id,
            "match_score": score,
            "rank": rank,
            "content_hash": content_hash,
            "matched_properties": matched,
            "missing_properties": missing,
            "match_reasoning": reasoning,
            "matched_at": datetime.now(),
        }


class ReviewFlagFactory(MockDataFactory):
    """Factory for match_review_flags records."""

    # Real distribution: 55% INSUFFICIENT_DATA, 32% LOW_CONFIDENCE, 13% AMBIGUOUS_MATCH
    ISSUE_DISTRIBUTION = [
        ("INSUFFICIENT_DATA", 0.55),
        ("LOW_CONFIDENCE", 0.32),
        ("AMBIGUOUS_MATCH", 0.13),
    ]

    REASONS = {
        "INSUFFICIENT_DATA": "No inventory matches found above minimum threshold",
        "LOW_CONFIDENCE": "Top match confidence below acceptable threshold",
        "AMBIGUOUS_MATCH": "Multiple matches with similar confidence scores",
    }

    ACTIONS = {
        "INSUFFICIENT_DATA": "Manual inventory search or create new inventory item",
        "LOW_CONFIDENCE": "Review match with inventory item {item}",
        "AMBIGUOUS_MATCH": "Verify best match between {item1} and {item2}",
    }

    def create(
        self, product_mention_id: int, inventory_item_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """Create a review flag record."""
        # Select issue type
        r = self.rng.random()
        cumulative = 0
        issue_type = "INSUFFICIENT_DATA"
        for issue, prob in self.ISSUE_DISTRIBUTION:
            cumulative += prob
            if r <= cumulative:
                issue_type = issue
                break

        reason = self.REASONS[issue_type]

        # Generate action
        if (
            issue_type == "AMBIGUOUS_MATCH"
            and inventory_item_ids
            and len(inventory_item_ids) >= 2
        ):
            action = self.ACTIONS[issue_type].format(
                item1=f"MOCK-{self.numeric.integer_number(1000, 9999)}",
                item2=f"MOCK-{self.numeric.integer_number(1000, 9999)}",
            )
        elif issue_type == "LOW_CONFIDENCE":
            action = self.ACTIONS[issue_type].format(
                item=f"MOCK-{self.numeric.integer_number(1000, 9999)}"
            )
        else:
            action = self.ACTIONS[issue_type]

        content_hash = self.compute_hash(f"{product_mention_id}{issue_type}{reason}")

        match_count = 0 if issue_type == "INSUFFICIENT_DATA" else self.rng.randint(1, 5)
        top_conf = (
            None
            if issue_type == "INSUFFICIENT_DATA"
            else round(self.rng.uniform(0.4, 0.7), 2)
        )

        return {
            "product_mention_id": product_mention_id,
            "issue_type": issue_type,
            "match_count": match_count,
            "top_confidence": top_conf,
            "reason": reason,
            "action_needed": action,
            "content_hash": content_hash,
            "is_resolved": self.rng.random() < 0.1,
            "resolved_at": None,
            "resolved_by": None,
            "resolution_notes": None,
            "flagged_at": datetime.now(),
        }
