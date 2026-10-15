"""
QR-Code Payment System allowing customers to generate branded payment QR codes
and scan/upload QR codes to execute transfers seamlessly.
"""

import streamlit as st

from auth import require_login
from services.account_service import get_account_by_number, get_user_accounts
from services.qr_service import decode_qr_image, generate_account_qr
from services.receipt_service import generate_receipt_pdf, render_receipt_html
from services.transaction_service import process_transfer
from utils import format_currency, mask_account_number, rupees_to_paise

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Digital Payment Ecosystem</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">QR-Code Payments</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Generate your personalized payment QR or upload a QR image to pay other BMS accounts instantly.</p>
</div>
""", unsafe_allow_html=True)

# Prominent Educational & Regulatory Disclaimer
st.info("""
🛡️ **Simulated Banking Demonstration**: This QR payment system is an internal educational simulation.
It securely encodes only the account reference and does not connect to real UPI or commercial banking networks.
""")

accounts = get_user_accounts(user_id, active_only=True)

if not accounts:
    st.warning("You have no active accounts available for QR payments.")
    st.stop()

acc_map = {a["id"]: a for a in accounts}
acc_labels = {a["id"]: f"{a['account_type']} • {a['account_number']} ({format_currency(a['balance_paise'])})" for a in accounts}

default_acc_id = st.session_state.get("selected_account_id")
default_idx = list(acc_map.keys()).index(default_acc_id) if default_acc_id in acc_map else 0

tab_receive, tab_pay = st.tabs(["📲 My Payment QR (Receive Money)", "📷 Scan / Upload & Pay"])

# -------------------------------------------------------------
# TAB 1: GENERATE MY PAYMENT QR
# -------------------------------------------------------------
with tab_receive:
    st.markdown("<br>", unsafe_allow_html=True)
    col_qr_left, col_qr_right = st.columns([1, 1])

    with col_qr_left:
        st.markdown("### Select Receiving Account")
        selected_rx_id = st.selectbox(
            "Account to Receive Funds",
            options=list(acc_map.keys()),
            format_func=lambda x: acc_labels[x],
            index=default_idx,
            key="rx_qr_select"
        )
        rx_account = acc_map[selected_rx_id]

        st.markdown(f"""
        <div class="bms-card">
            <div style="font-size: 0.85rem; color: #64748b;">Account Holder</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">{user['full_name']}</div>
            <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.5rem;">Account Number</div>
            <div style="font-size: 1.1rem; font-family: monospace; font-weight: 700; color: #2563eb;">{rx_account['account_number']}</div>
            <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.5rem;">Account Type</div>
            <div style="font-size: 1rem; font-weight: 600; color: #0f172a;">{rx_account['account_type']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_qr_right:
        st.markdown("### Your Official BMS Payment QR")
        pil_qr, png_bytes = generate_account_qr(
            account_number=rx_account["account_number"],
            account_holder=user["full_name"],
            account_type=rx_account["account_type"]
        )

        st.image(pil_qr, width=240, caption=f"Scan to pay {user['full_name']} ({rx_account['account_number']})")

        st.download_button(
            label="📥 Download Payment QR Code (PNG)",
            data=png_bytes,
            file_name=f"BMS_QR_{rx_account['account_number']}.png",
            mime="image/png",
            use_container_width=True
        )

# -------------------------------------------------------------
# TAB 2: UPLOAD / SCAN QR AND PAY
# -------------------------------------------------------------
with tab_pay:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Upload QR Code Image to Initiate Payment")
    st.write("Upload a downloaded or photographed BMS payment QR image to automatically read the beneficiary details.")

    uploaded_qr = st.file_uploader(
        "Choose a QR image (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        help="Upload the QR image of the person you wish to pay"
    )

    if uploaded_qr is not None:
        with st.spinner("Decoding QR code using computer vision..."):
            ok_qr, msg_qr, qr_data = decode_qr_image(uploaded_qr)

        if not ok_qr or not qr_data:
            st.error(f"❌ {msg_qr}")
        else:
            dest_acc_num = qr_data.get("account_number", "")
            beneficiary_name = qr_data.get("beneficiary_name", "Verified Customer")
            dest_acc_type = qr_data.get("account_type", "Account")

            st.success(f"✅ Verified QR Target: **{beneficiary_name}** ({dest_acc_num})")

            # Look up account in database to confirm validity
            acc_details = get_account_by_number(dest_acc_num)
            if not acc_details:
                st.error("This account number does not exist in the bank database.")
            elif not acc_details["is_active"]:
                st.error("This destination account is currently inactive/frozen.")
            else:
                col_pay_form, col_pay_preview = st.columns([3, 2])

                with col_pay_preview:
                    st.markdown("#### 🎯 Payment Summary")
                    st.markdown(f"""
                    <div class="bms-card" style="border-left: 4px solid #10b981;">
                        <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase;">Beneficiary</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a;">{acc_details['holder_name']}</div>
                        <div style="font-size: 0.85rem; color: #475569; margin-top: 0.25rem;">Account: {mask_account_number(dest_acc_num)}</div>
                        <div style="font-size: 0.85rem; color: #475569;">Type: {acc_details['account_type']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_pay_form:
                    st.markdown("#### 💳 Enter Payment Details")

                    # Select debit account
                    debit_account_id = st.selectbox(
                        "Pay From Account",
                        options=list(acc_map.keys()),
                        format_func=lambda x: acc_labels[x],
                        key="qr_debit_select"
                    )
                    debit_acc = acc_map[debit_account_id]

                    if debit_account_id == acc_details["id"]:
                        st.warning("⚠️ You cannot pay into the same account you are paying from.")
                    else:
                        with st.form("qr_pay_execution_form"):
                            pay_amount = st.number_input(
                                "Amount to Pay (₹)",
                                min_value=1.0,
                                max_value=1_000_000.0,
                                value=min(250.0, float(debit_acc["balance_paise"]) / 100.0) if debit_acc["balance_paise"] > 0 else 50.0,
                                step=50.0,
                                format="%.2f"
                            )
                            pay_note = st.text_input("Payment Description", placeholder="e.g. QR Instant Payment")

                            has_pin = bool(user.get("has_pin"))
                            pin_val = None
                            if has_pin:
                                pin_val = st.text_input("Transaction PIN", type="password", max_chars=6)

                            confirm_qr_pay = st.checkbox(
                                f"I confirm the payment of {format_currency(rupees_to_paise(pay_amount))} to {acc_details['holder_name']}."
                            )

                            btn_execute = st.form_submit_button("Confirm & Pay via QR", use_container_width=True)

                            if btn_execute:
                                pay_paise = rupees_to_paise(pay_amount)
                                if not confirm_qr_pay:
                                    st.error("Please confirm payment authorization.")
                                elif pay_paise > debit_acc["balance_paise"]:
                                    st.error(f"Insufficient balance in selected account ({format_currency(debit_acc['balance_paise'])} available).")
                                elif has_pin and not pin_val:
                                    st.error("Please enter your transaction PIN.")
                                else:
                                    with st.spinner("Authorizing and processing QR transaction..."):
                                        ok, msg, receipt = process_transfer(
                                            sender_user_id=user_id,
                                            sender_account_id=debit_account_id,
                                            recipient_account_number=dest_acc_num,
                                            amount_paise=pay_paise,
                                            description=f"[QR Payment] {pay_note}",
                                            transaction_pin=pin_val
                                        )

                                        if ok and receipt:
                                            st.session_state["last_qr_receipt"] = receipt
                                            st.success(f"🎉 {msg}")
                                        else:
                                            st.error(msg)

# Display QR Receipt
if "last_qr_receipt" in st.session_state and st.session_state["last_qr_receipt"]:
    st.markdown("---")
    st.markdown("### 🧾 QR Payment Receipt")
    receipt_data = st.session_state["last_qr_receipt"]

    col_rec, col_dl = st.columns([2, 1])
    with col_rec:
        render_receipt_html(receipt_data)
    with col_dl:
        st.markdown("<br><br>", unsafe_allow_html=True)
        pdf_bytes = generate_receipt_pdf(receipt_data)
        st.download_button(
            label="📥 Download PDF Receipt",
            data=pdf_bytes,
            file_name=f"BMS_QR_Receipt_{receipt_data['reference_no']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("Close Receipt", key="close_qr_rec", use_container_width=True):
            st.session_state["last_qr_receipt"] = None
            st.rerun()
