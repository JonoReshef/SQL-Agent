"""Models for the config file"""

from typing import List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from src.models.product import ValueTypes


class PropertyDefinition(BaseModel):
    """Definition of a product property"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "grade",
                "examples": ["8", "5", "A490"],
                "value_type": "measurement",
                "priority": 1,
            }
        }
    )

    name: str = Field(..., description="Property name (e.g., 'grade', 'size')")
    examples: List[str] = Field(default_factory=list, description="Example values")
    value_type: str = Field(
        default="description",
        description="Type of the property value (e.g., 'measurement', 'description')",
    )
    priority: int = Field(
        default=10,
        description="Priority for hierarchical filtering (lower = higher priority)",
    )


class ProductDefinition(BaseModel):
    """Definition of a product type"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Fasteners",
                "category": "Fasteners",
                "aliases": ["bolts", "nuts", "screws"],
                "properties": [
                    {"name": "grade", "type": "string", "examples": ["8", "5"]}
                ],
            }
        }
    )

    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    properties: List[PropertyDefinition] = Field(
        default_factory=list, description="Product properties"
    )


class ExtractionRules(BaseModel):
    """Rules for extracting information from emails"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity_patterns": ["\\d+ pcs", "\\d+ pieces"],
                "date_formats": ["%m/%d/%Y", "%d-%m-%Y"],
            }
        }
    )

    quantity_patterns: List[str] = Field(
        default_factory=list, description="Regex patterns for quantity extraction"
    )
    date_formats: List[str] = Field(
        default_factory=list, description="Date format strings for parsing"
    )


class ProductConfig(BaseModel):
    """Complete product configuration"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "products": [],
                "extraction_rules": {"quantity_patterns": [], "date_formats": []},
            }
        }
    )

    products: List[ProductDefinition] = Field(
        ..., description="List of product definitions"
    )
    extraction_rules: ExtractionRules = Field(..., description="Extraction rules")

    def get_product_by_name(self, name: str) -> Optional[ProductDefinition]:
        """
        Find a product by name or alias (case-insensitive).

        Args:
            name: Product name or alias to search for

        Returns:
            ProductDefinition if found, None otherwise
        """
        name_lower = name.lower().strip()

        for product in self.products:
            # Check exact name match
            if product.name.lower() == name_lower:
                return product

            # Check aliases
            if any(alias.lower() == name_lower for alias in product.aliases):
                return product

        return None

    def get_all_property_names(self) -> Set[str]:
        """
        Get all unique property names across all products.

        Returns:
            Set of property names
        """
        property_names = set()

        for product in self.products:
            for prop in product.properties:
                property_names.add(prop.name)

        return property_names

    def get_property_metadata(
        self, category: str, property_name: str
    ) -> tuple[ValueTypes, int]:
        """
        Get value_type and priority for a property within a category.

        Args:
            category: Product category
            property_name: Name of the property

        Returns:
            Tuple of (value_type, priority)
            Defaults to ("description", 10) if not found
        """
        # Find product by category
        product = None
        for p in self.products:
            if p.category.lower() == category.lower():
                product = p
                break

        if not product:
            return ("description", 10)

        # Find property definition
        property_name_lower = property_name.lower()
        for prop_def in product.properties:
            if prop_def.name.lower() == property_name_lower:
                prod_def_value_type: ValueTypes = prop_def.value_type  # type: ignore
                return (prod_def_value_type, prop_def.priority)

        return ("description", 10)
