"""
Unit tests for account management and isolation.
"""

from auth import register_user
from services.account_service import (
    create_account,
    get_account_by_id,
    get_account_by_number,
    get_total_balance_paise,
    get_user_accounts,
    toggle_account_status,
)


def test_account_creation_and_listing(test_db_path):
    """Test creating additional accounts and listing accounts by owner."""
    _, _, user = register_user(
        full_name="Vikram Singh",
        username="vikram",
        email="vikram@example.com",
        password="PassWord#2026",
        confirm_password="PassWord#2026",
        db_path=test_db_path
    )
    user_id = user["id"]

    # Initial registration created 1 account
    accounts = get_user_accounts(user_id, db_path=test_db_path)
    assert len(accounts) == 1
    assert accounts[0]["account_type"] == "Savings"

    # Create a Current account
    ok, msg, new_acc = create_account(user_id, "Current", db_path=test_db_path)
    assert ok
    assert new_acc["account_type"] == "Current"

    accounts_after = get_user_accounts(user_id, db_path=test_db_path)
    assert len(accounts_after) == 2


def test_account_authorization_isolation(test_db_path):
    """Ensure User A cannot query User B's account through user_id authorization."""
    _, _, user_a = register_user("User A", "usera", "a@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    _, _, user_b = register_user("User B", "userb", "b@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)

    accs_a = get_user_accounts(user_a["id"], db_path=test_db_path)
    acc_a_id = accs_a[0]["id"]

    # User A querying their own account
    acc = get_account_by_id(acc_a_id, user_id=user_a["id"], db_path=test_db_path)
    assert acc is not None

    # User B attempting to query User A's account
    unauthorized_acc = get_account_by_id(acc_a_id, user_id=user_b["id"], db_path=test_db_path)
    assert unauthorized_acc is None


def test_toggle_account_status(test_db_path):
    """Test admin freezing and unfreezing an account."""
    _, _, user = register_user("Test Holder", "holder", "h@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    accs = get_user_accounts(user["id"], db_path=test_db_path)
    acc_id = accs[0]["id"]

    # Freeze account
    freeze_ok, _ = toggle_account_status(acc_id, admin_user_id=1, is_active=False, reason="Audit freeze", db_path=test_db_path)
    assert freeze_ok
    acc = get_account_by_id(acc_id, db_path=test_db_path)
    assert acc["is_active"] == 0

    # Unfreeze account
    unfreeze_ok, _ = toggle_account_status(acc_id, admin_user_id=1, is_active=True, reason="Audit cleared", db_path=test_db_path)
    assert unfreeze_ok
    acc = get_account_by_id(acc_id, db_path=test_db_path)
    assert acc["is_active"] == 1
