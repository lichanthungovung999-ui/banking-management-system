"""
Banking Management System (BMS)
Main Application Entry Point & Authentication Hub
"""

from datetime import datetime
import streamlit as st

from auth import (
    authenticate_user,
    get_current_user,
    init_session_state,
    is_authenticated,
    login_user,
    logout_user,
    register_user,
)
from database import init_database
from styles import apply_custom_styles, render_sidebar_brand
from utils import check_password_strength

# Page Configuration
st.set_page_config(
    page_title="Banking Management System | BMS Bank",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database and Session State
init_database()
init_session_state()
apply_custom_styles()
render_sidebar_brand()


def render_authenticated_home(user: dict):
    """Render landing screen for already authenticated users."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 2rem; border-radius: 16px; color: white; margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <span class="bms-badge bms-badge-info" style="margin-bottom: 0.5rem;">SECURE SESSION ACTIVE</span>
                <h1 style="color: white; margin: 0.2rem 0; font-size: 2rem;">Welcome back, {name}!</h1>
                <p style="color: #94a3b8; margin: 0; font-size: 0.95rem;">Signed in as <strong>@{username}</strong> ({role})</p>
            </div>
            <div style="display: flex; gap: 0.75rem;">
                <span style="background: rgba(255, 255, 255, 0.1); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; border: 1px solid rgba(255, 255, 255, 0.15);">
                    🏛️ BMS Core v1.0
                </span>
            </div>
        </div>
    </div>
    """.format(
        name=user.get("full_name", "Valued Customer"),
        username=user.get("username", "user"),
        role=user.get("role", "customer").upper()
    ), unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🚀 Quick Access")
        st.info("Your authenticated session is active. Choose a destination below or use the sidebar navigation.")

        qcol1, qcol2, qcol3 = st.columns(3)
        with qcol1:
            if st.button("📊 Open Dashboard", use_container_width=True):
                st.switch_page("pages/1_Dashboard.py")
        with qcol2:
            if st.button("💳 My Accounts", use_container_width=True):
                st.switch_page("pages/2_My_Accounts.py")
        with qcol3:
            if st.button("🔁 Transfer Money", use_container_width=True):
                st.switch_page("pages/5_Transfer.py")

        st.markdown("<br>", unsafe_allow_html=True)
        qcol4, qcol5, qcol6 = st.columns(3)
        with qcol4:
            if st.button("💰 Deposit Funds", use_container_width=True):
                st.switch_page("pages/3_Deposit.py")
        with qcol5:
            if st.button("💸 Withdraw Funds", use_container_width=True):
                st.switch_page("pages/4_Withdraw.py")
        with qcol6:
            if st.button("📱 QR Payments", use_container_width=True):
                st.switch_page("pages/6_QR_Payments.py")

    with col2:
        st.markdown("### 👤 Session Controls")
        st.markdown(f"""
        <div class="bms-card">
            <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.25rem;">Logged-in User</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">{user.get('full_name')}</div>
            <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.2rem;">{user.get('email')}</div>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 1rem 0;">
            <div style="font-size: 0.8rem; color: #10b981; font-weight: 600;">🔒 End-to-End Encrypted Session</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout from Banking Platform", use_container_width=True, type="secondary"):
            logout_user()
            st.success("You have been signed out.")
            st.rerun()


def render_login_and_registration():
    """Render the polished login and registration interface."""
    # Hero Branding Banner
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem; padding: 1.5rem 0;">
        <div style="display: inline-flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); width: 64px; height: 64px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.4); margin-bottom: 1rem;">
            <span style="font-size: 32px;">🏛️</span>
        </div>
        <h1 style="font-size: 2.25rem; font-weight: 800; color: #0f172a; margin-bottom: 0.25rem; letter-spacing: -0.02em;">Banking Management System</h1>
        <p style="font-size: 1.05rem; color: #64748b; font-weight: 500;">Secure Banking. Simple Transactions.</p>
    </div>
    """, unsafe_allow_html=True)

    # Centered container using columns
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        tab_login, tab_register, tab_about = st.tabs(["🔐 Sign In", "📝 Create Account", "ℹ️ System Info"])

        # ---------------------------------------------------------
        # LOGIN TAB
        # ---------------------------------------------------------
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                st.markdown("#### Access Your Account")
                username_or_email = st.text_input(
                    "Username or Email",
                    placeholder="e.g. rajesh or rajesh@example.com",
                    help="Enter your registered username or email address"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your account password",
                    help="Case-sensitive password"
                )

                remember_me = st.checkbox("Keep me signed in for this browser session", value=True)
                submit_login = st.form_submit_button("Sign In to BMS Bank", use_container_width=True)

                if submit_login:
                    if not username_or_email or not password:
                        st.error("Please enter both username/email and password.")
                    else:
                        with st.spinner("Authenticating with secure database..."):
                            success, message, user_data = authenticate_user(username_or_email, password)
                            if success and user_data:
                                login_user(user_data)
                                st.success("Authentication successful! Redirecting to dashboard...")
                                st.rerun()
                            else:
                                st.error(message)

            # Quick credentials hint for demo testers
            with st.expander("🔑 Demo Credentials & Instructions"):
                st.markdown("""
                - **Default Administrator**:
                  - Username: `admin`
                  - Password: `Admin@BMS2026`
                - **New Customer**:
                  - Click the **Create Account** tab above to register a new user in 5 seconds.
                  - A 12-digit bank account number will be created automatically.
                """)

        # ---------------------------------------------------------
        # REGISTRATION TAB
        # ---------------------------------------------------------
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=False):
                st.markdown("#### Open a New Bank Account")
                st.write("Fill in your personal details to create a secure online banking account.")

                reg_full_name = st.text_input("Full Name", placeholder="e.g. Rajesh Sharma")
                col_u, col_e = st.columns(2)
                with col_u:
                    reg_username = st.text_input("Username", placeholder="e.g. rajesh").strip().lower()
                with col_e:
                    reg_email = st.text_input("Email Address", placeholder="rajesh@example.com").strip().lower()

                reg_phone = st.text_input("Phone Number (Optional)", placeholder="+91-9876543210")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    reg_password = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Choose a strong password",
                        help="Must be at least 8 characters with uppercase, lowercase, numbers, and symbols."
                    )
                with col_p2:
                    reg_confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat password")

                reg_acc_type = st.selectbox("Primary Account Type", ["Savings", "Current"])

                # Real-time visual feedback for password strength if entered
                if reg_password:
                    eval_pw = check_password_strength(reg_password)
                    st.progress(eval_pw["progress"] / 100.0)
                    st.caption(f"Password Strength: **{eval_pw['label']}** ({eval_pw['score']}/5)")
                    if eval_pw["feedback"]:
                        st.caption("Suggestions: " + ", ".join(eval_pw["feedback"]))

                submit_register = st.form_submit_button("Register & Generate Account", use_container_width=True)

                if submit_register:
                    if not reg_full_name or not reg_username or not reg_email or not reg_password:
                        st.error("Please fill in all mandatory fields.")
                    elif reg_password != reg_confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        with st.spinner("Creating secure account and hashing credentials with bcrypt..."):
                            success, msg, new_user = register_user(
                                full_name=reg_full_name,
                                username=reg_username,
                                email=reg_email,
                                password=reg_password,
                                confirm_password=reg_confirm_password,
                                phone=reg_phone,
                                initial_account_type=reg_acc_type
                            )
                            if success and new_user:
                                st.success(f"🎉 {msg}")
                                st.info(f"Your unique 12-digit account number is: **{new_user['primary_account']}**. Please switch to the Sign In tab to log in.")
                            else:
                                st.error(msg)

        # ---------------------------------------------------------
        # ABOUT TAB
        # ---------------------------------------------------------
        with tab_about:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="bms-card">
                <h4 style="margin-top: 0; color: #0f172a;">About Banking Management System</h4>
                <p style="color: #64748b; font-size: 0.95rem;">
                    BMS Bank is a full-featured educational banking simulation engineered with Python, Streamlit, and SQLite.
                </p>
                <div style="margin-top: 1rem;">
                    <strong>Security Architecture:</strong>
                    <ul style="color: #475569; font-size: 0.9rem; margin-top: 0.5rem;">
                        <li>Cryptographic password & PIN hashing via <code>bcrypt</code></li>
                        <li>Brute-force lockout protection (5 failed attempts locks for 10 minutes)</li>
                        <li>Strict integer paise storage for zero-floating-point financial accuracy</li>
                        <li>ACID-compliant SQLite transactions with automatic rollback</li>
                        <li>Complete separation of customer accounts and audit logging</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)


# Main router
current_user = get_current_user()

if is_authenticated() and current_user:
    render_authenticated_home(current_user)
else:
    render_login_and_registration()
