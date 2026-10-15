"""
Profile & Settings page for account details, password updates,
transaction PIN configuration, security audit info, and logout.
"""

import streamlit as st

from auth import (
    change_password,
    get_current_user,
    logout_user,
    require_login,
    set_transaction_pin,
)
from database import get_db_connection
from utils import check_password_strength, format_datetime, get_current_iso, log_audit_event

# Enforce Authentication
user = require_login()
user_id = user["id"]

st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <div style="font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Customer Security</div>
    <h1 style="color: #0f172a; margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em;">Profile & Security Settings</h1>
    <p style="color: #64748b; margin-top: 0.25rem;">Manage your credentials, transaction PIN, and personal details.</p>
</div>
""", unsafe_allow_html=True)

tab_profile, tab_security, tab_pin, tab_privacy = st.tabs([
    "👤 Personal Profile",
    "🔑 Change Password",
    "🔢 Transaction PIN",
    "🛡️ Privacy & Session"
])

# -------------------------------------------------------------
# TAB 1: PERSONAL PROFILE
# -------------------------------------------------------------
with tab_profile:
    st.markdown("<br>", unsafe_allow_html=True)
    col_p1, col_p2 = st.columns([2, 1])

    with col_p1:
        st.markdown("### Profile Information")

        with st.form("update_profile_form"):
            new_full_name = st.text_input("Full Name", value=user.get("full_name", ""))
            st.text_input("Username (Read-Only)", value=user.get("username", ""), disabled=True)
            st.text_input("Email Address (Read-Only)", value=user.get("email", ""), disabled=True)
            new_phone = st.text_input("Phone Number", value=user.get("phone", ""))

            submit_profile = st.form_submit_button("Save Profile Changes", use_container_width=True)

            if submit_profile:
                if not new_full_name.strip():
                    st.error("Full name cannot be empty.")
                else:
                    try:
                        with get_db_connection() as conn:
                            conn.execute("""
                                UPDATE users
                                SET full_name = ?, phone = ?, updated_at = ?
                                WHERE id = ?;
                            """, (new_full_name.strip(), new_phone.strip(), get_current_iso(), user_id))

                        # Update session user
                        st.session_state["user"]["full_name"] = new_full_name.strip()
                        st.session_state["user"]["phone"] = new_phone.strip()
                        log_audit_event(user_id, "PROFILE_UPDATED", "Customer updated personal profile details")
                        st.success("Profile updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update profile: {e}")

    with col_p2:
        st.markdown("### Account Badge")
        st.markdown(f"""
        <div class="bms-card" style="text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">👤</div>
            <div style="font-size: 1.2rem; font-weight: 800; color: #0f172a;">{user.get('full_name')}</div>
            <div style="font-size: 0.85rem; color: #64748b;">@{user.get('username')}</div>
            <div style="margin-top: 0.75rem;">
                <span class="bms-badge bms-badge-info">{user.get('role').upper()}</span>
            </div>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 1rem 0;">
            <div style="font-size: 0.8rem; color: #94a3b8;">Customer since {format_datetime(user.get('created_at'))}</div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 2: CHANGE PASSWORD
# -------------------------------------------------------------
with tab_security:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Update Account Password")
    st.write("Ensure your password is at least 8 characters long and contains letters, numbers, and special symbols.")

    with st.form("change_password_form", clear_on_submit=True):
        curr_pw = st.text_input("Current Password", type="password")
        new_pw = st.text_input("New Password", type="password")
        confirm_new_pw = st.text_input("Confirm New Password", type="password")

        if new_pw:
            eval_new = check_password_strength(new_pw)
            st.progress(eval_new["progress"] / 100.0)
            st.caption(f"Password Strength: **{eval_new['label']}**")
            if eval_new["feedback"]:
                st.caption("Suggestions: " + ", ".join(eval_new["feedback"]))

        submit_pw = st.form_submit_button("Update Password", use_container_width=True)

        if submit_pw:
            if not curr_pw or not new_pw or not confirm_new_pw:
                st.error("Please fill in all password fields.")
            elif new_pw != confirm_new_pw:
                st.error("New passwords do not match.")
            else:
                with st.spinner("Verifying current password and hashing with bcrypt..."):
                    pw_ok, pw_msg = change_password(user_id, curr_pw, new_pw)
                    if pw_ok:
                        st.success(f"🎉 {pw_msg}")
                    else:
                        st.error(pw_msg)

# -------------------------------------------------------------
# TAB 3: TRANSACTION PIN
# -------------------------------------------------------------
with tab_pin:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Transaction Security PIN")
    st.write("Set up or update a 4 or 6-digit numeric PIN used to authorize high-value transfers.")

    has_pin = bool(user.get("has_pin"))
    if has_pin:
        st.success("🔒 Transaction PIN is currently configured and active on your account.")
    else:
        st.warning("⚠️ No Transaction PIN configured. Setting a PIN adds an extra layer of protection against unauthorized transfers.")

    with st.form("set_pin_form", clear_on_submit=True):
        new_pin_val = st.text_input("New Transaction PIN (4 or 6 Digits)", type="password", max_chars=6)
        confirm_pin_val = st.text_input("Confirm Transaction PIN", type="password", max_chars=6)

        submit_pin = st.form_submit_button("Save Transaction PIN", use_container_width=True)

        if submit_pin:
            if not new_pin_val:
                st.error("Please enter a PIN.")
            elif new_pin_val != confirm_pin_val:
                st.error("PIN confirmation does not match.")
            else:
                pin_ok, pin_msg = set_transaction_pin(user_id, new_pin_val)
                if pin_ok:
                    st.session_state["user"]["has_pin"] = True
                    st.success(f"🎉 {pin_msg}")
                    st.rerun()
                else:
                    st.error(pin_msg)

# -------------------------------------------------------------
# TAB 4: PRIVACY & LOGOUT
# -------------------------------------------------------------
with tab_privacy:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🛡️ Privacy & Active Session")
    st.markdown("""
    <div class="bms-card">
        <h4 style="margin-top: 0; color: #0f172a;">Data Security Commitment</h4>
        <p style="color: #64748b; font-size: 0.95rem;">
            Your credentials and sensitive transaction data are protected by industry-standard cryptography:
        </p>
        <ul style="color: #475569; font-size: 0.9rem;">
            <li>Passwords and PINs are salted and hashed using <strong>bcrypt</strong> with work-factor 12.</li>
            <li>Plaintext passwords and PINs are never persisted in the database or exposed in logs.</li>
            <li>All financial amounts are tracked in integer paise to avoid rounding discrepancies.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🚪 End Banking Session")
    st.write("Signing out clears all active credentials from your browser session.")

    if st.button("Logout from BMS Bank", use_container_width=True, type="secondary"):
        logout_user()
        st.success("Successfully logged out. Redirecting...")
        st.switch_page("app.py")
