"""
Date utility functions for consistent date handling across the application.

This module provides standardized date parsing and formatting to handle
the mismatch between Python datetime objects and PostgreSQL DATE/TIMESTAMP types.
"""

from typing import Optional, Union
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def parse_date_safe(
    value: Union[str, datetime, date, None],
    default: Optional[date] = None
) -> Optional[date]:
    """
    Safely parse various date formats into a Python date object.
    
    Handles:
    - ISO format strings (YYYY-MM-DD)
    - datetime objects (extracts date)
    - date objects (returns as-is)
    - None (returns default)
    
    Args:
        value: Date value to parse
        default: Default value to return if parsing fails
        
    Returns:
        datetime.date or default
    """
    if value is None:
        return default
    
    # Already a date
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    
    # datetime - extract date
    if isinstance(value, datetime):
        return value.date()
    
    # String parsing
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
        
        # Try ISO format first (YYYY-MM-DD)
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
        
        # Try datetime ISO format (YYYY-MM-DDTHH:MM:SS)
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.date()
        except ValueError:
            pass
        
        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%Y/%m/%d',
            '%d %b %Y',
            '%d %B %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date string: {value}")
    
    return default


def format_date_for_db(value: Optional[date]) -> Optional[str]:
    """
    Format a date for PostgreSQL storage.
    
    PostgreSQL accepts ISO format (YYYY-MM-DD) for DATE columns.
    
    Args:
        value: Date to format
        
    Returns:
        ISO format string or None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        value = value.date()
    
    if isinstance(value, date):
        return value.isoformat()
    
    logger.warning(f"Unexpected date type: {type(value)}")
    return None


def datetime_to_date(value: Optional[datetime]) -> Optional[date]:
    """
    Convert datetime to date safely.
    
    Args:
        value: datetime object or None
        
    Returns:
        date object or None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, date):
        return value
    
    logger.warning(f"Cannot convert {type(value)} to date")
    return None


def validate_date_range(
    value: date,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
) -> bool:
    """
    Validate that a date falls within an acceptable range.
    
    Args:
        value: Date to validate
        min_date: Minimum acceptable date (inclusive)
        max_date: Maximum acceptable date (inclusive)
        
    Returns:
        True if valid, False otherwise
    """
    if min_date is not None and value < min_date:
        return False
    
    if max_date is not None and value > max_date:
        return False
    
    return True


def get_safe_publication_date(
    year: Optional[int],
    month: Optional[int] = None,
    day: Optional[int] = None,
    default: Optional[date] = None
) -> Optional[date]:
    """
    Create a publication date from year/month/day with validation.
    
    Handles incomplete dates (e.g., only year known) by using defaults.
    
    Args:
        year: Publication year
        month: Publication month (1-12, defaults to 1)
        day: Publication day (1-31, defaults to 1)
        default: Default value if creation fails
        
    Returns:
        datetime.date or default
    """
    if year is None:
        return default
    
    # Validate year is reasonable (scientific publications)
    current_year = datetime.now().year
    if year < 1900 or year > current_year + 1:
        logger.warning(f"Suspicious publication year: {year}")
        return default
    
    # Use safe defaults for missing month/day
    month = max(1, min(12, month)) if month is not None else 1
    day = max(1, min(31, day)) if day is not None else 1
    
    try:
        return date(year, month, day)
    except ValueError as e:
        logger.warning(f"Invalid date ({year}-{month}-{day}): {e}")
        return default
