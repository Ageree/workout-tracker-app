"""
Tests for date utility functions.
"""

import pytest
from datetime import datetime, date
from utils.date_utils import (
    parse_date_safe,
    format_date_for_db,
    datetime_to_date,
    get_safe_publication_date
)


class TestParseDateSafe:
    """Test parse_date_safe function."""
    
    def test_parse_date_safe_iso_string(self):
        """Test parsing ISO date string."""
        result = parse_date_safe('2024-01-15')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_safe_datetime_object(self):
        """Test parsing datetime object."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = parse_date_safe(dt)
        assert result == date(2024, 1, 15)
    
    def test_parse_date_safe_date_object(self):
        """Test parsing date object (returns as-is)."""
        d = date(2024, 1, 15)
        result = parse_date_safe(d)
        assert result == d
        assert result is d  # Should be same object
    
    def test_parse_date_safe_none(self):
        """Test parsing None returns default."""
        result = parse_date_safe(None)
        assert result is None
    
    def test_parse_date_safe_none_with_default(self):
        """Test parsing None returns custom default."""
        default_date = date(2020, 1, 1)
        result = parse_date_safe(None, default=default_date)
        assert result == default_date
    
    def test_parse_date_safe_empty_string(self):
        """Test parsing empty string returns default."""
        result = parse_date_safe('')
        assert result is None
    
    def test_parse_date_safe_whitespace_string(self):
        """Test parsing whitespace string returns default."""
        result = parse_date_safe('   ')
        assert result is None
    
    def test_parse_date_safe_datetime_iso_string(self):
        """Test parsing datetime ISO format string."""
        result = parse_date_safe('2024-01-15T10:30:00')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_safe_datetime_iso_string_with_z(self):
        """Test parsing datetime ISO format with Z."""
        result = parse_date_safe('2024-01-15T10:30:00Z')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_safe_common_formats(self):
        """Test parsing various common date formats."""
        formats = [
            ('2024-01-15 10:30:00', date(2024, 1, 15)),
            ('15/01/2024', date(2024, 1, 15)),
            ('01/15/2024', date(2024, 1, 15)),
            ('15-01-2024', date(2024, 1, 15)),
            ('2024/01/15', date(2024, 1, 15)),
        ]
        
        for date_str, expected in formats:
            result = parse_date_safe(date_str)
            assert result == expected, f"Failed for format: {date_str}"
    
    def test_parse_date_safe_invalid_string(self):
        """Test parsing invalid string returns default."""
        result = parse_date_safe('not-a-date')
        assert result is None


class TestFormatDateForDb:
    """Test format_date_for_db function."""
    
    def test_format_date_for_db_date(self):
        """Test formatting date for database."""
        result = format_date_for_db(date(2024, 1, 15))
        assert result == '2024-01-15'
    
    def test_format_date_for_db_datetime(self):
        """Test formatting datetime for database."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_date_for_db(dt)
        assert result == '2024-01-15'
    
    def test_format_date_for_db_none(self):
        """Test formatting None returns None."""
        result = format_date_for_db(None)
        assert result is None


class TestDatetimeToDate:
    """Test datetime_to_date function."""
    
    def test_datetime_to_date_datetime(self):
        """Test converting datetime to date."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = datetime_to_date(dt)
        assert result == date(2024, 1, 15)
    
    def test_datetime_to_date_date(self):
        """Test converting date returns same date."""
        d = date(2024, 1, 15)
        result = datetime_to_date(d)
        assert result == d
    
    def test_datetime_to_date_none(self):
        """Test converting None returns None."""
        result = datetime_to_date(None)
        assert result is None
    
    def test_datetime_to_date_string(self):
        """Test converting string returns parsed date."""
        result = datetime_to_date('2024-01-15')
        assert result == date(2024, 1, 15)


class TestGetSafePublicationDate:
    """Test get_safe_publication_date function."""
    
    def test_get_safe_publication_date_valid(self):
        """Test creating valid publication date."""
        result = get_safe_publication_date(2024, 1, 15)
        assert result == date(2024, 1, 15)
    
    def test_get_safe_publication_date_year_only(self):
        """Test creating date with year only."""
        result = get_safe_publication_date(2024)
        assert result == date(2024, 1, 1)
    
    def test_get_safe_publication_date_year_month(self):
        """Test creating date with year and month."""
        result = get_safe_publication_date(2024, 6)
        assert result == date(2024, 6, 1)
    
    def test_get_safe_publication_date_invalid_year_too_old(self):
        """Test invalid year (too old) returns None."""
        result = get_safe_publication_date(1800)
        assert result is None
    
    def test_get_safe_publication_date_invalid_year_future(self):
        """Test invalid year (future) returns None."""
        result = get_safe_publication_date(3000)
        assert result is None
    
    def test_get_safe_publication_date_invalid_month(self):
        """Test invalid month returns None."""
        result = get_safe_publication_date(2024, 13)
        assert result is None
    
    def test_get_safe_publication_date_invalid_day(self):
        """Test invalid day returns None."""
        result = get_safe_publication_date(2024, 2, 30)
        assert result is None
    
    def test_get_safe_publication_date_zero_month(self):
        """Test zero month returns None."""
        result = get_safe_publication_date(2024, 0)
        assert result is None
    
    def test_get_safe_publication_date_zero_day(self):
        """Test zero day returns None."""
        result = get_safe_publication_date(2024, 1, 0)
        assert result is None
    
    def test_get_safe_publication_date_negative_values(self):
        """Test negative values return None."""
        result = get_safe_publication_date(2024, -1, 15)
        assert result is None
