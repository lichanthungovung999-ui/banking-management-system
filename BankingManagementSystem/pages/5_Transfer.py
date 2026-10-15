"""
Transfer Money page for executing atomic fund transfers between BMS bank accounts.
Includes beneficiary account validation, transaction PIN verification,
and downloadable receipts.
"""

import streamlit as st

from auth import require_login
from services.account_service import get_account_by_number, get_user_accounts
from services.receipt_service import generate_receipt_pdf, render_receipt_html
from services.transaction_service import process_transfer
from utils import format_currency, mask_account_number, rupees_to_paise

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Peer-to-Peer & Internal Banking</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Transfer Money</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Send money instantly to any verified BMS account holder with atomic transaction safety.</p>
</div>
""", unsafe_allow_html=True)

accounts = get_user_accounts(user_id, active_only=True)

if not accounts:
    st.warning("You do not have any active source accounts. Please open or reactivate an account.")
    st.stop()

# Build Source Account Selector
acc_map = {a["id"]: a for a in accounts}
acc_labels = {a["id"]: f"{a['account_type']} • {a['account_number']} (Balance: {format_currency(a['balance_paise'])})" for a in accounts}

default_acc_id = st.session_state.get("selected_account_id")
default_idx = list(acc_map.keys()).index(default_acc_id) if default_acc_id in acc_map else 0

col_transfer, col_info = st.columns([3, 2])

with col_info:
    st.markdown("### 🔒 Secure Transfer Protocols")
    st.markdown("""
    <div class="bms-card">
        <div style="font-size: 0.9rem; color: #475569;">
            <p><strong>Atomic Guarantee:</strong> Both sender debit and recipient credit succeed simultaneously. If any glitch occurs, all funds remain untouched.</p>
            <p><strong>PIN Protection:</strong> If you have set up a Transaction PIN in your Profile Settings, you must enter it to authorize all outward transfers.</p>
            <p><strong>Instant Settlement:</strong> Transfers within BMS Bank settle in real-time with zero hold periods.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_transfer:
    selected_source_id = st.selectbox(
        "Select Debit (Sender) Account",
        options=list(acc_map.keys()),
        format_func=lambda x: acc_labels[x],
        index=default_idx
    )
    source_acc = acc_map[selected_source_id]
    source_bal_paise = source_acc["balance_paise"]

    # Pre-fill beneficiary account if coming from QR payments
    prefill_acc = st.session_state.get("qr_target_account", "")

    recipient_acc_num = st.text_input(
        "Recipient Account Number (12 Digits)",
        value=prefill_acc,
        max_chars=12,
        placeholder="e.g. 1001XXXXXXXX",
        help="Enter the exact 12-digit BMS bank account number"
    ).strip()

    beneficiary_info = None
    if recipient_acc_num:
        if len(recipient_acc_num) == 12:
            beneficiary_info = get_account_by_number(recipient_acc_num)
            if beneficiary_info:
                if beneficiary_info["id"] == selected_source_id:
                    st.warning("⚠️ You entered your own selected source account number. Cannot transfer to the same account.")
                elif not beneficiary_info["is_active"]:
                    st.error("⚠️ Recipient account is currently frozen/inactive.")
                else:
                    st.success(f"Verified Beneficiary: **{beneficiary_info['holder_name']}** ({beneficiary_info['account_type']} Account)")
            else:
                st.error("❌ No account found with this account number. Please verify.")
        else:
            st.caption("Enter full 12 digits to verify the recipient.")

    with st.form("transfer_form", clear_on_submit=False):
        amount_rupees = st.number_input(
            "Transfer Amount (₹)",
            min_value=1.0,
            max_value=1_000_000.0,
            step=50.0,
            value=min(500.0, float(source_bal_paise) / 100.0) if source_bal_paise > 0 else 100.0,
            format="%.2f"
        )

        transfer_note = st.text_input("Payment Purpose / Note (Optional)", placeholder="e.g. Dinner split, Rent, Project work")

        # Transaction PIN check
        has_pin = bool(user.get("has_pin"))
        pin_input = None
        if has_pin:
            pin_input = st.text_input(
                "Transaction PIN",
                type="password",
                max_chars=6,
                placeholder="Enter your 4 or 6-digit PIN",
                help="Enter the transaction PIN configured in your profile"
            )
        else:
            st.caption("💡 *Tip: You can set a Transaction PIN in Profile & Settings for additional transfer security.*")

        confirm_transfer = st.checkbox(
            f"I confirm this irreversible transfer of {format_currency(rupees_to_paise(amount_rupees))} to account {recipient_acc_num}."
        )

        submit_btn = st.form_submit_button("Authorize & Transfer Funds", use_container_width=True)

        if submit_btn:
            transfer_paise = rupees_to_paise(amount_rupees)

            if not recipient_acc_num or len(recipient_acc_num) != 12:
                st.error("Please provide a valid 12-digit recipient account number.")
            elif not confirm_transfer:
                st.error("Please check the confirmation box to authorize the transfer.")
            elif transfer_paise > source_bal_paise:
                st.error(f"Insufficient balance. Your available balance is {format_currency(source_bal_paise)}.")
            elif beneficiary_info and beneficiary_info["id"] == selected_source_id:
                st.error("Cannot transfer funds to the same account.")
            elif has_pin and not pin_input:
                st.error("Transaction PIN is required.")
            else:
                with st.spinner("Executing atomic ledger transfer..."):
                    ok, msg, receipt = process_transfer(
                        sender_user_id=user_id,
                        sender_account_id=selected_source_id,
                        recipient_account_number=recipient_acc_num,
                        amount_paise=transfer_paise,
                        description=transfer_note,
                        transaction_pin=pin_input
                    )

                    if ok and receipt:
                        st.session_state["last_transfer_receipt"] = receipt
                        # Clear any stored QR state
                        st.session_state["qr_target_account"] = ""
                        st.success(f"🎉 {msg}")
                    else:
                        st.error(msg)

# Display Receipt
if "last_transfer_receipt" in st.session_state and st.session_state["last_transfer_receipt"]:
    st.markdown("---")
    st.markdown("### 🧾 Official Transfer Receipt")
    receipt_data = st.session_state["last_transfer_receipt"]

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
            st.session_state["last_transfer_receipt"] = None
            st.rerun()
