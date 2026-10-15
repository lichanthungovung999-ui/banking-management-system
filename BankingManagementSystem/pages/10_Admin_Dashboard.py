"""
Administrator Dashboard for bank managers and auditors.
Provides bank-wide metrics, customer search, account freezing/unfreezing,
and comprehensive system audit logs.
"""

import pandas as pd
import streamlit as st

from auth import require_login
from database import get_db_connection
from services.account_service import toggle_account_status
from services.transaction_service import get_admin_system_stats
from styles import render_metric_card
from utils import format_currency, format_datetime, mask_account_number

# Enforce Administrator Authentication
admin_user = require_login(required_role="admin")
admin_id = admin_user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #dc2626; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Administrative Terminal</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Bank Administration Console</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Supervise customer accounts, audit transactions, and review system operations.</p>
</div>
""", unsafe_allow_html=True)

# Fetch System Analytics
stats = get_admin_system_stats()

# -------------------------------------------------------------
# HIGH-LEVEL SYSTEM METRICS
# -------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    render_metric_card("Registered Customers", str(stats["total_customers"]), "Verified retail clients", delta_type="info")

with kpi2:
    render_metric_card("Total Bank Accounts", str(stats["total_accounts"]), "Savings & Current accounts", delta_type="positive")

with kpi3:
    render_metric_card("Bank Total Deposits", format_currency(stats["total_assets_paise"]), "Cumulative ledger balance", delta_type="positive")

with kpi4:
    render_metric_card("Transaction Volume", format_currency(stats["total_volume_paise"]), f"{stats['total_transactions']} processed transactions", delta_type="info")

st.markdown("<br>", unsafe_allow_html=True)

tab_accounts, tab_txns, tab_audit = st.tabs([
    "🏦 Customer Accounts & Controls",
    "🔍 Bank-Wide Transactions",
    "📜 System Audit Trail"
])

# -------------------------------------------------------------
# TAB 1: ACCOUNTS & FREEZE / UNFREEZE
# -------------------------------------------------------------
with tab_accounts:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Customer Account Roster")

    all_accounts = stats["all_accounts"]

    search_term = st.text_input("🔍 Search by customer name, email, or account number", placeholder="e.g. Rajesh, 1001...").strip().lower()

    if search_term:
        all_accounts = [
            a for a in all_accounts
            if search_term in a["account_number"].lower()
            or search_term in (a["customer_name"] or "").lower()
            or search_term in (a["email"] or "").lower()
        ]

    if not all_accounts:
        st.info("No accounts matched your search.")
    else:
        # Table of accounts
        acc_rows = []
        for a in all_accounts:
            acc_rows.append({
                "Account No": a["account_number"],
                "Customer Name": a["customer_name"],
                "Email": a["email"],
                "Type": a["account_type"],
                "Balance": format_currency(a["balance_paise"]),
                "Status": "🟢 Active" if a["is_active"] else "🔴 Frozen",
                "Created At": format_datetime(a["created_at"])
            })

        st.dataframe(pd.DataFrame(acc_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ⚙️ Account Management Actions")
        st.write("Freeze or unfreeze an account with mandatory audit recording.")

        freeze_col1, freeze_col2 = st.columns(2)

        acc_choices = {a["id"]: f"{a['account_number']} - {a['customer_name']} ({'Active' if a['is_active'] else 'Frozen'})" for a in all_accounts}

        with freeze_col1:
            selected_admin_acc_id = st.selectbox(
                "Select Target Account",
                options=list(acc_choices.keys()),
                format_func=lambda x: acc_choices[x]
            )

        target_acc = next((a for a in all_accounts if a["id"] == selected_admin_acc_id), None)

        if target_acc:
            is_currently_active = bool(target_acc["is_active"])
            action_label = "Freeze Account" if is_currently_active else "Unfreeze Account"
            new_target_status = not is_currently_active

            with freeze_col2:
                action_reason = st.text_input(
                    "Reason for Status Modification",
                    placeholder="e.g. Customer request, KYC compliance, Security review"
                )

                if st.button(f"⚠️ {action_label}", use_container_width=True, type="secondary"):
                    if not action_reason.strip():
                        st.error("A reason must be documented for this administrative audit action.")
                    else:
                        with st.spinner("Updating account status and recording audit trail..."):
                            ok, msg = toggle_account_status(
                                account_id=selected_admin_acc_id,
                                admin_user_id=admin_id,
                                is_active=new_target_status,
                                reason=action_reason.strip()
                            )
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

# -------------------------------------------------------------
# TAB 2: BANK-WIDE TRANSACTIONS
# -------------------------------------------------------------
with tab_txns:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Bank-Wide Transaction Registry")
    st.write("Immutable ledger of all customer deposits, withdrawals, and transfers.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.transaction_ref, t.transaction_type, t.amount_paise,
                   t.balance_after_paise, t.status, t.created_at,
                   a.account_number, u.full_name as customer_name
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
            LIMIT 100;
        """)
        txn_records = [dict(r) for r in cursor.fetchall()]

    if txn_records:
        txn_display_list = []
        for r in txn_records:
            is_credit = r["transaction_type"] in ("DEPOSIT", "TRANSFER_CREDIT")
            txn_display_list.append({
                "Reference": r["transaction_ref"],
                "Timestamp": format_datetime(r["created_at"]),
                "Customer": r["customer_name"],
                "Account": mask_account_number(r["account_number"]),
                "Type": r["transaction_type"],
                "Amount": f"{'+' if is_credit else '-'}{format_currency(r['amount_paise'])}",
                "Balance After": format_currency(r["balance_after_paise"]),
                "Status": r["status"]
            })
        st.dataframe(pd.DataFrame(txn_display_list), use_container_width=True, hide_index=True)
    else:
        st.info("No transactions logged in the system yet.")

# -------------------------------------------------------------
# TAB 3: SYSTEM AUDIT TRAIL
# -------------------------------------------------------------
with tab_audit:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Security & System Audit Trail")
    st.write("Complete cryptographic and operational audit logs for compliance review.")

    audit_logs = stats["audit_logs"]

    if audit_logs:
        audit_rows = []
        for log in audit_logs:
            user_label = f"{log['full_name']} (@{log['username']})" if log.get("username") else "System / Unauthenticated"
            audit_rows.append({
                "Timestamp": format_datetime(log["created_at"]),
                "Action": log["action"],
                "User": user_label,
                "Details": log["details"],
                "IP Address": log["ip_address"]
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs recorded yet.")
