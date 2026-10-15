"""
Transaction service handling deposits, withdrawals, transfers,
atomic balance updates, and analytical summaries.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from database import get_db_connection
from utils import (
    format_currency,
    generate_transaction_ref,
    generate_transfer_ref,
    get_current_iso,
    log_audit_event,
    mask_account_number,
    send_notification,
)

# Maximum transaction limit: ₹10,00,000 (100,000,000 paise)
MAX_TRANSACTION_LIMIT_PAISE = 100_000_000


# ============================================================================
# DEPOSIT OPERATION
# ============================================================================

def process_deposit(
    user_id: int,
    account_id: int,
    amount_paise: int,
    description: str = "",
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Process a deposit into a user-owned account atomically.
    """
    if amount_paise <= 0:
        return False, "Deposit amount must be positive.", None

    if amount_paise > MAX_TRANSACTION_LIMIT_PAISE:
        return False, f"Deposit exceeds maximum per-transaction limit of {format_currency(MAX_TRANSACTION_LIMIT_PAISE)}.", None

    desc_cleaned = description.strip() or "Standard Deposit"
    now_iso = get_current_iso()
    txn_ref = generate_transaction_ref(prefix="DEP")

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # 1. Verify account ownership and active status
            cursor.execute("""
                SELECT id, account_number, account_type, balance_paise, is_active
                FROM accounts
                WHERE id = ? AND user_id = ?;
            """, (account_id, user_id))
            acc = cursor.fetchone()

            if not acc:
                return False, "Account not found or access denied.", None

            if not acc["is_active"]:
                return False, "Account is frozen/inactive. Deposits are currently disabled.", None

            # 2. Atomic Balance Update
            new_balance_paise = acc["balance_paise"] + amount_paise
            cursor.execute("""
                UPDATE accounts
                SET balance_paise = ?, updated_at = ?
                WHERE id = ?;
            """, (new_balance_paise, now_iso, account_id))

            # 3. Create Transaction Record
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, account_id, user_id, transaction_type,
                    amount_paise, balance_after_paise, description, status, created_at
                ) VALUES (?, ?, ?, 'DEPOSIT', ?, ?, ?, 'SUCCESS', ?);
            """, (
                txn_ref,
                account_id,
                user_id,
                amount_paise,
                new_balance_paise,
                desc_cleaned,
                now_iso
            ))

            txn_id = cursor.lastrowid

            # 4. Audit Log & In-App Notification
            log_audit_event(
                user_id,
                "DEPOSIT_SUCCESS",
                f"Deposited {format_currency(amount_paise)} into account {acc['account_number']}. Ref: {txn_ref}",
                db_path
            )
            send_notification(
                user_id,
                "Deposit Successful",
                f"{format_currency(amount_paise)} was deposited into account {mask_account_number(acc['account_number'])}. Updated balance: {format_currency(new_balance_paise)}.",
                db_path
            )

            receipt = {
                "transaction_id": txn_id,
                "reference_no": txn_ref,
                "type": "DEPOSIT",
                "account_number": acc["account_number"],
                "account_type": acc["account_type"],
                "amount_paise": amount_paise,
                "amount_formatted": format_currency(amount_paise),
                "balance_after_paise": new_balance_paise,
                "balance_after_formatted": format_currency(new_balance_paise),
                "description": desc_cleaned,
                "status": "SUCCESS",
                "timestamp": now_iso
            }
            return True, f"Successfully deposited {format_currency(amount_paise)}!", receipt

    except Exception as e:
        return False, f"Deposit transaction failed: {str(e)}", None


# ============================================================================
# WITHDRAWAL OPERATION
# ============================================================================

def process_withdrawal(
    user_id: int,
    account_id: int,
    amount_paise: int,
    description: str = "",
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Process an atomic withdrawal from a user-owned account.
    Guarantees no overdraft / negative balance.
    """
    if amount_paise <= 0:
        return False, "Withdrawal amount must be greater than zero.", None

    if amount_paise > MAX_TRANSACTION_LIMIT_PAISE:
        return False, f"Withdrawal exceeds per-transaction limit of {format_currency(MAX_TRANSACTION_LIMIT_PAISE)}.", None

    desc_cleaned = description.strip() or "Standard Withdrawal"
    now_iso = get_current_iso()
    txn_ref = generate_transaction_ref(prefix="WTH")

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # 1. Verify account ownership and active status
            cursor.execute("""
                SELECT id, account_number, account_type, balance_paise, is_active
                FROM accounts
                WHERE id = ? AND user_id = ?;
            """, (account_id, user_id))
            acc = cursor.fetchone()

            if not acc:
                return False, "Account not found or access denied.", None

            if not acc["is_active"]:
                return False, "Account is frozen/inactive. Withdrawals are disabled.", None

            current_balance = acc["balance_paise"]
            if current_balance < amount_paise:
                return False, f"Insufficient funds. Available: {format_currency(current_balance)}, Requested: {format_currency(amount_paise)}.", None

            new_balance_paise = current_balance - amount_paise

            # 2. Strict atomic debit with safeguard condition
            cursor.execute("""
                UPDATE accounts
                SET balance_paise = balance_paise - ?, updated_at = ?
                WHERE id = ? AND balance_paise >= ?;
            """, (amount_paise, now_iso, account_id, amount_paise))

            if cursor.rowcount == 0:
                return False, "Transaction declined: Insufficient balance or concurrent modification.", None

            # 3. Create Transaction Record
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, account_id, user_id, transaction_type,
                    amount_paise, balance_after_paise, description, status, created_at
                ) VALUES (?, ?, ?, 'WITHDRAWAL', ?, ?, ?, 'SUCCESS', ?);
            """, (
                txn_ref,
                account_id,
                user_id,
                amount_paise,
                new_balance_paise,
                desc_cleaned,
                now_iso
            ))

            txn_id = cursor.lastrowid

            # 4. Audit Log & In-App Notification
            log_audit_event(
                user_id,
                "WITHDRAWAL_SUCCESS",
                f"Withdrew {format_currency(amount_paise)} from account {acc['account_number']}. Ref: {txn_ref}",
                db_path
            )
            send_notification(
                user_id,
                "Withdrawal Confirmed",
                f"{format_currency(amount_paise)} was withdrawn from account {mask_account_number(acc['account_number'])}. Remaining balance: {format_currency(new_balance_paise)}.",
                db_path
            )

            receipt = {
                "transaction_id": txn_id,
                "reference_no": txn_ref,
                "type": "WITHDRAWAL",
                "account_number": acc["account_number"],
                "account_type": acc["account_type"],
                "amount_paise": amount_paise,
                "amount_formatted": format_currency(amount_paise),
                "balance_after_paise": new_balance_paise,
                "balance_after_formatted": format_currency(new_balance_paise),
                "description": desc_cleaned,
                "status": "SUCCESS",
                "timestamp": now_iso
            }
            return True, f"Successfully withdrew {format_currency(amount_paise)}!", receipt

    except Exception as e:
        return False, f"Withdrawal transaction failed: {str(e)}", None


# ============================================================================
# TRANSFER OPERATION
# ============================================================================

def process_transfer(
    sender_user_id: int,
    sender_account_id: int,
    recipient_account_number: str,
    amount_paise: int,
    description: str = "",
    transaction_pin: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute an atomic transfer between sender and recipient accounts.
    Both debit and credit succeed together or rollback on any error.
    """
    from auth import verify_user_pin

    if amount_paise <= 0:
        return False, "Transfer amount must be positive.", None

    if amount_paise > MAX_TRANSACTION_LIMIT_PAISE:
        return False, f"Transfer exceeds maximum limit of {format_currency(MAX_TRANSACTION_LIMIT_PAISE)}.", None

    recipient_acc_num = str(recipient_account_number).strip()
    desc_cleaned = description.strip() or "Account-to-Account Transfer"
    now_iso = get_current_iso()
    transfer_ref = generate_transfer_ref()

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # 1. Verify Sender Account & Ownership
            cursor.execute("""
                SELECT a.id, a.account_number, a.account_type, a.balance_paise, a.is_active,
                       u.pin_hash, u.full_name as sender_name
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                WHERE a.id = ? AND a.user_id = ?;
            """, (sender_account_id, sender_user_id))
            sender_acc = cursor.fetchone()

            if not sender_acc:
                return False, "Sender account not found or access denied.", None

            if not sender_acc["is_active"]:
                return False, "Sender account is frozen/inactive.", None

            # 2. Transaction PIN Verification if configured
            if sender_acc["pin_hash"]:
                if not transaction_pin:
                    return False, "Transaction PIN is required to complete this transfer.", None
                if not verify_user_pin(sender_user_id, transaction_pin, db_path):
                    log_audit_event(sender_user_id, "TRANSFER_PIN_FAILED", "Incorrect transaction PIN entered", db_path)
                    return False, "Incorrect transaction PIN. Transfer cancelled.", None

            # 3. Check sufficient balance
            sender_current_balance = sender_acc["balance_paise"]
            if sender_current_balance < amount_paise:
                return False, f"Insufficient balance for transfer. Available: {format_currency(sender_current_balance)}.", None

            # 4. Lookup Recipient Account
            cursor.execute("""
                SELECT a.id, a.user_id, a.account_number, a.account_type, a.balance_paise,
                       a.is_active, u.full_name as receiver_name, u.username as receiver_username
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                WHERE a.account_number = ?;
            """, (recipient_acc_num,))
            recipient_acc = cursor.fetchone()

            if not recipient_acc:
                return False, f"Recipient account '{recipient_acc_num}' does not exist.", None

            if recipient_acc["id"] == sender_account_id:
                return False, "Cannot transfer funds to the same account.", None

            if not recipient_acc["is_active"]:
                return False, "Recipient account is currently inactive.", None

            recipient_user_id = recipient_acc["user_id"]
            sender_new_balance = sender_current_balance - amount_paise
            recipient_new_balance = recipient_acc["balance_paise"] + amount_paise

            # 5. ATOMIC BALANCE UPDATES
            # Debit Sender
            cursor.execute("""
                UPDATE accounts
                SET balance_paise = balance_paise - ?, updated_at = ?
                WHERE id = ? AND balance_paise >= ?;
            """, (amount_paise, now_iso, sender_account_id, amount_paise))

            if cursor.rowcount == 0:
                return False, "Transfer failed: Sender balance was insufficient or modified concurrently.", None

            # Credit Recipient
            cursor.execute("""
                UPDATE accounts
                SET balance_paise = balance_paise + ?, updated_at = ?
                WHERE id = ?;
            """, (amount_paise, now_iso, recipient_acc["id"]))

            # 6. Insert Linked Transaction Records
            sender_txn_ref = f"{transfer_ref}-DR"
            recipient_txn_ref = f"{transfer_ref}-CR"

            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, account_id, user_id, transaction_type,
                    amount_paise, balance_after_paise, description, status, created_at
                ) VALUES (?, ?, ?, 'TRANSFER_DEBIT', ?, ?, ?, 'SUCCESS', ?);
            """, (
                sender_txn_ref,
                sender_account_id,
                sender_user_id,
                amount_paise,
                sender_new_balance,
                f"Transfer to {recipient_acc['holder_name'] if 'holder_name' in recipient_acc.keys() else recipient_acc['receiver_name']} ({mask_account_number(recipient_acc['account_number'])}): {desc_cleaned}",
                now_iso
            ))
            sender_txn_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, account_id, user_id, transaction_type,
                    amount_paise, balance_after_paise, description, status, created_at
                ) VALUES (?, ?, ?, 'TRANSFER_CREDIT', ?, ?, ?, 'SUCCESS', ?);
            """, (
                recipient_txn_ref,
                recipient_acc["id"],
                recipient_user_id,
                amount_paise,
                recipient_new_balance,
                f"Transfer from {sender_acc['sender_name']} ({mask_account_number(sender_acc['account_number'])}): {desc_cleaned}",
                now_iso
            ))
            recipient_txn_id = cursor.lastrowid

            # 7. Record Transfer Mapping
            cursor.execute("""
                INSERT INTO transfers (
                    transfer_ref, sender_account_id, receiver_account_id,
                    sender_transaction_id, receiver_transaction_id, amount_paise,
                    description, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'SUCCESS', ?);
            """, (
                transfer_ref,
                sender_account_id,
                recipient_acc["id"],
                sender_txn_id,
                recipient_txn_id,
                amount_paise,
                desc_cleaned,
                now_iso
            ))

            # 8. Dispatch Notifications and Audit Logs
            log_audit_event(
                sender_user_id,
                "TRANSFER_SENT",
                f"Transferred {format_currency(amount_paise)} from {sender_acc['account_number']} to {recipient_acc['account_number']}. Ref: {transfer_ref}",
                db_path
            )

            send_notification(
                sender_user_id,
                "Transfer Sent",
                f"Sent {format_currency(amount_paise)} to {recipient_acc['receiver_name']} ({mask_account_number(recipient_acc['account_number'])}). Remaining balance: {format_currency(sender_new_balance)}.",
                db_path
            )

            send_notification(
                recipient_user_id,
                "Funds Received",
                f"Received {format_currency(amount_paise)} from {sender_acc['sender_name']} into account {mask_account_number(recipient_acc['account_number'])}.",
                db_path
            )

            receipt = {
                "transaction_id": sender_txn_id,
                "reference_no": transfer_ref,
                "type": "TRANSFER",
                "sender_account": sender_acc["account_number"],
                "sender_name": sender_acc["sender_name"],
                "recipient_account": recipient_acc["account_number"],
                "recipient_name": recipient_acc["receiver_name"],
                "amount_paise": amount_paise,
                "amount_formatted": format_currency(amount_paise),
                "balance_after_paise": sender_new_balance,
                "balance_after_formatted": format_currency(sender_new_balance),
                "description": desc_cleaned,
                "status": "SUCCESS",
                "timestamp": now_iso
            }
            return True, f"Transfer of {format_currency(amount_paise)} completed successfully!", receipt

    except Exception as e:
        return False, f"Transfer failed: {str(e)}", None


# ============================================================================
# TRANSACTION QUERIES & ANALYTICS
# ============================================================================

def get_user_transactions(
    user_id: int,
    account_id: Optional[int] = None,
    txn_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    sort_by: str = "date_desc",
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Fetch and filter transactions for an authenticated user with multiple filter criteria.
    Never exposes transactions belonging to other users.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT t.id, t.transaction_ref, t.account_id, t.user_id,
                   t.transaction_type, t.amount_paise, t.balance_after_paise,
                   t.description, t.status, t.created_at,
                   a.account_number, a.account_type
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = ?
        """
        params: List[Any] = [user_id]

        if account_id:
            query += " AND t.account_id = ?"
            params.append(account_id)

        if txn_type and txn_type != "ALL":
            query += " AND t.transaction_type = ?"
            params.append(txn_type)

        if start_date:
            query += " AND t.created_at >= ?"
            params.append(f"{start_date}T00:00:00")

        if end_date:
            query += " AND t.created_at <= ?"
            params.append(f"{end_date}T23:59:59")

        if search_query:
            query += " AND (t.transaction_ref LIKE ? OR t.description LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term])

        # Sorting
        if sort_by == "date_asc":
            query += " ORDER BY t.created_at ASC"
        elif sort_by == "amount_desc":
            query += " ORDER BY t.amount_paise DESC"
        elif sort_by == "amount_asc":
            query += " ORDER BY t.amount_paise ASC"
        else:
            query += " ORDER BY t.created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_dashboard_summary(user_id: int, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Calculate full analytics for the customer dashboard:
    - total balance
    - active accounts count
    - total deposits amount
    - total withdrawals amount
    - recent transactions
    - monthly breakdown DataFrame
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Accounts total balance and count
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(balance_paise), 0) as total_balance
            FROM accounts
            WHERE user_id = ? AND is_active = 1;
        """, (user_id,))
        acc_row = cursor.fetchone()
        active_accounts_count = acc_row["count"] if acc_row else 0
        total_balance_paise = acc_row["total_balance"] if acc_row else 0

        # 2. Total Inflow (Deposits & Credit transfers)
        cursor.execute("""
            SELECT COALESCE(SUM(amount_paise), 0) as total_inflow
            FROM transactions
            WHERE user_id = ? AND status = 'SUCCESS'
              AND transaction_type IN ('DEPOSIT', 'TRANSFER_CREDIT');
        """, (user_id,))
        inflow_row = cursor.fetchone()
        total_deposit_paise = inflow_row["total_inflow"] if inflow_row else 0

        # 3. Total Outflow (Withdrawals & Debit transfers)
        cursor.execute("""
            SELECT COALESCE(SUM(amount_paise), 0) as total_outflow
            FROM transactions
            WHERE user_id = ? AND status = 'SUCCESS'
              AND transaction_type IN ('WITHDRAWAL', 'TRANSFER_DEBIT');
        """, (user_id,))
        outflow_row = cursor.fetchone()
        total_withdraw_paise = outflow_row["total_outflow"] if outflow_row else 0

        # 4. Recent 5 transactions
        cursor.execute("""
            SELECT t.id, t.transaction_ref, t.transaction_type, t.amount_paise,
                   t.balance_after_paise, t.description, t.status, t.created_at,
                   a.account_number, a.account_type
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
            LIMIT 5;
        """, (user_id,))
        recent_txns = [dict(r) for r in cursor.fetchall()]

        # 5. Recent notifications
        cursor.execute("""
            SELECT id, title, message, is_read, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 4;
        """, (user_id,))
        notifications = [dict(r) for r in cursor.fetchall()]

        # 6. Monthly Breakdown for interactive charts
        cursor.execute("""
            SELECT strftime('%Y-%m', created_at) as month,
                   transaction_type,
                   SUM(amount_paise) as total_paise
            FROM transactions
            WHERE user_id = ? AND status = 'SUCCESS'
            GROUP BY month, transaction_type
            ORDER BY month ASC;
        """, (user_id,))
        monthly_rows = [dict(r) for r in cursor.fetchall()]

        return {
            "total_balance_paise": total_balance_paise,
            "active_accounts_count": active_accounts_count,
            "total_deposit_paise": total_deposit_paise,
            "total_withdraw_paise": total_withdraw_paise,
            "recent_transactions": recent_txns,
            "notifications": notifications,
            "monthly_breakdown": monthly_rows
        }


def get_admin_system_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate aggregate bank-wide metrics for the Administrator dashboard."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'customer';")
        total_customers = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(balance_paise), 0) as total_assets FROM accounts;")
        acc_stats = cursor.fetchone()
        total_accounts = acc_stats["count"]
        total_assets_paise = acc_stats["total_assets"]

        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(amount_paise), 0) as total_vol FROM transactions WHERE status = 'SUCCESS';")
        txn_stats = cursor.fetchone()
        total_transactions = txn_stats["count"]
        total_volume_paise = txn_stats["total_vol"]

        # Recent system audit logs
        cursor.execute("""
            SELECT a.id, a.user_id, a.action, a.details, a.ip_address, a.created_at,
                   u.username, u.full_name
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 30;
        """)
        audit_logs = [dict(r) for r in cursor.fetchall()]

        # All accounts list for admin inspection
        cursor.execute("""
            SELECT a.id, a.account_number, a.account_type, a.balance_paise, a.is_active,
                   a.created_at, u.full_name as customer_name, u.email, u.username
            FROM accounts a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC;
        """)
        all_accounts = [dict(r) for r in cursor.fetchall()]

        return {
            "total_customers": total_customers,
            "total_accounts": total_accounts,
            "total_assets_paise": total_assets_paise,
            "total_transactions": total_transactions,
            "total_volume_paise": total_volume_paise,
            "audit_logs": audit_logs,
            "all_accounts": all_accounts
        }
