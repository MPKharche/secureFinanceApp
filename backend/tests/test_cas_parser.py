"""Tests for CAS parser."""
import pytest
from decimal import Decimal
from datetime import datetime
from io import BytesIO

from app.services.cas_parser import CASParser, CASData


def test_transaction_type_mapping():
    """Test transaction type mapping."""
    assert CASParser._map_transaction_type("Purchase") == "buy"
    assert CASParser._map_transaction_type("Additional Purchase") == "buy"
    assert CASParser._map_transaction_type("Redemption") == "sell"
    assert CASParser._map_transaction_type("Switch Out") == "sell"
    assert CASParser._map_transaction_type("Switch In") == "buy"
    assert CASParser._map_transaction_type("Dividend Reinvest") == "buy"


def test_amc_extraction():
    """Test AMC name extraction from scheme name."""
    assert CASParser._extract_amc_from_scheme_name("ICICI Prudential Bluechip Fund") == "ICICI Prudential"
    assert CASParser._extract_amc_from_scheme_name("HDFC Equity Fund") == "HDFC"
    assert CASParser._extract_amc_from_scheme_name("SBI Bluechip Fund") == "SBI"


def test_invalid_pdf():
    """Test handling of invalid PDF."""
    with pytest.raises(ValueError, match="Failed to parse"):
        CASParser.parse_pdf(b"Not a PDF")


# Add more tests with sample CAS data when available
