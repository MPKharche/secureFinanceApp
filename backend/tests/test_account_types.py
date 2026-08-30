from app.core.account_types import is_liability_account_type


def test_loan_and_card_are_liabilities():
    assert is_liability_account_type("loan")
    assert is_liability_account_type("credit_card")
    assert not is_liability_account_type("checking")
    assert not is_liability_account_type("investment")
