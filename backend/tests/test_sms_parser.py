"""Tests for SMS parser service."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.sms_parser import (
    parse_sms_with_llm,
    SMSParseResult,
    _extract_json,
)


class TestExtractJson:
    """Test JSON extraction from LLM responses."""

    def test_extract_json_from_clean_response(self):
        """Test extracting JSON from clean response."""
        text = '{"amount": 100.50, "merchant": "Amazon"}'
        result = _extract_json(text)
        assert result == {"amount": 100.50, "merchant": "Amazon"}

    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON with surrounding text."""
        text = 'Here is the parsed data: {"amount": 100.50, "merchant": "Amazon"} - done'
        result = _extract_json(text)
        assert result == {"amount": 100.50, "merchant": "Amazon"}

    def test_extract_json_from_invalid_text(self):
        """Test extracting JSON from invalid text."""
        text = "This is not JSON at all"
        result = _extract_json(text)
        assert result is None


@pytest.mark.asyncio
class TestParseSmsWithLlm:
    """Test SMS parsing with LLM."""

    async def test_parse_hdfc_debit_sms(self):
        """Test parsing HDFC bank debit SMS."""
        with patch("app.services.sms_parser.get_provider") as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = {
                "content": """
                {
                    "transaction_type": "debit",
                    "amount": 1250.50,
                    "currency": "INR",
                    "merchant": "Amazon",
                    "date": "2026-09-17",
                    "account_last_digits": "1234",
                    "description": "Purchase at Amazon",
                    "category_hint": "Shopping",
                    "confidence": 0.95
                }
                """
            }
            mock_provider.return_value = mock_llm

            result = await parse_sms_with_llm(
                sender="HDFCBK",
                body="INR 1,250.50 debited from A/c XX1234 on 17-Sep-26 at Amazon",
                user_id="test-user-id"
            )

            assert result.success is True
            assert result.confidence == 0.95
            assert result.transaction_type == "debit"
            assert result.amount == Decimal("1250.50")
            assert result.currency == "INR"
            assert result.merchant == "Amazon"
            assert result.date == "2026-09-17"
            assert result.account_last_digits == "1234"

    async def test_parse_low_confidence_sms(self):
        """Test parsing SMS with low confidence."""
        with patch("app.services.sms_parser.get_provider") as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = {
                "content": """
                {
                    "confidence": 0.3,
                    "error": "Ambiguous transaction details"
                }
                """
            }
            mock_provider.return_value = mock_llm

            result = await parse_sms_with_llm(
                sender="HDFCBK",
                body="Some unclear message",
                user_id="test-user-id"
            )

            assert result.success is False
            assert result.confidence == 0.3
            assert "Ambiguous" in result.error

    async def test_parse_non_transaction_sms(self):
        """Test parsing non-transaction SMS (OTP, promo)."""
        with patch("app.services.sms_parser.get_provider") as mock_provider:
            mock_llm = AsyncMock()
            mock_llm.generate.return_value = {
                "content": """
                {
                    "confidence": 0.0,
                    "error": "Not a transaction SMS"
                }
                """
            }
            mock_provider.return_value = mock_llm

            result = await parse_sms_with_llm(
                sender="HDFCBK",
                body="Your OTP is 123456",
                user_id="test-user-id"
            )

            assert result.success is False
            assert result.confidence == 0.0
            assert "Not a transaction SMS" in result.error

    async def test_parse_agents_disabled(self):
        """Test parsing when AI Agents is disabled."""
        with patch("app.services.sms_parser.get_agents_config") as mock_config:
            mock_config.return_value.enabled = False

            result = await parse_sms_with_llm(
                sender="HDFCBK",
                body="INR 100 debited",
                user_id="test-user-id"
            )

            assert result.success is False
            assert result.confidence == 0.0
            assert "not enabled" in result.error


class TestSMSParseResult:
    """Test SMSParseResult class."""

    def test_to_dict_success(self):
        """Test converting successful parse result to dict."""
        result = SMSParseResult(
            success=True,
            confidence=0.95,
            transaction_type="debit",
            amount=Decimal("100.50"),
            currency="INR",
            merchant="Amazon",
            date="2026-09-17",
            account_last_digits="1234",
            description="Purchase",
            category_hint="Shopping",
        )

        data = result.to_dict()
        assert data["success"] is True
        assert data["confidence"] == 0.95
        assert data["amount"] == "100.50"
        assert data["merchant"] == "Amazon"

    def test_to_dict_failure(self):
        """Test converting failed parse result to dict."""
        result = SMSParseResult(
            success=False,
            confidence=0.2,
            error="Parse failed",
        )

        data = result.to_dict()
        assert data["success"] is False
        assert data["confidence"] == 0.2
        assert data["error"] == "Parse failed"
