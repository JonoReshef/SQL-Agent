"""Unit tests for inventory loader"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.inventory.loader import get_inventory_stats, load_inventory_excel


@pytest.fixture
def sample_inventory_excel(tmp_path):
    """Create a sample inventory Excel file for testing"""
    excel_path = tmp_path / "test_inventory.xlsx"

    # Create sample data
    data = {
        "Item #": ["ITEM-001", "ITEM-002", "ITEM-003", "ITEM-004"],
        "Description": [
            '1/2-13 x 2" Grade 8 Hex Bolt, Zinc Plated',
            '3/4-10 x 3" Grade 5 Hex Bolt',
            "M12 x 50mm Stainless Steel Bolt",
            "1/4-20 Lock Nut, Zinc",
        ],
        "Price": [1.50, 2.00, 3.50, 0.75],
        "Stock": [100, 50, 75, 200],
    }

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    return excel_path


@pytest.fixture
def invalid_inventory_excel(tmp_path):
    """Create an invalid inventory Excel file (missing columns)"""
    excel_path = tmp_path / "invalid_inventory.xlsx"

    data = {
        "Item": ["ITEM-001", "ITEM-002"],  # Wrong column name
        "Desc": ["Bolt", "Nut"],  # Wrong column name
    }

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    return excel_path


@pytest.mark.unit
def test_load_inventory_excel_success(sample_inventory_excel):
    """Test successful loading of inventory Excel"""
    items = load_inventory_excel(sample_inventory_excel)

    assert len(items) == 4
    assert items[0]["item_number"] == "ITEM-001"
    assert "Grade 8" in items[0]["raw_description"]
    assert items[1]["item_number"] == "ITEM-002"
    assert items[2]["item_number"] == "ITEM-003"
    assert items[3]["item_number"] == "ITEM-004"


@pytest.mark.unit
def test_load_inventory_excel_file_not_found():
    """Test error handling when file doesn't exist"""
    with pytest.raises(FileNotFoundError):
        load_inventory_excel("/nonexistent/path/inventory.xlsx")


@pytest.mark.unit
def test_load_inventory_excel_missing_columns(invalid_inventory_excel):
    """Test error handling when required columns are missing"""
    with pytest.raises(ValueError, match="Missing required columns"):
        load_inventory_excel(invalid_inventory_excel)


@pytest.mark.unit
def test_load_inventory_excel_with_empty_rows(tmp_path):
    """Test that empty rows are skipped"""
    excel_path = tmp_path / "inventory_with_empty.xlsx"

    data = {
        "Item #": ["ITEM-001", None, "ITEM-002", "", "ITEM-003"],
        "Description": [
            "Bolt",
            "Should be skipped",
            "Nut",
            "Also skipped",
            "Washer",
        ],
    }

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    items = load_inventory_excel(excel_path)

    # Only 3 valid items (rows with None or empty item numbers are skipped)
    assert len(items) == 3
    assert items[0]["item_number"] == "ITEM-001"
    assert items[1]["item_number"] == "ITEM-002"
    assert items[2]["item_number"] == "ITEM-003"


@pytest.mark.unit
def test_get_inventory_stats(sample_inventory_excel):
    """Test inventory statistics calculation"""
    items = load_inventory_excel(sample_inventory_excel)
    stats = get_inventory_stats(items)

    assert stats["total_items"] == 4
    assert stats["avg_description_length"] > 0
    assert stats["longest_description"] is not None
    assert stats["shortest_description"] is not None
    assert len(stats["shortest_description"]) <= len(stats["longest_description"])


@pytest.mark.unit
def test_get_inventory_stats_empty_list():
    """Test statistics with empty inventory list"""
    stats = get_inventory_stats([])

    assert stats["total_items"] == 0
    assert stats["avg_description_length"] == 0
    assert stats["longest_description"] is None
    assert stats["shortest_description"] is None


@pytest.mark.unit
def test_load_inventory_excel_strips_whitespace(tmp_path):
    """Test that item numbers and descriptions are stripped of whitespace"""
    excel_path = tmp_path / "inventory_whitespace.xlsx"

    data = {
        "Item #": ["  ITEM-001  ", "ITEM-002\n"],
        "Description": ["  Bolt with spaces  ", "Nut\t\n"],
    }

    df = pd.DataFrame(data)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    items = load_inventory_excel(excel_path)

    assert items[0]["item_number"] == "ITEM-001"
    assert items[0]["raw_description"] == "Bolt with spaces"
    assert items[1]["item_number"] == "ITEM-002"
    assert items[1]["raw_description"] == "Nut"


@pytest.mark.unit
def test_load_inventory_real_file_if_exists():
    """Test loading actual inventory file if it exists"""
    real_inventory_path = (
        Path(__file__).parent.parent / "data" / "Inventory" / "Item List.xlsx"
    )

    if not real_inventory_path.exists():
        pytest.skip("Real inventory file not available")

    items = load_inventory_excel(real_inventory_path)

    # Should have loaded some items
    assert len(items) > 0

    # All items should have required fields
    for item in items:
        assert "item_number" in item
        assert "raw_description" in item
        assert len(item["item_number"]) > 0
        assert len(item["raw_description"]) > 0

    # Print stats for information
    stats = get_inventory_stats(items)
    print(f"\nReal inventory stats: {stats}")
