"""
Data cleaning utilities for F1 project.
Provides functions to clean and normalize data before database insertion.

Authors: David & Alberto
"""

from datetime import datetime
from typing import Optional, Union


def clean_string(value: Optional[str]) -> Optional[str]:
    """
    Clean and normalize a string value.
    Trims whitespace and handles None/empty values.

    Args:
        value: String value to clean

    Returns:
        Cleaned string or None if value is None/empty
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    cleaned = value.strip()

    if cleaned == "":
        return None

    return cleaned


def clean_date(date_str: Optional[str]) -> Optional[int]:
    """
    Parse a date string and convert to YYYYMMDD integer format.
    This prevents duplicate date strings in the database.

    Args:
        date_str: Date string in format 'YYYY-MM-DD' or similar

    Returns:
        Integer in YYYYMMDD format or None if invalid
    """
    if date_str is None:
        return None

    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    if date_str == "":
        return None

    try:
        # Try parsing common date formats
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Convert to YYYYMMDD integer
                return int(dt.strftime("%Y%m%d"))
            except ValueError:
                continue

        # If no format matches, return None
        return None
    except Exception:
        return None


def clean_integer(value: Optional[Union[int, str, float]]) -> Optional[int]:
    """
    Clean and validate an integer value.

    Args:
        value: Value to convert to integer

    Returns:
        Integer value or None if invalid
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value) if not (value != value) else None  # Check for NaN

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        try:
            return int(float(value))  # Use float first to handle "1.0" strings
        except (ValueError, TypeError):
            return None

    return None


def clean_float(value: Optional[Union[int, str, float]]) -> Optional[float]:
    """
    Clean and validate a float value.

    Args:
        value: Value to convert to float

    Returns:
        Float value or None if invalid
    """
    if value is None:
        return None

    if isinstance(value, float):
        return value if value == value else None  # Check for NaN

    if isinstance(value, int):
        return float(value)

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    return None




