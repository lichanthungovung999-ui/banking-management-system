"""
Unit tests for deposit and withdrawal operations, limit enforcement, and balance tracking.
"""

from auth import register_user
from services.account_service import get_account_by_id, get_user_accounts
from services.transaction_service import (
    get_user_transactions,
    process_deposit,
    process_withdrawal,
)
from utils import rupees_to_paise


def test_deposit_success_and_balance_update(test_db_path):
    """Test successful deposit updating balance in paise and saving transaction."""
    _, _, user = register_user("Karan Kapoor", "karan", "karan@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    user_id = user["id"]
    account_id = get_user_accounts(user_id, db_path=test_db_path)[0]["id"]

    deposit_paise = rupees_to_paise(5000.50)  # ₹5,000.50 -> 500050 paise
    ok, msg, receipt = process_deposit(user_id, account_id, deposit_paise, "Initial Salary", db_path=test_db_path)

    assert ok
    assert receipt["amount_paise"] == 500050
    assert receipt["balance_after_paise"] == 500050
    assert "₹5,000.50" in receipt["amount_formatted"]

    acc = get_account_by_id(account_id, db_path=test_db_path)
    assert acc["balance_paise"] == 500050

    # Verify transaction record
    txns = get_user_transactions(user_id, db_path=test_db_path)
    assert len(txns) == 1
    assert txns[0]["transaction_type"] == "DEPOSIT"


def test_invalid_deposit_amounts(test_db_path):
    """Test rejecting negative or zero deposits."""
    _, _, user = register_user("User Dep", "userdep", "dep@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    acc_id = get_user_accounts(user["id"], db_path=test_db_path)[0]["id"]

    # Negative amount
    ok_neg, msg_neg, _ = process_deposit(user["id"], acc_id, -100, db_path=test_db_path)
    assert not ok_neg
    assert "positive" in msg_neg

    # Zero amount
    ok_zero, msg_zero, _ = process_deposit(user["id"], acc_id, 0, db_path=test_db_path)
    assert not ok_zero


def test_withdrawal_success_and_insufficient_funds_rejection(test_db_path):
    """Test withdrawal and rejection when attempting to overdraft."""
    _, _, user = register_user("Meera Nair", "meera", "meera@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    user_id = user["id"]
    acc_id = get_user_accounts(user_id, db_path=test_db_path)[0]["id"]

    # 1. Deposit ₹10,000
    process_deposit(user_id, acc_id, rupees_to_paise(10000), "Deposit", db_path=test_db_path)

    # 2. Withdraw ₹3,000 -> balance becomes ₹7,000
    w_ok, _, receipt = process_withdrawal(user_id, acc_id, rupees_to_paise(3000), "ATM Cash", db_path=test_db_path)
    assert w_ok
    assert receipt["balance_after_paise"] == rupees_to_paise(7000)

    # 3. Attempt to withdraw ₹8,000 (exceeds available ₹7,000) -> MUST BE REJECTED
    fail_ok, fail_msg, _ = process_withdrawal(user_id, acc_id, rupees_to_paise(8000), "Excessive", db_path=test_db_path)
    assert not fail_ok
    assert "Insufficient funds" in fail_msg

    # Verify balance was NOT touched
    acc = get_account_by_id(acc_id, db_path=test_db_path)
    assert acc["balance_paise"] == rupees_to_paise(7000)
