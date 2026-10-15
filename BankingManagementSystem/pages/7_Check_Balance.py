"""
Check Balance page displaying real-time account balances, account details,
and mini account-specific transaction ledger.
"""

import pandas as pd
import streamlit as st

from auth import require_login
from services.account_service import get_user_accounts
from services.transaction_service import get_user_transactions
from styles import render_bank_card_widget
from utils import format_currency, format_datetime, mask_account_number

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Real-time Inquiry</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Check Account Balance</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Inspect available cleared funds and recent ledger activity for your verified accounts.</p>
</div>
""", unsafe_allow_html=True)

accounts = get_user_accounts(user_id)

if not accounts:
    st.warning("You do not have any registered accounts.")
    st.stop()

acc_map = {a["id"]: a for a in accounts}
acc_labels = {a["id"]: f"{a['account_type']} • {a['account_number']}" for a in accounts}

default_acc_id = st.session_state.get("selected_account_id")
default_idx = list(acc_map.keys()).index(default_acc_id) if default_acc_id in acc_map else 0

top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    selected_id = st.selectbox(
        "Select Account to Inspect",
        options=list(acc_map.keys()),
        format_func=lambda x: acc_labels[x],
        index=default_idx
    )
with top_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Balance", use_container_width=True):
        st.rerun()

chosen_account = acc_map[selected_id]
bal_str = format_currency(chosen_account["balance_paise"])

col_card_preview, col_details = st.columns([1, 1])

with col_card_preview:
    render_bank_card_widget(
        account_number=chosen_account["account_number"],
        account_type=chosen_account["account_type"],
        balance_str=bal_str,
        holder_name=user["full_name"],
        is_active=bool(chosen_account["is_active"])
    )

with col_details:
    st.markdown("### Account Specifications")
    st.markdown(f"""
    <div class="bms-card">
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
            <span style="color: #64748b; font-weight: 500;">Account Number:</span>
            <span style="color: #0f172a; font-weight: 700; font-family: monospace;">{chosen_account['account_number']}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
            <span style="color: #64748b; font-weight: 500;">Account Type:</span>
            <span style="color: #0f172a; font-weight: 700;">{chosen_account['account_type']}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
            <span style="color: #64748b; font-weight: 500;">Status:</span>
            <span style="color: {'#15803d' if chosen_account['is_active'] else '#b91c1c'}; font-weight: 700;">
                {'Active & Operational' if chosen_account['is_active'] else 'Frozen / Suspended'}
            </span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9;">
            <span style="color: #64748b; font-weight: 500;">Opening Date:</span>
            <span style="color: #0f172a; font-weight: 700;">{format_datetime(chosen_account['created_at'])}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;">
            <span style="color: #64748b; font-weight: 500;">Currency:</span>
            <span style="color: #0f172a; font-weight: 700;">INR (Indian Rupee - ₹)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# RECENT ACCOUNT-SPECIFIC ACTIVITY
# -------------------------------------------------------------
st.markdown("### 📋 Recent Ledger Activity for this Account")
account_txns = get_user_transactions(user_id=user_id, account_id=selected_id, sort_by="date_desc")

if account_txns:
    rows = []
    for t in account_txns[:10]:
        is_credit = t["transaction_type"] in ("DEPOSIT", "TRANSFER_CREDIT")
        amount_display = f"{'+' if is_credit else '-'}{format_currency(t['amount_paise'])}"
        rows.append({
            "Date & Time": format_datetime(t["created_at"]),
            "Reference": t["transaction_ref"],
            "Type": t["transaction_type"],
            "Amount": amount_display,
            "Balance After": format_currency(t["balance_after_paise"]),
            "Description": t["description"] or "N/A"
        })
    df_acc_txns = pd.DataFrame(rows)
    st.dataframe(df_acc_txns, use_container_width=True, hide_index=True)
else:
    st.info("No transaction history recorded yet for this account.")
