"""SMS parser service using LLM for Indian bank SMS parsing."""

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.agents.providers.registry import build_provider
from app.agents.config import get_agent_settings


SMS_PARSER_PROMPT = """You are an expert at parsing Indian bank SMS messages into structured transaction data.

Parse the following SMS message and extract transaction details. Indian banks send SMS for various transaction types including:
- Debit card purchases
- Credit card purchases
- UPI payments
- ATM withdrawals
- NEFT/RTGS/IMPS transfers
- Account debits/credits

Extract these fields:
- transaction_type: "debit" or "credit"
- amount: numeric value only (e.g., 1250.50)
- currency: typically "INR" for Indian banks
- merchant: merchant/payee name (normalize: remove extra spaces, common abbreviations)
- date: transaction date in ISO format (YYYY-MM-DD), if time is included use current date
- account_last_digits: last 4 digits of account/card number if present
- description: clean, concise description of the transaction
- category_hint: suggest a category (e.g., "Groceries", "Fuel", "Dining", "Shopping", "Transfer", "ATM", "Bills", "Entertainment")

Common Indian bank SMS patterns:
- HDFC: "INR X.XX debited from A/c XX1234 on DD-MMM-YY at MERCHANT"
- ICICI: "Your A/c XX1234 is debited with INR X.XX on DD-MMM-YYYY for MERCHANT"
- SBI: "Dear Customer, INR X.XX has been debited from your A/c XX1234 on DD/MM/YY to MERCHANT"
- Axis: "Your A/c XX1234 debited by Rs.X.XX on DD-MMM-YY. Info: MERCHANT"
- UPI: "Rs X.XX sent to MERCHANT via UPI"

Return ONLY a JSON object with these fields. Set "confidence" (0.0-1.0) based on how clear the parsing is.

Example output:
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

If the SMS is NOT a transaction alert (e.g., OTP, balance inquiry, promotional), return:
{
  "confidence": 0.0,
  "error": "Not a transaction SMS"
}

SMS to parse:
{sms_body}

Return only the JSON object, no other text."""


class SMSParseResult:
    """Result of SMS parsing."""

    def __init__(
        self,
        success: bool,
        confidence: float,
        transaction_type: Optional[str] = None,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
        merchant: Optional[str] = None,
        date: Optional[str] = None,
        account_last_digits: Optional[str] = None,
        description: Optional[str] = None,
        category_hint: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.confidence = confidence
        self.transaction_type = transaction_type
        self.amount = amount
        self.currency = currency
        self.merchant = merchant
        self.date = date
        self.account_last_digits = account_last_digits
        self.description = description
        self.category_hint = category_hint
        self.error = error

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "success": self.success,
            "confidence": self.confidence,
            "transaction_type": self.transaction_type,
            "amount": str(self.amount) if self.amount else None,
            "currency": self.currency,
            "merchant": self.merchant,
            "date": self.date,
            "account_last_digits": self.account_last_digits,
            "description": self.description,
            "category_hint": self.category_hint,
            "error": self.error,
        }


async def parse_sms_with_llm(sender: str, body: str, user_id: str) -> SMSParseResult:
    """
    Parse SMS message using LLM.

    Args:
        sender: SMS sender (e.g., "HDFCBK", "ICICIB")
        body: SMS message body
        user_id: User ID for provider lookup

    Returns:
        SMSParseResult with parsed data and confidence score
    """
    config = get_agent_settings()
    
    if not config.enabled:
        return SMSParseResult(
            success=False,
            confidence=0.0,
            error="AI Agents feature is not enabled"
        )

    try:
        # Get AI provider - build a default provider for SMS parsing
        config = get_agent_settings()
        provider = build_provider(
            name=config.default_provider if hasattr(config, 'default_provider') else "ollama",
            api_key="",
            model=config.default_model if hasattr(config, 'default_model') else None,
        )
        
        # Format prompt
        prompt = SMS_PARSER_PROMPT.format(sms_body=body)
        
        # Call LLM
        response = await provider.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temperature for consistent parsing
            max_tokens=500,
        )
        
        # Extract JSON from response
        content = response.get("content", "")
        parsed_data = _extract_json(content)
        
        if not parsed_data:
            return SMSParseResult(
                success=False,
                confidence=0.0,
                error="Failed to extract JSON from LLM response"
            )
        
        # Validate and build result
        confidence = float(parsed_data.get("confidence", 0.0))
        
        if confidence < 0.5:
            return SMSParseResult(
                success=False,
                confidence=confidence,
                error=parsed_data.get("error", "Low confidence parse")
            )
        
        # Parse amount
        amount = None
        if parsed_data.get("amount"):
            try:
                amount = Decimal(str(parsed_data["amount"]))
            except Exception:
                pass
        
        return SMSParseResult(
            success=True,
            confidence=confidence,
            transaction_type=parsed_data.get("transaction_type"),
            amount=amount,
            currency=parsed_data.get("currency", "INR"),
            merchant=parsed_data.get("merchant"),
            date=parsed_data.get("date"),
            account_last_digits=parsed_data.get("account_last_digits"),
            description=parsed_data.get("description"),
            category_hint=parsed_data.get("category_hint"),
        )
        
    except Exception as e:
        return SMSParseResult(
            success=False,
            confidence=0.0,
            error=f"LLM parsing failed: {str(e)}"
        )


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON object from LLM response text."""
    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Try parsing entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None
