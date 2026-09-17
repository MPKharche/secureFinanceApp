"""CAS PDF parser for Indian mutual funds (simplified MVP version)."""
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import pdfplumber

@dataclass
class CASTransaction:
    date: datetime
    description: str
    amount: Decimal
    units: Decimal
    nav: Decimal
    transaction_type: str

@dataclass
class CASScheme:
    scheme_name: str
    folio_number: str
    isin: Optional[str]
    amc_name: str
    scheme_code: Optional[str]
    plan_type: Optional[str]
    transactions: List[CASTransaction]

@dataclass
class CASData:
    pan: Optional[str]
    investor_name: Optional[str]
    email: Optional[str]
    schemes: List[CASScheme]
    statement_period: Optional[str]

class CASParser:
    TRANSACTION_TYPES = {'purchase': 'buy', 'sip': 'buy', 'redemption': 'sell', 'dividend': 'dividend'}
    AMC_NAMES = {'hdfc mutual fund': 'HDFC', 'sbi mutual fund': 'SBI', 'icici prudential': 'ICICI Prudential'}
    
    @staticmethod
    def parse_pdf(pdf_bytes) -> CASData:
        try:
            with pdfplumber.open(pdf_bytes) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
                if not text.strip():
                    raise ValueError("PDF contains no text")
                return CASData(
                    pan=CASParser._extract_pan(text),
                    investor_name=CASParser._extract_investor_name(text),
                    email=CASParser._extract_email(text),
                    schemes=CASParser._parse_schemes(text),
                    statement_period=CASParser._extract_period(text)
                )
        except Exception as e:
            raise ValueError(f"Failed to parse CAS PDF: {str(e)}")
    
    @staticmethod
    def _extract_pan(text: str) -> Optional[str]:
        m = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
        return m.group(0) if m else None
    
    @staticmethod
    def _extract_investor_name(text: str) -> Optional[str]:
        m = re.search(r'(?:Investor\s+)?Name\s*:\s*([A-Z\s]+)', text, re.I)
        return m.group(1).strip() if m else None
    
    @staticmethod
    def _extract_email(text: str) -> Optional[str]:
        m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return m.group(0) if m else None
    
    @staticmethod
    def _extract_period(text: str) -> Optional[str]:
        m = re.search(r'Period\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+to\s+[0-9]{2}-[A-Za-z]{3}-[0-9]{4})', text, re.I)
        return m.group(1) if m else None
    
    @staticmethod
    def _parse_schemes(text: str) -> List[CASScheme]:
        schemes = []
        for m in re.finditer(r'Folio\s+No\s*:\s*(\d+/?[\d]*)', text, re.I):
            folio = m.group(1)
            scheme_name = re.search(r'Folio\s+No[^\n]+\n([^\n]+)', text[m.start():], re.I)
            schemes.append(CASScheme(
                scheme_name=scheme_name.group(1).strip() if scheme_name else "Unknown",
                folio_number=folio,
                isin=None,
                amc_name="Unknown AMC",
                scheme_code=None,
                plan_type=None,
                transactions=[]
            ))
        return schemes
    
    @staticmethod
    def _map_transaction_type(desc: str) -> str:
        for key, val in CASParser.TRANSACTION_TYPES.items():
            if key in desc.lower():
                return val
        return 'buy'
