"""Inventory Excel file loader"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any


def load_inventory_excel(file_path: Path | str) -> List[Dict[str, Any]]:
    """
    Load inventory items from Excel file.
    
    Args:
        file_path: Path to Item List.xlsx
        
    Returns:
        List of dictionaries with item_number and raw_description
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {file_path}")
    
    # Read Excel file
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")
    
    # Check for required columns
    required_columns = ["Item #", "Description"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"Available columns: {list(df.columns)}"
        )
    
    # Convert to list of dictionaries
    inventory_items = []
    
    for _, row in df.iterrows():
        item_number = str(row["Item #"]).strip()
        description = str(row["Description"]).strip()
        
        # Skip rows with empty or invalid data
        if not item_number or item_number.lower() in ["nan", "none", ""]:
            continue
        if not description or description.lower() in ["nan", "none", ""]:
            continue
        
        inventory_items.append({
            "item_number": item_number,
            "raw_description": description,
        })
    
    return inventory_items


def get_inventory_stats(inventory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about inventory items.
    
    Args:
        inventory_items: List of inventory item dictionaries
        
    Returns:
        Dictionary with statistics
    """
    total = len(inventory_items)
    
    # Calculate average description length
    avg_length = sum(len(item["raw_description"]) for item in inventory_items) / total if total > 0 else 0
    
    # Find longest and shortest descriptions
    if total > 0:
        longest = max(inventory_items, key=lambda x: len(x["raw_description"]))
        shortest = min(inventory_items, key=lambda x: len(x["raw_description"]))
    else:
        longest = shortest = None
    
    return {
        "total_items": total,
        "avg_description_length": round(avg_length, 1),
        "longest_description": longest["raw_description"] if longest else None,
        "shortest_description": shortest["raw_description"] if shortest else None,
    }
