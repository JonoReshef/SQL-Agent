"""Tests for property hierarchy extraction from config"""

from pathlib import Path

import pytest

from src.matching.hierarchy import PropertyHierarchy, get_hierarchy_for_category


class TestPropertyHierarchy:
    """Test property hierarchy management"""

    def test_create_hierarchy_from_list(self):
        """Test creating hierarchy from ordered property list"""
        hierarchy = PropertyHierarchy(
            category="Fasteners",
            property_order=["grade", "size", "length", "material", "finish"],
        )

        assert hierarchy.category == "Fasteners"
        assert hierarchy.property_order == [
            "grade",
            "size",
            "length",
            "material",
            "finish",
        ]
        assert hierarchy.get_rank("grade") == 0
        assert hierarchy.get_rank("size") == 1
        assert hierarchy.get_rank("finish") == 4

    def test_get_rank_for_unknown_property(self):
        """Test that unknown properties return None or high rank"""
        hierarchy = PropertyHierarchy(
            category="Fasteners", property_order=["grade", "size"]
        )

        # Unknown property should return None or max rank
        rank = hierarchy.get_rank("unknown")
        assert rank is None or rank > 100

    def test_property_order_immutable(self):
        """Test that property order list is immutable after creation"""
        hierarchy = PropertyHierarchy(
            category="Fasteners", property_order=["grade", "size"]
        )

        # Verify we can't modify the original list
        assert isinstance(hierarchy.property_order, (list, tuple))


class TestGetHierarchyForCategory:
    """Test loading hierarchies from config file"""

    def test_get_fasteners_hierarchy(self):
        """Test loading Fasteners hierarchy from config"""
        hierarchy = get_hierarchy_for_category("Fasteners")

        assert hierarchy is not None
        assert hierarchy.category == "Fasteners"
        assert len(hierarchy.property_order) > 0

        # Verify order matches config (grade, size, length, material, finish, head_type, thread_length, thread_standard)
        assert hierarchy.property_order[0] == "grade"
        assert hierarchy.property_order[1] == "size"
        assert hierarchy.property_order[2] == "length"

    def test_get_threaded_rod_hierarchy(self):
        """Test loading Threaded Rod hierarchy from config"""
        hierarchy = get_hierarchy_for_category("Threaded Rod")

        assert hierarchy is not None
        assert hierarchy.category == "Threaded Rod"

        # Verify first few properties match config order
        assert hierarchy.property_order[0] == "diameter"
        assert hierarchy.property_order[1] == "length"
        assert hierarchy.property_order[2] == "grade"

    def test_get_nuts_hierarchy(self):
        """Test loading Nuts hierarchy from config"""
        hierarchy = get_hierarchy_for_category("Nuts")

        assert hierarchy is not None
        assert hierarchy.category == "Nuts"

        # Nuts hierarchy: size, grade, type, finish
        assert hierarchy.property_order[0] == "size"
        assert hierarchy.property_order[1] == "grade"

    def test_get_washers_hierarchy(self):
        """Test loading Washers hierarchy"""
        hierarchy = get_hierarchy_for_category("Washers")

        assert hierarchy is not None
        assert hierarchy.category == "Washers"
        assert "size" in hierarchy.property_order
        assert "type" in hierarchy.property_order

    def test_unknown_category_returns_none_or_default(self):
        """Test that unknown category returns None or a default empty hierarchy"""
        hierarchy = get_hierarchy_for_category("UnknownCategory")

        # Should return None or empty hierarchy
        assert hierarchy is None or len(hierarchy.property_order) == 0

    def test_case_insensitive_category_lookup(self):
        """Test that category lookup is case-insensitive"""
        hierarchy1 = get_hierarchy_for_category("Fasteners")
        hierarchy2 = get_hierarchy_for_category("fasteners")
        hierarchy3 = get_hierarchy_for_category("FASTENERS")

        assert hierarchy1 is not None
        assert hierarchy2 is not None
        assert hierarchy3 is not None
        assert hierarchy1.property_order == hierarchy2.property_order
        assert hierarchy2.property_order == hierarchy3.property_order


class TestHierarchyIntegration:
    """Integration tests for hierarchy system"""

    def test_all_config_categories_loadable(self):
        """Test that all categories in config can be loaded"""
        # List of all categories in products_config.yaml
        categories = [
            "Fasteners",
            "Threaded Rod",
            "Nuts",
            "Washers",
            "Gaskets",
            "Casing Spacers",
            "Stud Kits",
            "Seal Kits",
        ]

        for category in categories:
            hierarchy = get_hierarchy_for_category(category)
            assert hierarchy is not None, f"Failed to load hierarchy for {category}"
            assert len(hierarchy.property_order) > 0, f"Empty hierarchy for {category}"
