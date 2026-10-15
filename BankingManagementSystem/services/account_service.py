"""
Account service managing bank accounts, account creation, queries,
and authorization checks.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from database import get_db_connection
from utils import (
    generate_account_number,
    get_current_iso,
    log_audit_event,
    send_notification,
)


def get_user_accounts(
    user_id: int,
    active_only: bool = False,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Fetch all bank accounts owned by a specific customer.
    Ensures that customers can only view their own accounts.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT id, user_id, account_number, account_type, balance_paise,
                   is_active, created_at, updated_at
            FROM accounts
            WHERE user_id = ?
        """
        params: List[Any] = [user_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY id ASC;"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_account_by_id(
    account_id: int,
    user_id: Optional[int] = None,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch account by ID. If user_id is provided, strictly enforces ownership check.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("""
                SELECT a.*, u.full_name as holder_name, u.email as holder_email
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                WHERE a.id = ? AND a.user_id = ?;
            """, (account_id, user_id))
        else:
            cursor.execute("""
                SELECT a.*, u.full_name as holder_name, u.email as holder_email
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                WHERE a.id = ?;
            """, (account_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_account_by_number(
    account_number: str,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Look up account details by account number.
    Returns account information joined with holder name.
    """
    cleaned = str(account_number).strip()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.user_id, a.account_number, a.account_type,
                   a.balance_paise, a.is_active, a.created_at,
                   u.full_name as holder_name, u.username as holder_username
            FROM accounts a
            JOIN users u ON a.user_id = u.id
            WHERE a.account_number = ?;
        """, (cleaned,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_account(
    user_id: int,
    account_type: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Create an additional bank account for an authenticated customer.
    Allowed types: 'Savings', 'Current'.
    """
    valid_types = ["Savings", "Current"]
    if account_type not in valid_types:
        return False, f"Invalid account type. Allowed types: {', '.join(valid_types)}", None

    now_iso = get_current_iso()
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Verify user exists and is active
            cursor.execute("SELECT full_name, is_active FROM users WHERE id = ?;", (user_id,))
            user_row = cursor.fetchone()
            if not user_row or not user_row["is_active"]:
                return False, "User account is invalid or inactive.", None

            account_number = generate_account_number()

            cursor.execute("""
                INSERT INTO accounts (
                    user_id, account_number, account_type, balance_paise,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, 0, 1, ?, ?);
            """, (user_id, account_number, account_type, now_iso, now_iso))

            account_id = cursor.lastrowid
            log_audit_event(user_id, "ACCOUNT_CREATED", f"New {account_type} account created: {account_number}", db_path)
            send_notification(user_id, "Account Created", f"Your new {account_type} account ({account_number}) is active and ready for use.", db_path)

            new_acc = {
                "id": account_id,
                "user_id": user_id,
                "account_number": account_number,
                "account_type": account_type,
                "balance_paise": 0,
                "is_active": 1,
                "created_at": now_iso
            }
            return True, f"Successfully created new {account_type} account!", new_acc

    except Exception as e:
        return False, f"Failed to create account: {e}", None


def get_total_balance_paise(user_id: int, db_path: Optional[Path] = None) -> int:
    """Calculate total balance across all accounts belonging to a user."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(balance_paise), 0) as total
            FROM accounts
            WHERE user_id = ? AND is_active = 1;
        """, (user_id,))
        row = cursor.fetchone()
        return row["total"] if row else 0


def toggle_account_status(
    account_id: int,
    admin_user_id: int,
    is_active: bool,
    reason: str = "Admin status update",
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Administrative action to freeze (deactivate) or unfreeze (activate) an account.
    """
    now_iso = get_current_iso()
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT account_number, user_id FROM accounts WHERE id = ?;", (account_id,))
            acc = cursor.fetchone()
            if not acc:
                return False, "Account not found."

            status_val = 1 if is_active else 0
            cursor.execute("""
                UPDATE accounts SET is_active = ?, updated_at = ? WHERE id = ?;
            """, (status_val, now_iso, account_id))

            action_name = "ACCOUNT_ACTIVATED" if is_active else "ACCOUNT_DEACTIVATED"
            details = f"Account {acc['account_number']} status changed to {'active' if is_active else 'inactive'}. Reason: {reason}"
            log_audit_event(admin_user_id, action_name, details, db_path)

            status_text = "activated" if is_active else "frozen"
            send_notification(acc["user_id"], "Account Status Update", f"Your account ({acc['account_number']}) has been {status_text}.", db_path)

            return True, f"Account {acc['account_number']} has been successfully {status_text}."
    except Exception as e:
        return False, f"Error updating account status: {e}"
