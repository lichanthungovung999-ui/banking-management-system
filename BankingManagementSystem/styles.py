"""
Custom CSS styles and UI component templates for Banking Management System.
Provides a modern, premium digital banking experience.
"""

import streamlit as st


def apply_custom_styles() -> None:
    """
    Inject custom CSS into the Streamlit app.
    Ensures modern styling for cards, metrics, navigation, and badges
    while preserving complete compatibility with Streamlit inputs and widgets.
    """
    css = """
    <style>
    /* -------------------------------------------------------------
       GLOBAL RESET & TYPOGRAPHY
       ------------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Background and workspace */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    /* -------------------------------------------------------------
       SIDEBAR STYLING (Dark Navy Theme)
       ------------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090e17 0%, #0f172a 100%) !important;
        border-right: 1px solid #1e293b;
    }

    section[data-testid="stSidebar"] * {
        color: #cbd5e1;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
    }

    section[data-testid="stSidebar"] a {
        color: #94a3b8 !important;
    }

    section[data-testid="stSidebar"] a:hover {
        color: #60a5fa !important;
    }

    /* Sidebar navigation links */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
        border-radius: 8px;
        margin: 2px 8px;
        transition: all 0.2s ease;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(59, 130, 246, 0.15) !important;
    }

    section[data-testid="stSidebar"] [aria-current="page"] {
        background: linear-gradient(90deg, rgba(37, 99, 235, 0.3) 0%, rgba(37, 99, 235, 0.1) 100%) !important;
        border-left: 3px solid #3b82f6;
        color: #ffffff !important;
        font-weight: 600;
    }

    /* -------------------------------------------------------------
       PRIMARY & SECONDARY BUTTONS
       ------------------------------------------------------------- */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #ffffff;
        font-weight: 600;
        padding: 0.55rem 1.4rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        transition: all 0.2s ease-in-out;
        letter-spacing: 0.01em;
    }

    div.stButton > button:first-child:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
        transform: translateY(-1px);
        color: #ffffff;
    }

    div.stButton > button:first-child:active {
        transform: translateY(1px);
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2);
    }

    /* Secondary / outline buttons */
    div.stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }

    div.stButton > button[kind="secondary"]:hover {
        background: #f1f5f9 !important;
        border-color: #94a3b8 !important;
    }

    /* -------------------------------------------------------------
       CARDS & CONTAINERS
       ------------------------------------------------------------- */
    .bms-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -2px rgba(0, 0, 0, 0.03);
        margin-bottom: 1.25rem;
        transition: box-shadow 0.2s ease;
    }

    .bms-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
    }

    .bms-metric-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .bms-metric-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }

    .bms-metric-value {
        color: #0f172a;
        font-size: 1.75rem;
        font-weight: 800;
        line-height: 1.2;
    }

    .bms-metric-subtitle {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 0.4rem;
    }

    /* -------------------------------------------------------------
       BADGES & STATUS PILLS
       ------------------------------------------------------------- */
    .bms-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }

    .bms-badge-success {
        background-color: #dcfce7;
        color: #15803d;
        border: 1px solid #bbf7d0;
    }

    .bms-badge-danger {
        background-color: #fee2e2;
        color: #b91c1c;
        border: 1px solid #fecaca;
    }

    .bms-badge-info {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
    }

    .bms-badge-warning {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }

    /* -------------------------------------------------------------
       BANK DEBIT / CREDIT CARD SIMULATION
       ------------------------------------------------------------- */
    .bms-bank-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%);
        color: #ffffff;
        border-radius: 20px;
        padding: 1.75rem;
        box-shadow: 0 15px 30px -5px rgba(30, 58, 138, 0.4);
        position: relative;
        overflow: hidden;
        min-height: 210px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 1.25rem;
    }

    .bms-bank-card::after {
        content: "";
        position: absolute;
        top: -60px;
        right: -60px;
        width: 180px;
        height: 180px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.08);
        pointer-events: none;
    }

    .bms-card-chip {
        width: 44px;
        height: 32px;
        background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
        border-radius: 6px;
        display: inline-block;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.3);
    }

    .bms-card-balance-label {
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #93c5fd;
    }

    .bms-card-balance {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
    }

    .bms-card-number {
        font-family: 'Courier New', Courier, monospace;
        font-size: 1.2rem;
        letter-spacing: 0.22em;
        color: #f1f5f9;
        margin: 1rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }

    .bms-card-footer {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }

    .bms-card-holder {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #f8fafc;
    }

    .bms-card-type {
        font-size: 0.85rem;
        font-weight: 700;
        color: #93c5fd;
        text-transform: uppercase;
    }

    /* -------------------------------------------------------------
       RECEIPT DISPLAY STYLING
       ------------------------------------------------------------- */
    .bms-receipt-box {
        background: #ffffff;
        border: 2px dashed #cbd5e1;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);
        max-width: 580px;
        margin: 1rem auto;
    }

    .bms-receipt-header {
        text-align: center;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 1.25rem;
        margin-bottom: 1.25rem;
    }

    .bms-receipt-row {
        display: flex;
        justify-content: space-between;
        padding: 0.45rem 0;
        font-size: 0.92rem;
        border-bottom: 1px dashed #f1f5f9;
    }

    .bms-receipt-label {
        color: #64748b;
        font-weight: 500;
    }

    .bms-receipt-value {
        color: #0f172a;
        font-weight: 700;
        text-align: right;
    }

    /* -------------------------------------------------------------
       FORM INPUTS & STREAMLIT ENHANCEMENTS
       ------------------------------------------------------------- */
    div[data-testid="stForm"] {
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.5rem;
        background-color: #ffffff;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
    }

    .stTextInput input, .stNumberInput input, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
    }

    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }

    /* Streamlit tabs styling */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.25rem !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #2563eb !important;
        border-bottom-color: #2563eb !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    """Render application branding in the Streamlit sidebar."""
    brand_html = """
    <div style="padding: 1rem 0.5rem 1.5rem 0.5rem; border-bottom: 1px solid #1e293b; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.4);">
                <span style="font-size: 22px; color: white;">🏛️</span>
            </div>
            <div>
                <div style="font-size: 1.1rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em; line-height: 1.2;">BMS Core</div>
                <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 500; letter-spacing: 0.02em;">Secure Banking Platform</div>
            </div>
        </div>
    </div>
    """
    st.sidebar.markdown(brand_html, unsafe_allow_html=True)


def render_metric_card(title: str, value: str, subtitle: str = "", delta_type: str = "neutral") -> None:
    """Render a clean financial KPI metric card."""
    accent_bar = {
        "positive": "#10b981",
        "negative": "#ef4444",
        "info": "#3b82f6",
        "neutral": "#e2e8f0"
    }.get(delta_type, "#e2e8f0")

    card_html = f"""
    <div class="bms-metric-card" style="border-top: 4px solid {accent_bar};">
        <div class="bms-metric-title">{title}</div>
        <div class="bms-metric-value">{value}</div>
        <div class="bms-metric-subtitle">{subtitle}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_bank_card_widget(
    account_number: str,
    account_type: str,
    balance_str: str,
    holder_name: str,
    is_active: bool = True
) -> None:
    """Render an ultra-realistic, sleek debit card component."""
    from utils import mask_account_number
    masked_acc = mask_account_number(account_number)
    status_pill = '<span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #6ee7b7; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 700;">ACTIVE</span>' if is_active else '<span style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #fca5a5; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; font-weight: 700;">FROZEN</span>'

    card_html = f"""
    <div class="bms-bank-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.25rem;">🏛️</span>
                <span style="font-weight: 800; font-size: 1rem; letter-spacing: 0.05em;">BMS BANK</span>
            </div>
            <div>{status_pill}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; margin-top: 0.75rem;">
            <div class="bms-card-chip"></div>
            <span style="font-size: 1.2rem; opacity: 0.8;">📶</span>
        </div>
        <div class="bms-card-number">{masked_acc}</div>
        <div class="bms-card-footer">
            <div>
                <div class="bms-card-balance-label">Available Balance</div>
                <div class="bms-card-balance">{balance_str}</div>
                <div class="bms-card-holder" style="margin-top: 4px;">{holder_name}</div>
            </div>
            <div style="text-align: right;">
                <div class="bms-card-type">{account_type}</div>
                <div style="font-size: 0.75rem; color: #93c5fd; letter-spacing: 0.05em;">DEBIT CARD</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
