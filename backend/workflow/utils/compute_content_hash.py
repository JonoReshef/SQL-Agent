import hashlib
import json

from pydantic import BaseModel


def compute_content_hash(*args, len=16) -> str:
    """
    Compute SHA256 hash of content for duplicate detection.

    Args:
        *args: Variable arguments to include in hash
        len: Length of the returned hash string (default 16)

    Returns:
        Hex string of SHA256 hash
    """
    # Create a deterministic string representation
    content_parts = []
    for arg in args:
        if arg is None:
            content_parts.append("NULL")
        elif isinstance(arg, BaseModel):
            # For Pydantic models, use mode='json' to handle datetime objects
            content_parts.append(json.dumps(arg.model_dump(mode="json"), sort_keys=True))
        elif isinstance(arg, (dict, list)):
            # For JSON-serializable objects, use sorted JSON
            content_parts.append(json.dumps(arg, sort_keys=True, default=str))
        else:
            content_parts.append(str(arg))

    content_str = "|".join(content_parts)
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()[:len]
