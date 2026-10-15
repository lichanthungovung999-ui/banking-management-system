"""
Account management page for viewing, creating, searching, and selecting bank accounts.
"""

import streamlit as st

from auth import require_login
from services.account_service import create_account, get_user_accounts
from styles import render_bank_card_widget
from utils import format_currency, format_datetime, mask_account_number

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Portfolio Management</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">My Bank Accounts</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">View your linked accounts, inspect balance details, or open a new account.</p>
</div>
""", unsafe_allow_html=True)

# Fetch user accounts
accounts = get_user_accounts(user_id)

col_cards, col_action = st.columns([2, 1])

with col_action:
    # ---------------------------------------------------------
    # OPEN NEW ACCOUNT FORM
    # ---------------------------------------------------------
    st.markdown("### ➕ Open New Account")
    with st.form("create_account_form", clear_on_submit=True):
        st.write("You can open multiple accounts under your verified profile.")
        acc_type_choice = st.selectbox(
            "Select Account Type",
            ["Savings", "Current"],
            help="Savings offers daily interest calculation. Current offers higher transaction limits."
        )
        submit_create = st.form_submit_button("Open Account", use_container_width=True)

        if submit_create:
            with st.spinner("Generating account and allocating unique account number..."):
                ok, msg, new_acc = create_account(user_id, acc_type_choice)
                if ok and new_acc:
                    st.success(f"🎉 {msg}")
                    st.info(f"New Account Number: **{new_acc['account_number']}**")
                    st.session_state["selected_account_id"] = new_acc["id"]
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")
    st.markdown("### 📌 Active Account Selection")
    if accounts:
        acc_options = {acc["id"]: f"{acc['account_type']} • {acc['account_number']} ({format_currency(acc['balance_paise'])})" for acc in accounts}
        current_selection = st.session_state.get("selected_account_id")
        # Default to first account if none selected
        default_idx = list(acc_options.keys()).index(current_selection) if current_selection in acc_options else 0

        selected_id = st.selectbox(
            "Selected Account for Quick Actions",
            options=list(acc_options.keys()),
            format_func=lambda x: acc_options[x],
            index=default_idx
        )
        st.session_state["selected_account_id"] = selected_id
        st.caption("This account will be pre-selected in Deposit, Withdraw, and Transfer pages.")

with col_cards:
    # ---------------------------------------------------------
    # SEARCH & FILTER
    # ---------------------------------------------------------
    search_col, filter_col = st.columns([2, 1])
    with search_col:
        search_query = st.text_input("🔍 Search Accounts", placeholder="Search by account number...").strip()
    with filter_col:
        type_filter = st.selectbox("Filter Type", ["All Types", "Savings", "Current"])

    # Filter list
    filtered_accounts = accounts
    if search_query:
        filtered_accounts = [a for a in filtered_accounts if search_query in a["account_number"]]
    if type_filter != "All Types":
        filtered_accounts = [a for a in filtered_accounts if a["account_type"] == type_filter]

    st.markdown(f"### 💳 Your Accounts ({len(filtered_accounts)})")

    if not filtered_accounts:
        st.info("No accounts matched your search criteria.")
    else:
        for acc in filtered_accounts:
            is_active = bool(acc["is_active"])
            bal_str = format_currency(acc["balance_paise"])
            is_currently_selected = (acc["id"] == st.session_state.get("selected_account_id"))

            with st.container():
                # Realistic Bank Debit Card UI
                render_bank_card_widget(
                    account_number=acc["account_number"],
                    account_type=acc["account_type"],
                    balance_str=bal_str,
                    holder_name=user["full_name"],
                    is_active=is_active
                )

                # Card metadata row
                meta_col1, meta_col2, meta_col3 = st.columns([2, 2, 1])
                with meta_col1:
                    st.caption(f"📅 **Opened:** {format_datetime(acc['created_at'])}")
                with meta_col2:
                    status_badge = "🟢 Active" if is_active else "🔴 Frozen"
                    sel_badge = " ⭐ (Active Selection)" if is_currently_selected else ""
                    st.caption(f"**Status:** {status_badge}{sel_badge}")
                with meta_col3:
                    if not is_currently_selected:
                        if st.button("Select", key=f"sel_acc_{acc['id']}", use_container_width=True):
                            st.session_state["selected_account_id"] = acc["id"]
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
