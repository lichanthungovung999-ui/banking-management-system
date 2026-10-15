"""
Transaction History page with comprehensive search, filters, sorting,
receipt inspection, and CSV export.
"""

from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from auth import require_login
from services.account_service import get_user_accounts
from services.receipt_service import generate_receipt_pdf, render_receipt_html
from services.transaction_service import get_user_transactions
from utils import format_currency, format_datetime, mask_account_number

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Audit & History</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Transaction History</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Search, filter, inspect receipts, and export complete transaction ledgers.</p>
</div>
""", unsafe_allow_html=True)

accounts = get_user_accounts(user_id)
acc_options = {None: "All Accounts"}
for a in accounts:
    acc_options[a["id"]] = f"{a['account_type']} • {a['account_number']}"

# -------------------------------------------------------------
# FILTER CONTROLS BAR
# -------------------------------------------------------------
with st.expander("🔍 Filter & Sort Transactions", expanded=True):
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
        selected_acc_filter = st.selectbox(
            "Account",
            options=list(acc_options.keys()),
            format_func=lambda x: acc_options[x]
        )

    with f_col2:
        type_options = {
            "ALL": "All Transaction Types",
            "DEPOSIT": "Deposits (Inflow)",
            "WITHDRAWAL": "Withdrawals (Outflow)",
            "TRANSFER_DEBIT": "Transfers Sent",
            "TRANSFER_CREDIT": "Transfers Received"
        }
        selected_type = st.selectbox(
            "Type",
            options=list(type_options.keys()),
            format_func=lambda x: type_options[x]
        )

    with f_col3:
        sort_options = {
            "date_desc": "Date: Newest First",
            "date_asc": "Date: Oldest First",
            "amount_desc": "Amount: High to Low",
            "amount_asc": "Amount: Low to High"
        }
        selected_sort = st.selectbox(
            "Sort Order",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x]
        )

    with f_col4:
        search_kw = st.text_input("Search Reference / Note", placeholder="e.g. TXN- or Salary...").strip()

    # Date range filters
    d_col1, d_col2 = st.columns(2)
    today = datetime.now().date()
    with d_col1:
        filter_start = st.date_input("Start Date", value=today - timedelta(days=90))
    with d_col2:
        filter_end = st.date_input("End Date", value=today)

# -------------------------------------------------------------
# QUERY DATABASE
# -------------------------------------------------------------
transactions = get_user_transactions(
    user_id=user_id,
    account_id=selected_acc_filter,
    txn_type=selected_type,
    start_date=filter_start.isoformat() if filter_start else None,
    end_date=filter_end.isoformat() if filter_end else None,
    search_query=search_kw,
    sort_by=selected_sort
)

st.markdown(f"### 📑 Records Found ({len(transactions)})")

if not transactions:
    st.info("No transactions found matching your selected filter criteria.")
else:
    # Prepare DataFrame for table and CSV export
    export_rows = []
    display_rows = []

    for t in transactions:
        is_credit = t["transaction_type"] in ("DEPOSIT", "TRANSFER_CREDIT")
        amt_sign = "+" if is_credit else "-"
        amt_formatted = f"{amt_sign}{format_currency(t['amount_paise'])}"

        # For visual display table
        display_rows.append({
            "Reference ID": t["transaction_ref"],
            "Timestamp": format_datetime(t["created_at"]),
            "Account": mask_account_number(t["account_number"]),
            "Type": t["transaction_type"],
            "Amount": amt_formatted,
            "Balance After": format_currency(t["balance_after_paise"]),
            "Description": t["description"] or "",
            "Status": t["status"]
        })

        # For CSV export (raw values)
        export_rows.append({
            "Transaction_Reference": t["transaction_ref"],
            "Timestamp": t["created_at"],
            "Account_Number": t["account_number"],
            "Account_Type": t["account_type"],
            "Transaction_Type": t["transaction_type"],
            "Amount_Rupees": float(t["amount_paise"]) / 100.0,
            "Balance_After_Rupees": float(t["balance_after_paise"]) / 100.0,
            "Description": t["description"],
            "Status": t["status"]
        })

    df_display = pd.DataFrame(display_rows)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # CSV EXPORT
    # ---------------------------------------------------------
    df_export = pd.DataFrame(export_rows)
    csv_bytes = df_export.to_csv(index=False).encode("utf-8")

    exp_col1, exp_col2 = st.columns([1, 2])
    with exp_col1:
        st.download_button(
            label="📊 Export Ledger to CSV",
            data=csv_bytes,
            file_name=f"BMS_Statement_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # ---------------------------------------------------------
    # RECEIPT VIEWER MODAL / SECTION
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🔍 Inspect Transaction Receipt")

    ref_map = {t["transaction_ref"]: t for t in transactions}
    inspected_ref = st.selectbox(
        "Choose Transaction Reference to View Official Receipt",
        options=list(ref_map.keys())
    )

    if inspected_ref:
        selected_txn = ref_map[inspected_ref]
        receipt_dict = {
            "transaction_id": selected_txn["id"],
            "reference_no": selected_txn["transaction_ref"],
            "type": selected_txn["transaction_type"],
            "account_number": selected_txn["account_number"],
            "amount_formatted": format_currency(selected_txn["amount_paise"]),
            "balance_after_formatted": format_currency(selected_txn["balance_after_paise"]),
            "description": selected_txn["description"],
            "status": selected_txn["status"],
            "timestamp": selected_txn["created_at"]
        }

        col_r_view, col_r_btn = st.columns([2, 1])
        with col_r_view:
            render_receipt_html(receipt_dict)
        with col_r_btn:
            st.markdown("<br><br>", unsafe_allow_html=True)
            pdf_data = generate_receipt_pdf(receipt_dict)
            st.download_button(
                label="📥 Download PDF Receipt",
                data=pdf_data,
                file_name=f"BMS_Receipt_{selected_txn['transaction_ref']}.pdf",
                mime="application/pdf",
                key="btn_dl_history_receipt",
                use_container_width=True
            )
