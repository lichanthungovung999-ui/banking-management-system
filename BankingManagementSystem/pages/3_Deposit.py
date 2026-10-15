"""
Deposit Funds page allowing customers to add funds to their accounts securely.
Includes confirmation step, atomic database updates, and downloadable PDF receipts.
"""

import streamlit as st

from auth import require_login
from services.account_service import get_user_accounts
from services.receipt_service import generate_receipt_pdf, render_receipt_html
from services.transaction_service import process_deposit
from utils import format_currency, rupees_to_paise

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Financial Inflow</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Deposit Money</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Safely deposit funds into your verified BMS bank accounts.</p>
</div>
""", unsafe_allow_html=True)

accounts = get_user_accounts(user_id, active_only=True)

if not accounts:
    st.warning("You do not have any active accounts available for deposit. Please open an account or contact support.")
    st.stop()

# Build Account Selector
acc_map = {a["id"]: a for a in accounts}
acc_labels = {a["id"]: f"{a['account_type']} • {a['account_number']} (Current: {format_currency(a['balance_paise'])})" for a in accounts}

# Select default account
default_acc_id = st.session_state.get("selected_account_id")
default_idx = list(acc_map.keys()).index(default_acc_id) if default_acc_id in acc_map else 0

col_form, col_info = st.columns([3, 2])

with col_info:
    st.markdown("### ℹ️ Deposit Policy")
    st.markdown("""
    <div class="bms-card">
        <ul style="color: #475569; font-size: 0.9rem; margin: 0; padding-left: 1.2rem;">
            <li>Minimum deposit amount: <strong>₹1.00</strong></li>
            <li>Maximum per-transaction limit: <strong>₹10,00,000.00</strong></li>
            <li>Zero transaction fees on standard digital deposits</li>
            <li>Instant balance credit and digital audit receipt generation</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_form:
    selected_id = st.selectbox(
        "Choose Destination Account",
        options=list(acc_map.keys()),
        format_func=lambda x: acc_labels[x],
        index=default_idx
    )
    chosen_account = acc_map[selected_id]

    st.markdown(f"**Available Account Balance:** `{format_currency(chosen_account['balance_paise'])}`")

    with st.form("deposit_form", clear_on_submit=False):
        amount_rupees = st.number_input(
            "Deposit Amount (₹)",
            min_value=1.0,
            max_value=1_000_000.0,
            step=100.0,
            value=1000.0,
            format="%.2f",
            help="Enter deposit amount in Indian Rupees"
        )
        description = st.text_input("Transaction Note / Description (Optional)", placeholder="e.g. Monthly Savings, Cash Deposit")

        st.markdown("##### ⚠️ Confirmation")
        confirm_deposit = st.checkbox(
            f"I confirm the deposit of {format_currency(rupees_to_paise(amount_rupees))} into account {chosen_account['account_number']}."
        )

        submit_btn = st.form_submit_button("Confirm & Process Deposit", use_container_width=True)

        if submit_btn:
            if not confirm_deposit:
                st.error("Please tick the confirmation checkbox to authorize this deposit.")
            elif amount_rupees <= 0:
                st.error("Please enter a valid positive deposit amount.")
            else:
                deposit_paise = rupees_to_paise(amount_rupees)
                with st.spinner("Processing atomic deposit and updating ledger..."):
                    ok, msg, receipt = process_deposit(
                        user_id=user_id,
                        account_id=selected_id,
                        amount_paise=deposit_paise,
                        description=description
                    )

                    if ok and receipt:
                        st.session_state["last_deposit_receipt"] = receipt
                        st.success(f"🎉 {msg}")
                    else:
                        st.error(msg)

# Display Receipt if a deposit was just completed
if "last_deposit_receipt" in st.session_state and st.session_state["last_deposit_receipt"]:
    st.markdown("---")
    st.markdown("### 🧾 Transaction Receipt")
    receipt_data = st.session_state["last_deposit_receipt"]

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
            st.session_state["last_deposit_receipt"] = None
            st.rerun()
