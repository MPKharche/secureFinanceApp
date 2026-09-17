"""Prepayment strategy service for loan prioritization."""
from decimal import Decimal
from typing import Literal
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.services.loan_analytics_service import LoanAnalyticsService


async def compare_strategies(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    prepayment_amount: Decimal,
) -> dict:
    """
    Compare prepayment strategies: Avalanche, Snowball, Balanced.
    
    - Avalanche: Prioritize highest interest rate
    - Snowball: Prioritize smallest balance
    - Balanced: Weighted score (interest rate + balance)
    
    Returns comparison showing interest savings and time saved for each strategy.
    """
    # Get active loans
    loans_query = select(Account).where(
        and_(
            Account.workspace_id == workspace_id,
            Account.account_type == "loan",
            Account.is_closed == False,
        )
    )
    result = await session.execute(loans_query)
    active_loans = result.scalars().all()
    
    if not active_loans:
        return {"strategies": []}
    
    analytics_service = LoanAnalyticsService(session)
    
    # Build loan data
    loan_data = []
    for loan in active_loans:
        summary = await analytics_service.get_loan_summary(loan.id)
        loan_data.append({
            "loan_id": str(loan.id),
            "loan_name": loan.name,
            "outstanding_principal": Decimal(str(summary.get("outstanding_principal", 0))),
            "interest_rate": Decimal(str(summary.get("interest_rate", 0))),
            "remaining_months": summary.get("remaining_months", 0),
        })
    
    # Calculate for each strategy
    strategies = []
    
    # Avalanche (highest interest rate first)
    avalanche_sorted = sorted(loan_data, key=lambda x: x["interest_rate"], reverse=True)
    avalanche_result = _simulate_prepayment(avalanche_sorted, prepayment_amount)
    strategies.append({
        "strategy": "avalanche",
        "name": "Avalanche (Highest Interest First)",
        "priority_loan": avalanche_sorted[0]["loan_name"] if avalanche_sorted else None,
        "total_interest_savings": float(avalanche_result["interest_savings"]),
        "months_saved": avalanche_result["months_saved"],
        "description": "Pay off loans with highest interest rates first to minimize total interest paid.",
    })
    
    # Snowball (smallest balance first)
    snowball_sorted = sorted(loan_data, key=lambda x: x["outstanding_principal"])
    snowball_result = _simulate_prepayment(snowball_sorted, prepayment_amount)
    strategies.append({
        "strategy": "snowball",
        "name": "Snowball (Smallest Balance First)",
        "priority_loan": snowball_sorted[0]["loan_name"] if snowball_sorted else None,
        "total_interest_savings": float(snowball_result["interest_savings"]),
        "months_saved": snowball_result["months_saved"],
        "description": "Pay off smallest loans first for psychological wins and momentum.",
    })
    
    # Balanced (weighted score)
    for loan in loan_data:
        # Normalize and create weighted score
        max_rate = max(l["interest_rate"] for l in loan_data)
        max_balance = max(l["outstanding_principal"] for l in loan_data)
        
        rate_score = loan["interest_rate"] / max_rate if max_rate > 0 else 0
        balance_score = (max_balance - loan["outstanding_principal"]) / max_balance if max_balance > 0 else 0
        
        loan["balanced_score"] = float(rate_score * 0.6 + balance_score * 0.4)  # 60% weight to rate, 40% to balance
    
    balanced_sorted = sorted(loan_data, key=lambda x: x["balanced_score"], reverse=True)
    balanced_result = _simulate_prepayment(balanced_sorted, prepayment_amount)
    strategies.append({
        "strategy": "balanced",
        "name": "Balanced (Hybrid Approach)",
        "priority_loan": balanced_sorted[0]["loan_name"] if balanced_sorted else None,
        "total_interest_savings": float(balanced_result["interest_savings"]),
        "months_saved": balanced_result["months_saved"],
        "description": "Balance between interest savings and quick wins.",
    })
    
    return {"strategies": strategies}


async def get_priority_ranking(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> dict:
    """
    Get priority ranking for each strategy.
    
    Returns ordered list of loans for Avalanche, Snowball, and Balanced strategies.
    """
    # Get active loans
    loans_query = select(Account).where(
        and_(
            Account.workspace_id == workspace_id,
            Account.account_type == "loan",
            Account.is_closed == False,
        )
    )
    result = await session.execute(loans_query)
    active_loans = result.scalars().all()
    
    if not active_loans:
        return {
            "avalanche": [],
            "snowball": [],
            "balanced": {},
        }
    
    analytics_service = LoanAnalyticsService(session)
    
    # Build loan data
    loan_data = []
    for loan in active_loans:
        summary = await analytics_service.get_loan_summary(loan.id)
        loan_data.append({
            "loan_id": str(loan.id),
            "loan_name": loan.name,
            "outstanding_principal": float(summary.get("outstanding_principal", 0)),
            "interest_rate": float(summary.get("interest_rate", 0)),
            "remaining_months": summary.get("remaining_months", 0),
        })
    
    # Avalanche ranking
    avalanche = sorted(loan_data, key=lambda x: x["interest_rate"], reverse=True)
    avalanche_ranked = [
        {**loan, "rank": idx + 1, "reason": f"{loan['interest_rate']:.2f}% interest rate"}
        for idx, loan in enumerate(avalanche)
    ]
    
    # Snowball ranking
    snowball = sorted(loan_data, key=lambda x: x["outstanding_principal"])
    snowball_ranked = [
        {**loan, "rank": idx + 1, "reason": f"₹{loan['outstanding_principal']:,.2f} balance"}
        for idx, loan in enumerate(snowball)
    ]
    
    # Balanced ranking
    if loan_data:
        max_rate = max(l["interest_rate"] for l in loan_data)
        max_balance = max(l["outstanding_principal"] for l in loan_data)
        
        for loan in loan_data:
            rate_score = loan["interest_rate"] / max_rate if max_rate > 0 else 0
            balance_score = (max_balance - loan["outstanding_principal"]) / max_balance if max_balance > 0 else 0
            loan["balanced_score"] = rate_score * 0.6 + balance_score * 0.4
        
        balanced = sorted(loan_data, key=lambda x: x["balanced_score"], reverse=True)
        balanced_ranked = [
            {**loan, "rank": idx + 1, "reason": f"Score: {loan['balanced_score']:.2f}"}
            for idx, loan in enumerate(balanced)
        ]
        
        # Recommendation based on portfolio
        avg_rate = sum(l["interest_rate"] for l in loan_data) / len(loan_data)
        high_rate_count = sum(1 for l in loan_data if l["interest_rate"] > avg_rate * 1.2)
        small_balance_count = sum(1 for l in loan_data if l["outstanding_principal"] < 100000)
        
        if high_rate_count >= len(loan_data) * 0.5:
            recommendation = "avalanche"
            reason = "You have multiple high-interest loans. Avalanche strategy will save the most money."
        elif small_balance_count >= len(loan_data) * 0.5:
            recommendation = "snowball"
            reason = "You have multiple small loans. Snowball strategy will give you quick wins and motivation."
        else:
            recommendation = "balanced"
            reason = "Your loan mix benefits from a balanced approach."
        
        return {
            "avalanche": avalanche_ranked,
            "snowball": snowball_ranked,
            "balanced": {
                "ranking": balanced_ranked,
                "recommendation": recommendation,
                "reason": reason,
            },
        }
    
    return {
        "avalanche": [],
        "snowball": [],
        "balanced": {},
    }


def _simulate_prepayment(sorted_loans: list[dict], prepayment_amount: Decimal) -> dict:
    """
    Simulate prepayment impact on a prioritized loan list.
    
    Simplified calculation: estimate interest savings and time reduction.
    """
    if not sorted_loans:
        return {"interest_savings": Decimal("0"), "months_saved": 0}
    
    # For simplicity, apply prepayment to top-priority loan
    top_loan = sorted_loans[0]
    principal = top_loan["outstanding_principal"]
    rate_monthly = top_loan["interest_rate"] / Decimal("12") / Decimal("100")
    remaining_months = top_loan["remaining_months"]
    
    if principal <= 0 or remaining_months <= 0:
        return {"interest_savings": Decimal("0"), "months_saved": 0}
    
    # Approximate EMI (assuming equal EMI)
    if rate_monthly > 0:
        emi = principal * rate_monthly * (1 + rate_monthly) ** remaining_months / (
            (1 + rate_monthly) ** remaining_months - 1
        )
    else:
        emi = principal / remaining_months
    
    # Without prepayment: total interest
    total_payment_without = emi * remaining_months
    interest_without = total_payment_without - principal
    
    # With prepayment: reduce principal
    new_principal = principal - prepayment_amount
    if new_principal <= 0:
        # Loan fully paid off
        return {
            "interest_savings": interest_without,
            "months_saved": remaining_months,
        }
    
    # Recalculate with reduced principal (keep same EMI, reduce tenure)
    if rate_monthly > 0:
        # Solve for new tenure: n = log((EMI / (EMI - P*r))) / log(1+r)
        try:
            import math
            
            numerator = emi / (emi - new_principal * rate_monthly)
            if numerator > 1:
                new_months = math.log(numerator) / math.log(1 + float(rate_monthly))
                new_months = int(new_months) + 1
            else:
                new_months = remaining_months
        except:
            new_months = remaining_months
    else:
        new_months = int(new_principal / emi) + 1
    
    new_months = max(1, min(new_months, remaining_months))
    
    total_payment_with = emi * new_months
    interest_with = total_payment_with - new_principal
    
    interest_savings = max(Decimal("0"), interest_without - interest_with)
    months_saved = max(0, remaining_months - new_months)
    
    return {
        "interest_savings": interest_savings,
        "months_saved": months_saved,
    }
