"""Mutual Fund service layer."""
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_transaction import AssetTransaction
from app.models.mutual_fund_sip import MutualFundSIP
from app.services.cas_parser import CASParser
from app.services.xirr_calculator import XIRRCalculator

class MutualFundService:
    def __init__(self, db: Session, workspace_id: UUID):
        self.db = db
        self.workspace_id = workspace_id
    
    async def import_cas(self, pdf_bytes: bytes) -> Dict:
        cas_data = CASParser.parse_pdf(io.BytesIO(pdf_bytes))
        imported_schemes = 0
        for scheme in cas_data.schemes:
            try:
                asset = self._find_or_create_asset(scheme)
                imported_schemes += 1
            except Exception:
                continue
        self.db.commit()
        return {'imported_schemes': imported_schemes, 'investor_name': cas_data.investor_name, 'pan': cas_data.pan}
    
    def _find_or_create_asset(self, scheme) -> Asset:
        stmt = select(Asset).where(Asset.workspace_id == self.workspace_id, Asset.folio_number == scheme.folio_number)
        asset = self.db.execute(stmt).scalar_one_or_none()
        if asset:
            return asset
        asset = Asset(workspace_id=self.workspace_id, symbol=scheme.folio_number, name=scheme.scheme_name,
                     type='mutual_fund', folio_number=scheme.folio_number, amc_name=scheme.amc_name,
                     plan_type=scheme.plan_type, units=Decimal('0'), average_price=Decimal('0'),
                     purchase_price=Decimal('0'), current_price=Decimal('0'), currency='INR',
                     created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        self.db.add(asset)
        self.db.flush()
        return asset
    
    async def get_portfolio_summary(self) -> Dict:
        stmt = select(Asset).where(Asset.workspace_id == self.workspace_id, Asset.type == 'mutual_fund', Asset.units > 0)
        assets = self.db.execute(stmt).scalars().all()
        holdings = []
        total_invested = Decimal('0')
        total_current = Decimal('0')
        for asset in assets:
            current_value = asset.units * (asset.current_price or Decimal('0'))
            unrealized_gain = current_value - asset.purchase_price
            holdings.append({
                'asset_id': str(asset.id), 'scheme_name': asset.name, 'folio_number': asset.folio_number,
                'amc_name': asset.amc_name, 'units': float(asset.units), 'invested': float(asset.purchase_price),
                'current_value': float(current_value), 'unrealized_gain': float(unrealized_gain)
            })
            total_invested += asset.purchase_price
            total_current += current_value
        return {'holdings': holdings, 'summary': {'total_invested': float(total_invested),
                'current_value': float(total_current), 'total_gain': float(total_current - total_invested)}}
    
    async def get_sips(self) -> List[Dict]:
        stmt = select(MutualFundSIP).where(MutualFundSIP.workspace_id == self.workspace_id)
        sips = self.db.execute(stmt).scalars().all()
        return [{'id': str(sip.id), 'asset_id': str(sip.asset_id), 'amount': float(sip.amount),
                'frequency': sip.frequency, 'status': sip.status,
                'next_due_date': sip.next_due_date.isoformat() if sip.next_due_date else None} for sip in sips]
