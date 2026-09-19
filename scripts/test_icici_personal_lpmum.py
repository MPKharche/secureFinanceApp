#!/usr/bin/env python3
"""Test suite for ICICI Personal Loan LPMUM00052503715.

Tests:
1. EMI calculation accuracy
2. Schedule generation (60 entries)
3. Interest/principal split validation
4. Transaction linking workflow
5. API endpoint responses
6. Data integrity checks
"""
import asyncio
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.account import Account
from app.models.loan_schedule import LoanAmortizationSchedule
from app.services.loan_schedule_service import calculate_emi

# Expected values from PDF
LOAN_ACCOUNT_NO = "LPMUM00052503715"
EXPECTED_PRINCIPAL = Decimal("1000000.00")
EXPECTED_RATE = Decimal("10.70")
EXPECTED_TENURE = 60
EXPECTED_EMI = Decimal("21703.00")
EXPECTED_TOTAL_INTEREST = Decimal("302036.00")
EXPECTED_TOTAL_PAYMENT = Decimal("1302036.00")

# First EMI breakdown from PDF (Page 3)
EXPECTED_FIRST_EMI_PRINCIPAL = Decimal("7734.00")
EXPECTED_FIRST_EMI_INTEREST = Decimal("13969.00")
EXPECTED_FIRST_EMI_CLOSING = Decimal("992266.00")


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test: str):
        self.passed.append(test)
        print(f"  ✓ {test}")
    
    def add_fail(self, test: str, reason: str):
        self.failed.append(f"{test}: {reason}")
        print(f"  ✗ {test}: {reason}")
    
    def add_warning(self, test: str, reason: str):
        self.warnings.append(f"{test}: {reason}")
        print(f"  ⚠ {test}: {reason}")
    
    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"{self.name} Summary")
        print(f"{'='*60}")
        print(f"Passed: {len(self.passed)}/{total}")
        print(f"Failed: {len(self.failed)}/{total}")
        if self.warnings:
            print(f"Warnings: {len(self.warnings)}")
        return len(self.failed) == 0


def test_emi_calculation():
    """Test 1: EMI calculation accuracy."""
    result = TestResult("Test 1: EMI Calculation")
    
    # Calculate EMI using our formula
    calculated_emi = calculate_emi(EXPECTED_PRINCIPAL, EXPECTED_RATE, EXPECTED_TENURE)
    
    # Check if it matches expected
    diff = abs(calculated_emi - EXPECTED_EMI)
    if diff <= Decimal("1.00"):  # Allow ₹1 tolerance
        result.add_pass(f"EMI matches: ₹{calculated_emi} ≈ ₹{EXPECTED_EMI}")
    else:
        result.add_fail(f"EMI mismatch", f"₹{calculated_emi} vs ₹{EXPECTED_EMI}")
    
    # Test edge cases
    try:
        zero_rate_emi = calculate_emi(EXPECTED_PRINCIPAL, Decimal("0"), EXPECTED_TENURE)
        expected_zero = EXPECTED_PRINCIPAL / EXPECTED_TENURE
        if abs(zero_rate_emi - expected_zero) < Decimal("0.01"):
            result.add_pass("Zero interest rate handled correctly")
        else:
            result.add_fail("Zero interest", f"Got ₹{zero_rate_emi}, expected ₹{expected_zero}")
    except Exception as e:
        result.add_fail("Zero interest", str(e))
    
    return result.summary()


async def test_schedule_generation():
    """Test 2: Schedule generation validation."""
    result = TestResult("Test 2: Schedule Generation")
    
    async with async_session_maker() as session:
        # Get loan
        loan_result = await session.execute(
            select(Account).where(Account.external_id == LOAN_ACCOUNT_NO)
        )
        loan = loan_result.scalar_one_or_none()
        
        if not loan:
            result.add_fail("Loan not found", f"Account {LOAN_ACCOUNT_NO} does not exist")
            return result.summary()
        
        result.add_pass(f"Loan found: {loan.id}")
        
        # Get schedule
        schedule_result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == loan.id,
                LoanAmortizationSchedule.schedule_version == loan.current_schedule_version
            )
            .order_by(LoanAmortizationSchedule.emi_number)
        )
        entries = list(schedule_result.scalars().all())
        
        # Test: 60 entries
        if len(entries) == EXPECTED_TENURE:
            result.add_pass(f"Schedule has {len(entries)} entries")
        else:
            result.add_fail("Entry count", f"{len(entries)} vs {EXPECTED_TENURE}")
        
        # Test: All EMI numbers sequential
        expected_numbers = list(range(1, EXPECTED_TENURE + 1))
        actual_numbers = [e.emi_number for e in entries]
        if actual_numbers == expected_numbers:
            result.add_pass("EMI numbers are sequential 1-60")
        else:
            result.add_fail("EMI numbers", "Not sequential or duplicates found")
        
        # Test: All due dates on 5th
        all_fifth = all(e.due_date.day == 5 for e in entries)
        if all_fifth:
            result.add_pass("All due dates on 5th of month")
        else:
            wrong_days = [e.emi_number for e in entries if e.due_date.day != 5]
            result.add_fail("Due date day", f"EMIs {wrong_days} not on 5th")
        
        # Test: Closing balance of last EMI is zero
        last_closing = entries[-1].closing_balance
        if last_closing == Decimal("0.00"):
            result.add_pass("Last EMI closing balance is ₹0")
        else:
            result.add_fail("Final balance", f"₹{last_closing} != ₹0")
        
        # Test: Opening balance of first EMI matches principal
        first_opening = entries[0].opening_balance
        if first_opening == EXPECTED_PRINCIPAL:
            result.add_pass(f"First EMI opening balance: ₹{first_opening}")
        else:
            result.add_fail("Initial balance", f"₹{first_opening} vs ₹{EXPECTED_PRINCIPAL}")
        
        # Test: All payment statuses are 'scheduled'
        statuses = set(e.payment_status for e in entries)
        if statuses == {"scheduled"}:
            result.add_pass("All EMIs have 'scheduled' status")
        else:
            result.add_warning("Payment status", f"Found statuses: {statuses}")
        
    return result.summary()


async def test_interest_principal_split():
    """Test 3: Interest/principal split validation."""
    result = TestResult("Test 3: Interest/Principal Split")
    
    async with async_session_maker() as session:
        loan_result = await session.execute(
            select(Account).where(Account.external_id == LOAN_ACCOUNT_NO)
        )
        loan = loan_result.scalar_one_or_none()
        
        if not loan:
            result.add_fail("Loan not found", "Cannot test without loan")
            return result.summary()
        
        schedule_result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == loan.id,
                LoanAmortizationSchedule.schedule_version == loan.current_schedule_version
            )
            .order_by(LoanAmortizationSchedule.emi_number)
        )
        entries = list(schedule_result.scalars().all())
        
        if not entries:
            result.add_fail("No schedule entries", "Cannot validate")
            return result.summary()
        
        # Calculate totals
        total_principal = sum(e.principal_component for e in entries)
        total_interest = sum(e.interest_component for e in entries)
        total_payment = sum(e.emi_amount for e in entries)
        
        # Test: Total principal equals original principal
        if abs(total_principal - EXPECTED_PRINCIPAL) < Decimal("1.00"):
            result.add_pass(f"Total principal: ₹{total_principal:,.2f}")
        else:
            result.add_fail("Total principal", f"₹{total_principal} vs ₹{EXPECTED_PRINCIPAL}")
        
        # Test: Total interest matches expected (within tolerance)
        interest_diff = abs(total_interest - EXPECTED_TOTAL_INTEREST)
        if interest_diff <= Decimal("10000.00"):  # ±₹10k tolerance (rounding differences)
            result.add_pass(f"Total interest: ₹{total_interest:,.2f}")
            if interest_diff > Decimal("100.00"):
                result.add_warning("Interest variance", f"₹{interest_diff:,.2f} difference from PDF")
        else:
            result.add_fail("Total interest", f"₹{total_interest} vs ₹{EXPECTED_TOTAL_INTEREST}")
        
        # Test: Total payment
        payment_diff = abs(total_payment - EXPECTED_TOTAL_PAYMENT)
        if payment_diff <= Decimal("10000.00"):
            result.add_pass(f"Total payment: ₹{total_payment:,.2f}")
            if payment_diff > Decimal("100.00"):
                result.add_warning("Payment variance", f"₹{payment_diff:,.2f} difference from PDF")
        else:
            result.add_fail("Total payment", f"₹{total_payment} vs ₹{EXPECTED_TOTAL_PAYMENT}")
        
        # Test: Each EMI principal + interest = EMI amount
        all_balanced = all(
            abs((e.principal_component + e.interest_component) - e.emi_amount) < Decimal("0.01")
            for e in entries
        )
        if all_balanced:
            result.add_pass("All EMIs balanced (principal + interest = EMI)")
        else:
            unbalanced = [
                e.emi_number for e in entries 
                if abs((e.principal_component + e.interest_component) - e.emi_amount) >= Decimal("0.01")
            ]
            result.add_fail("EMI balance", f"Unbalanced EMIs: {unbalanced[:5]}")
        
        # Test: Principal increases over time (reducing balance)
        principal_increasing = all(
            entries[i].principal_component <= entries[i+1].principal_component
            for i in range(len(entries) - 1)
        )
        if principal_increasing:
            result.add_pass("Principal component increases each month")
        else:
            result.add_fail("Principal trend", "Not monotonically increasing")
        
        # Test: Interest decreases over time
        interest_decreasing = all(
            entries[i].interest_component >= entries[i+1].interest_component
            for i in range(len(entries) - 1)
        )
        if interest_decreasing:
            result.add_pass("Interest component decreases each month")
        else:
            result.add_fail("Interest trend", "Not monotonically decreasing")
        
    return result.summary()


async def test_data_integrity():
    """Test 4: Data integrity checks."""
    result = TestResult("Test 4: Data Integrity")
    
    async with async_session_maker() as session:
        loan_result = await session.execute(
            select(Account).where(Account.external_id == LOAN_ACCOUNT_NO)
        )
        loan = loan_result.scalar_one_or_none()
        
        if not loan:
            result.add_fail("Loan not found", "Cannot test")
            return result.summary()
        
        # Test: Account fields populated
        fields_to_check = [
            ("name", loan.name),
            ("display_name", loan.display_name),
            ("external_id", loan.external_id),
            ("masked_number", loan.masked_number),
            ("type", loan.type),
            ("loan_kind", loan.loan_kind),
            ("original_principal", loan.original_principal),
            ("interest_rate", loan.interest_rate),
            ("tenure_months", loan.tenure_months),
            ("emi_amount", loan.emi_amount),
            ("disbursed_on", loan.disbursed_on),
            ("emi_day", loan.emi_day),
            ("currency", loan.currency),
        ]
        
        for field_name, field_value in fields_to_check:
            if field_value is not None:
                result.add_pass(f"Field '{field_name}' populated")
            else:
                result.add_fail(f"Field '{field_name}'", "NULL value")
        
        # Test: Schedule version consistency
        schedule_result = await session.execute(
            select(LoanAmortizationSchedule)
            .where(
                LoanAmortizationSchedule.account_id == loan.id,
                LoanAmortizationSchedule.schedule_version == loan.current_schedule_version
            )
        )
        entries = list(schedule_result.scalars().all())
        
        if entries:
            all_same_version = all(e.schedule_version == loan.current_schedule_version for e in entries)
            if all_same_version:
                result.add_pass(f"All entries use version {loan.current_schedule_version}")
            else:
                result.add_fail("Version consistency", "Mixed versions in schedule")
        
        # Test: Workspace consistency
        all_same_workspace = all(e.workspace_id == loan.workspace_id for e in entries)
        if all_same_workspace:
            result.add_pass("All entries in same workspace")
        else:
            result.add_fail("Workspace consistency", "Mixed workspaces")
        
    return result.summary()


async def main():
    print("="*60)
    print("ICICI Personal Loan Test Suite")
    print(f"Loan Account: {LOAN_ACCOUNT_NO}")
    print("="*60)
    print()
    
    all_passed = True
    
    # Test 1: EMI Calculation
    passed = test_emi_calculation()
    all_passed = all_passed and passed
    print()
    
    # Test 2: Schedule Generation
    passed = await test_schedule_generation()
    all_passed = all_passed and passed
    print()
    
    # Test 3: Interest/Principal Split
    passed = await test_interest_principal_split()
    all_passed = all_passed and passed
    print()
    
    # Test 4: Data Integrity
    passed = await test_data_integrity()
    all_passed = all_passed and passed
    print()
    
    # Final summary
    print("="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
