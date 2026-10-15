"""
Authentication and authorization module for Banking Management System.
Handles bcrypt hashing, user registration, login lockout, session state,
and page protection.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import bcrypt
import streamlit as st

from database import get_db_connection
from utils import (
    check_password_strength,
    generate_account_number,
    get_current_iso,
    log_audit_event,
    send_notification,
)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 10


# ============================================================================
# CRYPTOGRAPHIC HASHING HELPERS
# ============================================================================

def hash_secret(plain: str) -> str:
    """Hash a plaintext password or PIN using bcrypt with a random salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_secret(plain: str, hashed: str) -> bool:
    """Securely verify a plaintext against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ============================================================================
# REGISTRATION & USER CREATION
# ============================================================================

def register_user(
    full_name: str,
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    phone: str = "",
    initial_account_type: str = "Savings",
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate and register a new customer. Automatically creates their primary bank account.
    Returns: (success: bool, message: str, user_dict_or_none)
    """
    full_name = full_name.strip()
    username = username.strip().lower()
    email = email.strip().lower()
    phone = phone.strip()

    if not full_name or not username or not email or not password:
        return False, "All required fields must be filled.", None

    if len(username) < 3:
        return False, "Username must be at least 3 characters long.", None

    if "@" not in email or "." not in email:
        return False, "Please enter a valid email address.", None

    if password != confirm_password:
        return False, "Passwords do not match.", None

    strength = check_password_strength(password)
    if not strength["is_valid"]:
        issues = ", ".join(strength["feedback"])
        return False, f"Password does not meet security requirements: {issues}", None

    hashed_pw = hash_secret(password)
    now_iso = get_current_iso()

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Check duplicate username
            cursor.execute("SELECT id FROM users WHERE username = ?;", (username,))
            if cursor.fetchone():
                return False, "Username is already taken. Please choose another.", None

            # Check duplicate email
            cursor.execute("SELECT id FROM users WHERE email = ?;", (email,))
            if cursor.fetchone():
                return False, "Email address is already registered.", None

            # Insert new customer
            cursor.execute("""
                INSERT INTO users (
                    username, email, password_hash, full_name, phone, role,
                    is_active, failed_login_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'customer', 1, 0, ?, ?);
            """, (username, email, hashed_pw, full_name, phone, now_iso, now_iso))

            user_id = cursor.lastrowid

            # Generate unique account number and create primary account
            account_number = generate_account_number()
            cursor.execute("""
                INSERT INTO accounts (
                    user_id, account_number, account_type, balance_paise,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, 0, 1, ?, ?);
            """, (user_id, account_number, initial_account_type, now_iso, now_iso))

            # Record audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, details, created_at)
                VALUES (?, 'USER_REGISTRATION', ?, ?);
            """, (user_id, f"Customer registered: {username}. Primary account created: {account_number}", now_iso))

            # Send welcome notification
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, is_read, created_at)
                VALUES (?, 'Welcome to BMS Bank', ?, 0, ?);
            """, (user_id, f"Welcome {full_name}! Your primary {initial_account_type} account ({account_number}) is ready.", now_iso))

            new_user = {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "role": "customer",
                "primary_account": account_number
            }
            return True, "Registration successful! You may now sign in.", new_user

    except Exception as e:
        return False, f"Registration failed due to a database error: {str(e)}", None


# ============================================================================
# AUTHENTICATION & LOGIN
# ============================================================================

def authenticate_user(
    username_or_email: str,
    password: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate user credentials with rate limiting and lockout protection.
    Returns: (success: bool, message: str, user_dict_or_none)
    """
    identifier = username_or_email.strip().lower()
    if not identifier or not password:
        return False, "Please enter your username/email and password.", None

    now = datetime.now()
    now_iso = now.isoformat()

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, password_hash, pin_hash, full_name,
                       phone, role, is_active, failed_login_attempts, lockout_until, created_at
                FROM users
                WHERE username = ? OR email = ?;
            """, (identifier, identifier))
            row = cursor.fetchone()

            if not row:
                return False, "Invalid username or password.", None

            user_id = row["id"]
            is_active = bool(row["is_active"])
            failed_attempts = row["failed_login_attempts"] or 0
            lockout_until_str = row["lockout_until"]

            if not is_active:
                log_audit_event(user_id, "LOGIN_FAILED", "Account deactivated/frozen", db_path)
                return False, "Your account has been deactivated. Please contact support.", None

            # Check if user is currently locked out
            if lockout_until_str:
                lockout_until = datetime.fromisoformat(lockout_until_str)
                if now < lockout_until:
                    remaining = int((lockout_until - now).total_seconds() // 60) + 1
                    return False, f"Account temporarily locked due to multiple failed attempts. Try again in {remaining} minute(s).", None

            # Verify password
            if not verify_secret(password, row["password_hash"]):
                new_attempts = failed_attempts + 1
                if new_attempts >= MAX_FAILED_ATTEMPTS:
                    lock_time = (now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                    cursor.execute("""
                        UPDATE users
                        SET failed_login_attempts = ?, lockout_until = ?, updated_at = ?
                        WHERE id = ?;
                    """, (new_attempts, lock_time, now_iso, user_id))
                    log_audit_event(user_id, "ACCOUNT_LOCKED", f"Account locked for {LOCKOUT_DURATION_MINUTES} mins after {new_attempts} failures", db_path)
                    return False, f"Too many failed login attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes.", None
                else:
                    cursor.execute("""
                        UPDATE users
                        SET failed_login_attempts = ?, updated_at = ?
                        WHERE id = ?;
                    """, (new_attempts, now_iso, user_id))
                    attempts_left = MAX_FAILED_ATTEMPTS - new_attempts
                    log_audit_event(user_id, "LOGIN_FAILED", f"Invalid password attempt ({new_attempts}/{MAX_FAILED_ATTEMPTS})", db_path)
                    return False, f"Invalid username or password. {attempts_left} attempt(s) remaining before temporary lockout.", None

            # Successful Authentication: Reset failed attempts & clear lockout
            cursor.execute("""
                UPDATE users
                SET failed_login_attempts = 0, lockout_until = NULL, updated_at = ?
                WHERE id = ?;
            """, (now_iso, user_id))

            log_audit_event(user_id, "LOGIN_SUCCESS", f"User {row['username']} logged in successfully", db_path)

            user_data = {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "full_name": row["full_name"],
                "phone": row["phone"] or "",
                "role": row["role"],
                "has_pin": bool(row["pin_hash"]),
                "created_at": row["created_at"]
            }
            return True, "Login successful!", user_data

    except Exception as e:
        return False, f"Authentication error: {str(e)}", None


# ============================================================================
# PASSWORD & PIN UPDATES
# ============================================================================

def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Change user password with current password verification."""
    strength = check_password_strength(new_password)
    if not strength["is_valid"]:
        issues = ", ".join(strength["feedback"])
        return False, f"New password is too weak: {issues}"

    now_iso = get_current_iso()
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row or not verify_secret(current_password, row["password_hash"]):
                return False, "Current password is incorrect."

            new_hash = hash_secret(new_password)
            cursor.execute("""
                UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?;
            """, (new_hash, now_iso, user_id))

            log_audit_event(user_id, "PASSWORD_CHANGED", "User changed password successfully", db_path)
            send_notification(user_id, "Security Alert", "Your account password was updated successfully.", db_path)
            return True, "Password updated successfully!"
    except Exception as e:
        return False, f"Error updating password: {e}"


def set_transaction_pin(
    user_id: int,
    new_pin: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Set or update a 4 to 6 digit transaction PIN."""
    pin_str = str(new_pin).strip()
    if not (pin_str.isdigit() and len(pin_str) in (4, 6)):
        return False, "Transaction PIN must be a 4 or 6-digit number."

    now_iso = get_current_iso()
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            pin_hash = hash_secret(pin_str)
            cursor.execute("""
                UPDATE users SET pin_hash = ?, updated_at = ? WHERE id = ?;
            """, (pin_hash, now_iso, user_id))

            log_audit_event(user_id, "PIN_UPDATED", "Transaction PIN configured/updated", db_path)
            send_notification(user_id, "Security Alert", "Your transaction PIN was configured/updated.", db_path)
            return True, "Transaction PIN set successfully!"
    except Exception as e:
        return False, f"Error setting PIN: {e}"


def verify_user_pin(user_id: int, pin: str, db_path: Optional[Path] = None) -> bool:
    """Verify user transaction PIN."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pin_hash FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row or not row["pin_hash"]:
                return False
            return verify_secret(str(pin).strip(), row["pin_hash"])
    except Exception:
        return False


# ============================================================================
# STREAMLIT SESSION STATE MANAGEMENT
# ============================================================================

def init_session_state() -> None:
    """Ensure session state keys are initialized safely."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "selected_account_id" not in st.session_state:
        st.session_state["selected_account_id"] = None


def login_user(user_data: Dict[str, Any]) -> None:
    """Save user details into session state."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = user_data


def logout_user() -> None:
    """Clear user session state and sign out."""
    user = st.session_state.get("user")
    if user:
        log_audit_event(user.get("id"), "LOGOUT", f"User {user.get('username')} logged out")
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.session_state["selected_account_id"] = None


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieve logged in user information."""
    init_session_state()
    if st.session_state.get("authenticated") and st.session_state.get("user"):
        return st.session_state["user"]
    return None


def is_authenticated() -> bool:
    """Check if current session is authenticated."""
    init_session_state()
    return bool(st.session_state.get("authenticated") and st.session_state.get("user"))


def is_admin() -> bool:
    """Check if current logged in user has admin role."""
    user = get_current_user()
    return bool(user and user.get("role") == "admin")


def require_login(required_role: Optional[str] = None) -> Dict[str, Any]:
    """
    Enforce page protection on Streamlit pages.
    Halts execution if not logged in or if unauthorized role.
    """
    from styles import apply_custom_styles, render_sidebar_brand
    apply_custom_styles()
    render_sidebar_brand()

    user = get_current_user()

    if not user:
        st.error("🔒 **Authentication Required**")
        st.info("You must sign in to access this page. Please return to the login screen.")
        if st.button("⬅️ Go to Login Page", use_container_width=True):
            try:
                st.switch_page("app.py")
            except Exception:
                st.markdown("[Click here to return to Login](file:///app.py)")
        st.stop()

    if required_role and user.get("role") != required_role:
        st.error("🚫 **Access Denied**")
        st.warning(f"This page requires administrative privileges ({required_role}).")
        if st.button("⬅️ Return to Customer Dashboard", use_container_width=True):
            try:
                st.switch_page("pages/1_Dashboard.py")
            except Exception:
                pass
        st.stop()

    return user
