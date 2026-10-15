"""
Main Banking Dashboard displaying customer overview, balances, Plotly charts,
recent transactions, and alerts.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import require_login
from services.transaction_service import get_dashboard_summary
from styles import render_metric_card
from utils import format_currency, format_datetime, mask_account_number, paise_to_rupees

# Enforce Authentication
user = require_login()
user_id = user["id"]

# Fetch Real-time Dashboard Analytics from SQLite
summary = get_dashboard_summary(user_id)

# -------------------------------------------------------------
# TOP HEADER & WELCOME
# -------------------------------------------------------------
st.markdown(f"""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Financial Overview</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Welcome back, {user['full_name']}!</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Here is a comprehensive summary of your accounts and recent transactions.</p>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP METRIC CARDS
# -------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    tot_bal_str = format_currency(summary["total_balance_paise"])
    render_metric_card("Total Net Balance", tot_bal_str, "Across all active accounts", delta_type="info")

with col2:
    act_acc_count = summary["active_accounts_count"]
    render_metric_card("Active Accounts", str(act_acc_count), "Available for transactions", delta_type="positive")

with col3:
    tot_dep_str = format_currency(summary["total_deposit_paise"])
    render_metric_card("Total Inflow / Deposits", tot_dep_str, "Deposits & transfers received", delta_type="positive")

with col4:
    tot_wth_str = format_currency(summary["total_withdraw_paise"])
    render_metric_card("Total Outflow", tot_wth_str, "Withdrawals & transfers sent", delta_type="negative")

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# QUICK ACTION BUTTONS
# -------------------------------------------------------------
st.markdown("### ⚡ Quick Banking Actions")
qcol1, qcol2, qcol3, qcol4, qcol5 = st.columns(5)

with qcol1:
    if st.button("💰 Deposit Funds", use_container_width=True):
        st.switch_page("pages/3_Deposit.py")

with qcol2:
    if st.button("💸 Withdraw Funds", use_container_width=True):
        st.switch_page("pages/4_Withdraw.py")

with qcol3:
    if st.button("🔁 Transfer Money", use_container_width=True):
        st.switch_page("pages/5_Transfer.py")

with qcol4:
    if st.button("🏦 My Accounts", use_container_width=True):
        st.switch_page("pages/2_My_Accounts.py")

with qcol5:
    if st.button("📱 QR Payments", use_container_width=True):
        st.switch_page("pages/6_QR_Payments.py")

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# INTERACTIVE PLOTLY CHARTS
# -------------------------------------------------------------
chart_col1, chart_col2 = st.columns(2)

monthly_data = summary["monthly_breakdown"]

with chart_col1:
    st.markdown("### 📊 Inflow vs Outflow Trend")
    if monthly_data:
        df_monthly = pd.DataFrame(monthly_data)
        df_monthly["amount_rupees"] = df_monthly["total_paise"].apply(paise_to_rupees)

        # Categorize into Inflow (DEPOSIT, TRANSFER_CREDIT) and Outflow (WITHDRAWAL, TRANSFER_DEBIT)
        def categorize(txn_t):
            if txn_t in ("DEPOSIT", "TRANSFER_CREDIT"):
                return "Inflow (Deposits / Received)"
            return "Outflow (Withdrawals / Sent)"

        df_monthly["Category"] = df_monthly["transaction_type"].apply(categorize)
        df_grouped = df_monthly.groupby(["month", "Category"])["amount_rupees"].sum().reset_index()

        fig_bar = px.bar(
            df_grouped,
            x="month",
            y="amount_rupees",
            color="Category",
            barmode="group",
            labels={"month": "Month", "amount_rupees": "Amount (₹)"},
            color_discrete_map={
                "Inflow (Deposits / Received)": "#10b981",
                "Outflow (Withdrawals / Sent)": "#ef4444"
            }
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="#e2e8f0"),
            xaxis=dict(gridcolor="#e2e8f0")
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No transaction history recorded yet. Make a deposit to see your monthly financial trends!")

with chart_col2:
    st.markdown("### 📈 Transaction Activity Breakdown")
    if monthly_data:
        df_pie = pd.DataFrame(monthly_data)
        df_pie["amount_rupees"] = df_pie["total_paise"].apply(paise_to_rupees)
        type_sums = df_pie.groupby("transaction_type")["amount_rupees"].sum().reset_index()

        fig_pie = px.pie(
            type_sums,
            names="transaction_type",
            values="amount_rupees",
            hole=0.45,
            color_discrete_sequence=["#2563eb", "#10b981", "#f59e0b", "#8b5cf6"]
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No transaction volume to display. Start transacting to visualize category distributions.")

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# RECENT TRANSACTIONS TABLE & NOTIFICATIONS
# -------------------------------------------------------------
bottom_col1, bottom_col2 = st.columns([2, 1])

with bottom_col1:
    st.markdown("### 🕒 Recent Transactions")
    recent_txns = summary["recent_transactions"]

    if recent_txns:
        table_rows = []
        for t in recent_txns:
            # Color code based on transaction direction
            is_credit = t["transaction_type"] in ("DEPOSIT", "TRANSFER_CREDIT")
            amount_display = f"{'+' if is_credit else '-'}{format_currency(t['amount_paise'])}"

            table_rows.append({
                "Date & Time": format_datetime(t["created_at"]),
                "Reference": t["transaction_ref"],
                "Account": mask_account_number(t["account_number"]),
                "Type": t["transaction_type"],
                "Amount": amount_display,
                "Status": t["status"]
            })

        df_display = pd.DataFrame(table_rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        if st.button("View Full Transaction Ledger ➡️", key="btn_view_full_txns"):
            st.switch_page("pages/8_Transaction_History.py")
    else:
        st.info("No transactions logged yet. Use the Quick Banking Actions above to deposit or transfer funds.")

with bottom_col2:
    st.markdown("### 🔔 Recent Notifications")
    notifications = summary["notifications"]

    if notifications:
        for n in notifications:
            st.markdown(f"""
            <div style="background: white; border-radius: 10px; padding: 0.9rem; border: 1px solid #e2e8f0; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a;">{n['title']}</div>
                    <div style="font-size: 0.72rem; color: #94a3b8;">{format_datetime(n['created_at'])}</div>
                </div>
                <div style="font-size: 0.82rem; color: #475569; margin-top: 0.3rem;">{n['message']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No new notifications at this time.")
