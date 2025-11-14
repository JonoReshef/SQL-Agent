"""Unit tests for configuration loading"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from src.config.config_loader import (
    ProductConfig,
    load_config,
)
from src.models.configs import ExtractionRules, ProductDefinition, PropertyDefinition


class TestConfigLoader:
    """Test suite for configuration loading"""

    @pytest.mark.unit
    def test_load_config_basic(self):
        """Test loading basic configuration"""
        config_path = Path("config/products_config.yaml")

        if not config_path.exists():
            pytest.skip(f"Config file not found: {config_path}")

        config = load_config(config_path)

        # Verify structure
        assert isinstance(config, ProductConfig)
        assert hasattr(config, "products")
        assert hasattr(config, "extraction_rules")
        assert len(config.products) > 0

    @pytest.mark.unit
    def test_product_definition_structure(self):
        """Test product definition fields"""
        config = load_config()

        for product in config.products:
            assert isinstance(product, ProductDefinition)
            assert isinstance(product.name, str)
            assert isinstance(product.category, str)
            assert isinstance(product.aliases, list)
            assert isinstance(product.properties, list)
            assert len(product.name) > 0

    @pytest.mark.unit
    def test_property_definition_structure(self):
        """Test property definition fields"""
        config = load_config()

        for product in config.products:
            for prop in product.properties:
                assert isinstance(prop, PropertyDefinition)
                assert isinstance(prop.name, str)
                assert isinstance(prop.type, str)
                assert len(prop.name) > 0

    @pytest.mark.unit
    def test_extraction_rules_structure(self):
        """Test extraction rules fields"""
        config = load_config()

        assert isinstance(config.extraction_rules, ExtractionRules)
        assert hasattr(config.extraction_rules, "quantity_patterns")
        assert hasattr(config.extraction_rules, "date_formats")

        if config.extraction_rules.quantity_patterns:
            assert isinstance(config.extraction_rules.quantity_patterns, list)

        if config.extraction_rules.date_formats:
            assert isinstance(config.extraction_rules.date_formats, list)

    @pytest.mark.unit
    def test_config_caching(self):
        """Test that config is cached on subsequent loads"""
        config1 = load_config()
        config2 = load_config()

        # Should be same object (cached)
        assert config1 is config2

    @pytest.mark.unit
    def test_load_config_nonexistent_file(self):
        """Test handling of nonexistent config file"""
        fake_path = Path("config/nonexistent.yaml")

        with pytest.raises(FileNotFoundError):
            load_config(fake_path)

    @pytest.mark.unit
    def test_get_product_by_name(self):
        """Test finding products by exact name"""
        config = load_config()

        # Should find product by exact name
        for product in config.products:
            found = config.get_product_by_name(product.name)
            assert found is not None
            # When searching by exact name, should return that product
            assert (
                found.name.lower() == product.name.lower()
                or product.name.lower() in [a.lower() for a in found.aliases]
            )

    @pytest.mark.unit
    def test_get_product_by_alias(self):
        """Test finding products by alias"""
        config = load_config()

        # Find a product with aliases
        for product in config.products:
            if product.aliases:
                found = config.get_product_by_name(product.aliases[0])
                assert found is not None
                assert product.aliases[0] in found.aliases

    @pytest.mark.unit
    def test_case_insensitive_product_lookup(self):
        """Test case-insensitive product name lookup"""
        config = load_config()

        for product in config.products:
            # Try uppercase
            found = config.get_product_by_name(product.name.upper())
            assert found is not None

            # Try lowercase
            found = config.get_product_by_name(product.name.lower())
            assert found is not None

    @pytest.mark.unit
    def test_get_all_property_names(self):
        """Test getting all unique property names"""
        config = load_config()

        property_names = config.get_all_property_names()

        assert isinstance(property_names, set)
        assert len(property_names) > 0

        # Should include common properties
        # (This will pass as long as config defines any properties)
        assert all(isinstance(name, str) for name in property_names)


class TestProductConfigModel:
    """Test Pydantic models for configuration"""

    @pytest.mark.unit
    def test_product_definition_validation(self):
        """Test ProductDefinition model validation"""
        product = ProductDefinition(
            name="Test Product",
            category="Test Category",
            aliases=["alias1", "alias2"],
            properties=[
                PropertyDefinition(name="size", type="string", examples=["10mm"])
            ],
        )

        assert product.name == "Test Product"
        assert len(product.aliases) == 2
        assert len(product.properties) == 1

    @pytest.mark.unit
    def test_property_definition_validation(self):
        """Test PropertyDefinition model validation"""
        prop = PropertyDefinition(
            name="grade", type="string", examples=["8", "5", "A490"]
        )

        assert prop.name == "grade"
        assert prop.type == "string"
        assert len(prop.examples) == 3

    @pytest.mark.unit
    def test_property_definition_optional_examples(self):
        """Test that examples is optional"""
        prop = PropertyDefinition(name="color", type="string")

        assert prop.name == "color"
        assert prop.examples == []

    @pytest.mark.unit
    def test_extraction_rules_validation(self):
        """Test ExtractionRules model validation"""
        rules = ExtractionRules(
            quantity_patterns=["\\d+ pcs", "\\d+ pieces"],
            date_formats=["%m/%d/%Y", "%d-%m-%Y"],
        )

        assert len(rules.quantity_patterns) == 2
        assert len(rules.date_formats) == 2

    @pytest.mark.unit
    def test_product_config_serialization(self):
        """Test config serialization to dict"""
        config = load_config()

        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert "products" in config_dict
        assert "extraction_rules" in config_dict
        assert isinstance(config_dict["products"], list)
