"""
Withdraw Funds page allowing customers to withdraw funds from their accounts safely.
Enforces zero-overdraft guarantee, confirmation steps, and provides downloadable receipts.
"""

import streamlit as st

from auth import require_login
from services.account_service import get_user_accounts
from services.receipt_service import generate_receipt_pdf, render_receipt_html
from services.transaction_service import process_withdrawal
from utils import format_currency, rupees_to_paise

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Financial Outflow</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Withdraw Money</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Withdraw funds safely from your active accounts without overdraft risk.</p>
</div>
""", unsafe_allow_html=True)

accounts = get_user_accounts(user_id, active_only=True)

if not accounts:
    st.warning("You do not have any active accounts available. Please check your accounts.")
    st.stop()

# Build Account Selector
acc_map = {a["id"]: a for a in accounts}
acc_labels = {a["id"]: f"{a['account_type']} • {a['account_number']} (Available: {format_currency(a['balance_paise'])})" for a in accounts}

default_acc_id = st.session_state.get("selected_account_id")
default_idx = list(acc_map.keys()).index(default_acc_id) if default_acc_id in acc_map else 0

col_form, col_info = st.columns([3, 2])

with col_info:
    st.markdown("### ⚠️ Security Guidelines")
    st.markdown("""
    <div class="bms-card">
        <ul style="color: #475569; font-size: 0.9rem; margin: 0; padding-left: 1.2rem;">
            <li>Withdrawal amounts cannot exceed your <strong>cleared available balance</strong>.</li>
            <li>Zero overdraft policy: Accounts will never slip into negative balance.</li>
            <li>Every withdrawal is accompanied by an authenticated digital audit signature.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_form:
    selected_id = st.selectbox(
        "Choose Source Account",
        options=list(acc_map.keys()),
        format_func=lambda x: acc_labels[x],
        index=default_idx
    )
    chosen_account = acc_map[selected_id]
    current_bal_paise = chosen_account["balance_paise"]

    st.markdown(f"**Available Account Balance:** `{format_currency(current_bal_paise)}`")

    with st.form("withdraw_form", clear_on_submit=False):
        amount_rupees = st.number_input(
            "Withdrawal Amount (₹)",
            min_value=1.0,
            max_value=1_000_000.0,
            step=100.0,
            value=min(500.0, float(current_bal_paise) / 100.0) if current_bal_paise > 0 else 100.0,
            format="%.2f",
            help="Enter amount to withdraw in Indian Rupees"
        )
        description = st.text_input("Transaction Reason / Memo (Optional)", placeholder="e.g. ATM Cash, Personal Expenses")

        st.markdown("##### ⚠️ Authorization Confirmation")
        confirm_wth = st.checkbox(
            f"I authorize the debit of {format_currency(rupees_to_paise(amount_rupees))} from account {chosen_account['account_number']}."
        )

        submit_btn = st.form_submit_button("Authorize & Process Withdrawal", use_container_width=True)

        if submit_btn:
            wth_paise = rupees_to_paise(amount_rupees)
            if not confirm_wth:
                st.error("Please confirm your authorization by checking the box above.")
            elif wth_paise > current_bal_paise:
                st.error(f"Declined: Requested amount ({format_currency(wth_paise)}) exceeds available balance ({format_currency(current_bal_paise)}).")
            else:
                with st.spinner("Executing secure balance deduction..."):
                    ok, msg, receipt = process_withdrawal(
                        user_id=user_id,
                        account_id=selected_id,
                        amount_paise=wth_paise,
                        description=description
                    )

                    if ok and receipt:
                        st.session_state["last_withdraw_receipt"] = receipt
                        st.success(f"🎉 {msg}")
                    else:
                        st.error(msg)

# Display Receipt if a withdrawal was just completed
if "last_withdraw_receipt" in st.session_state and st.session_state["last_withdraw_receipt"]:
    st.markdown("---")
    st.markdown("### 🧾 Transaction Receipt")
    receipt_data = st.session_state["last_withdraw_receipt"]

    col_rec, col_dl = st.columns([2, 1])
    with col_rec:
        render_receipt_html(receipt_data)
    with col_dl:
        st.markdown("<br><br>", unsafe_allow_html=True)
        pdf_bytes = generate_receipt_pdf(receipt_data)
        st.download_button(
            label="📥 Download PDF Receipt",
            data=pdf_bytes,
            file_name=f"BMS_Receipt_{receipt_data['reference_no']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("Close Receipt", use_container_width=True):
            st.session_state["last_withdraw_receipt"] = None
            st.rerun()
