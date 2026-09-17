"""Test tax table migrations."""
import pytest
from sqlalchemy import inspect

from app.core.database import engine


def test_tax_tables_exist():
    """Verify all tax tables are created."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert 'tax_income_sources' in tables
    assert 'tax_deductions' in tables
    assert 'tax_projections' in tables
    assert 'tax_events_log' in tables


def test_user_dob_column_exists():
    """Verify date_of_birth column added to users table."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('users')}
    assert 'date_of_birth' in columns


def test_tax_income_sources_columns():
    """Verify tax_income_sources has required columns."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tax_income_sources')}
    
    required_columns = {
        'id', 'user_id', 'workspace_id', 'financial_year',
        'salary_annual', 'rental_income', 'interest_income',
        'basic_salary', 'hra_received', 'salary_auto_detected',
        'created_at', 'updated_at'
    }
    assert required_columns.issubset(columns)


def test_tax_deductions_columns():
    """Verify tax_deductions has required columns."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tax_deductions')}
    
    required_columns = {
        'id', 'user_id', 'workspace_id', 'financial_year',
        'epf_employee', 'ppf', 'elss', 'health_insurance_self',
        'rent_paid_annual', 'city', 'created_at', 'updated_at'
    }
    assert required_columns.issubset(columns)


def test_tax_projections_columns():
    """Verify tax_projections has required columns."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tax_projections')}
    
    required_columns = {
        'id', 'user_id', 'workspace_id', 'financial_year',
        'old_regime_gross_income', 'old_regime_total_tax',
        'new_regime_gross_income', 'new_regime_total_tax',
        'recommended_regime', 'savings_with_recommendation',
        'is_stale', 'calculated_at', 'created_at', 'updated_at'
    }
    assert required_columns.issubset(columns)


def test_tax_events_log_columns():
    """Verify tax_events_log has required columns."""
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('tax_events_log')}
    
    required_columns = {
        'id', 'user_id', 'financial_year', 'event_type',
        'event_data', 'triggered_recalculation', 'created_at'
    }
    assert required_columns.issubset(columns)


def test_tax_indexes():
    """Verify indexes are created."""
    inspector = inspect(engine)
    
    # Check tax_income_sources index
    income_indexes = {idx['name'] for idx in inspector.get_indexes('tax_income_sources')}
    assert 'idx_tax_income_user_fy' in income_indexes
    
    # Check tax_deductions index
    deductions_indexes = {idx['name'] for idx in inspector.get_indexes('tax_deductions')}
    assert 'idx_tax_deductions_user_fy' in deductions_indexes
    
    # Check tax_projections indexes
    projections_indexes = {idx['name'] for idx in inspector.get_indexes('tax_projections')}
    assert 'idx_tax_projections_user_fy' in projections_indexes
    assert 'idx_tax_projections_stale' in projections_indexes
