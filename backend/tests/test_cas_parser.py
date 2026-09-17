"""Tests for CAS parser."""
from app.services.cas_parser import CASParser

def test_transaction_type_mapping():
    assert CASParser._map_transaction_type("Purchase - CAMS") == "buy"
    assert CASParser._map_transaction_type("Redemption") == "sell"
    assert CASParser._map_transaction_type("Dividend Payout") == "dividend"
