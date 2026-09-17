"""Event listeners for automatic tax projection refresh."""
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.tax import TaxIncomeSource, TaxDeduction, TaxProjection
from app.models.transaction import Transaction


def mark_projections_stale_sync(session: Session, user_id, financial_year: str):
    """
    Synchronous helper to mark projections stale.
    
    Used by SQLAlchemy event listeners which run in sync context.
    """
    # Find matching projections
    projections = session.query(TaxProjection).filter(
        TaxProjection.user_id == user_id,
        TaxProjection.financial_year == financial_year,
        TaxProjection.is_stale == False
    ).all()
    
    for projection in projections:
        projection.is_stale = True


# Income Source Change Listener

@event.listens_for(TaxIncomeSource, 'after_update')
def after_income_source_update(mapper, connection, target):
    """Mark projections stale when income sources change."""
    session = Session.object_session(target)
    if session:
        mark_projections_stale_sync(session, target.user_id, target.financial_year)


@event.listens_for(TaxIncomeSource, 'after_insert')
def after_income_source_insert(mapper, connection, target):
    """Mark projections stale when income sources created."""
    session = Session.object_session(target)
    if session:
        mark_projections_stale_sync(session, target.user_id, target.financial_year)


# Deduction Change Listener

@event.listens_for(TaxDeduction, 'after_update')
def after_deduction_update(mapper, connection, target):
    """Mark projections stale when deductions change."""
    session = Session.object_session(target)
    if session:
        mark_projections_stale_sync(session, target.user_id, target.financial_year)


@event.listens_for(TaxDeduction, 'after_insert')
def after_deduction_insert(mapper, connection, target):
    """Mark projections stale when deductions created."""
    session = Session.object_session(target)
    if session:
        mark_projections_stale_sync(session, target.user_id, target.financial_year)


# Transaction Change Listener (for salary/interest auto-detection)

@event.listens_for(Transaction, 'after_insert')
def after_transaction_insert(mapper, connection, target):
    """
    Detect salary/interest transactions and mark projections stale.
    
    This enables automatic income detection from transaction data.
    """
    # Skip if transaction doesn't have category or amount
    if not target.category_id or not target.amount:
        return
    
    # Check if it's a salary or interest transaction
    # This is a simplified detection - real implementation would check category names
    session = Session.object_session(target)
    if not session:
        return
    
    # Get current financial year from transaction date
    # Simplified: assumes FY starts April 1
    from datetime import date
    tx_date = target.date or date.today()
    
    if tx_date.month >= 4:
        fy_start = tx_date.year
    else:
        fy_start = tx_date.year - 1
    
    financial_year = f"{fy_start}-{str(fy_start + 1)[-2:]}"
    
    # Mark projections stale for this user and FY
    mark_projections_stale_sync(session, target.user_id, financial_year)


def setup_tax_listeners():
    """
    Setup all tax-related event listeners.
    
    Call this during application startup to register listeners.
    """
    # Listeners are registered via decorators, so this is a no-op
    # but provides a clear entry point for initialization
    pass
