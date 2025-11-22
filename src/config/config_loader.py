"""Configuration loader for product definitions and extraction rules"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from src.models.configs import ProductConfig


def load_config(config_path: Optional[Path] = None) -> ProductConfig:
    """
    Load product configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, uses default.

    Returns:
        ProductConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if config_path is None:
        config_path = Path("config/products_config.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    # Validate and create ProductConfig
    config = ProductConfig(**config_data)

    return config


def format_config(config: ProductConfig) -> str:
    """
    Format ProductConfig as a YAML string.

    Args:
        config: ProductConfig object
    Returns:
        YAML string representation
    """
    # Build product definitions section
    products_info = []
    for product in config.products:
        products_info.append(
            f"Product {product.name} which is in the category {product.category} has the following aliases: {', '.join(product.aliases)}. The below are the valid properties of {product.name} (with examples): "
        )
        for property in product.properties:
            products_info.append(
                f"-- {property.name} has the following examples: {', '.join(property.examples)}"
            )
        products_info.append("\n-----\n")

    products_section = "\n".join(products_info)

    return products_section


def reload_config(config_path: Optional[Path] = None) -> ProductConfig:
    """
    Force reload of configuration (clears cache).

    Args:
        config_path: Path to configuration file

    Returns:
        ProductConfig object
    """
    return load_config(config_path)


if __name__ == "__main__":
    # Example usage
    config_text = load_config()
    print("Loaded Product Configuration:")
    print(config_text)
