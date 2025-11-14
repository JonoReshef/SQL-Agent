"""Configuration loader for product definitions and extraction rules"""

import yaml
from pathlib import Path
from typing import Optional
from functools import lru_cache

from src.models.configs import ProductConfig


@lru_cache(maxsize=1)
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


def reload_config(config_path: Optional[Path] = None) -> ProductConfig:
    """
    Force reload of configuration (clears cache).

    Args:
        config_path: Path to configuration file

    Returns:
        ProductConfig object
    """
    load_config.cache_clear()
    return load_config(config_path)
