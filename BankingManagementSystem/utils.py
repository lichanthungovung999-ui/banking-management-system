"""
Utility functions for currency formatting, identifier generation, date formatting,
audit logging, notification dispatch, and password strength checks.
"""

import json
import random
import re
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from database import get_db_connection


# ============================================================================
# CURRENCY & NUMBER FORMATTING
# ============================================================================

def paise_to_rupees(paise: int) -> float:
    """Convert integer paise to floating rupees."""
    return float(paise) / 100.0


def rupees_to_paise(rupees: float | int) -> int:
    """Safely convert rupees to integer paise without floating point drift."""
    return int(round(float(rupees) * 100))


def format_currency(paise: int, symbol: str = "₹") -> str:
    """
    Format paise into Indian numbering system currency string.
    Example: 12345678 paise -> ₹1,23,456.78
    """
    is_negative = paise < 0
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    fraction = abs_paise % 100

    s = str(rupees)
    if len(s) <= 3:
        formatted_rupees = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_rupees = ",".join(groups) + "," + last3

    formatted_str = f"{symbol}{formatted_rupees}.{fraction:02d}"
    return f"-{formatted_str}" if is_negative else formatted_str


# ============================================================================
# IDENTIFIER GENERATION
# ============================================================================

def generate_account_number(prefix: str = "1001") -> str:
    """
    Generate a 12-digit unique account number starting with bank prefix.
    """
    random_digits = "".join(random.choices(string.digits, k=8))
    return f"{prefix}{random_digits}"


def generate_transaction_ref(prefix: str = "TXN") -> str:
    """
    Generate unique transaction reference string.
    Example: TXN-20261015-894231
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    rand_chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{timestamp}-{rand_chars}"


def generate_transfer_ref() -> str:
    """Generate unique transfer reference string."""
    return generate_transaction_ref(prefix="TRF")


def mask_account_number(account_number: str) -> str:
    """
    Mask an account number for secure display.
    Example: 100148291034 -> •••• •••• 1034
    """
    cleaned = str(account_number).strip()
    if len(cleaned) < 4:
        return cleaned
    last4 = cleaned[-4:]
    return f"•••• •••• {last4}"


# ============================================================================
# DATE & TIME FORMATTING
# ============================================================================

def format_datetime(iso_str: Optional[str]) -> str:
    """
    Convert an ISO format timestamp into a human-readable display string.
    Example: 2026-10-15T15:30:00 -> 15 Oct 2026, 03:30 PM
    """
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso_str


def get_current_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().isoformat()


# ============================================================================
# PASSWORD STRENGTH VALIDATION
# ============================================================================

def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Evaluate password strength against security criteria.
    Returns score (0-4), label, color, and actionable feedback items.
    """
    feedback: List[str] = []
    score = 0

    if len(password) >= 8:
        score += 1
    else:
        feedback.append("At least 8 characters required")

    if re.search(r"[A-Z]", password):
        score += 1
    else:
        feedback.append("At least one uppercase letter (A-Z)")

    if re.search(r"[a-z]", password):
        score += 1
    else:
        feedback.append("At least one lowercase letter (a-z)")

    if re.search(r"[0-9]", password):
        score += 1
    else:
        feedback.append("At least one number (0-9)")

    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
    else:
        feedback.append("At least one special symbol (!@#$%^&*)")

    strength_map = {
        0: ("Very Weak", "#ef4444", 10),
        1: ("Weak", "#f97316", 25),
        2: ("Moderate", "#eab308", 50),
        3: ("Good", "#3b82f6", 75),
        4: ("Strong", "#10b981", 90),
        5: ("Very Strong", "#059669", 100),
    }

    label, color, progress = strength_map.get(score, ("Weak", "#ef4444", 20))
    is_valid = score >= 3 and len(password) >= 8

    return {
        "score": score,
        "label": label,
        "color": color,
        "progress": progress,
        "feedback": feedback,
        "is_valid": is_valid
    }


# ============================================================================
# AUDIT LOGGING & NOTIFICATIONS
# ============================================================================

def log_audit_event(
    user_id: Optional[int],
    action: str,
    details: str,
    db_path: Optional[Path] = None,
    ip_address: str = "127.0.0.1"
) -> None:
    """
    Log an event to the audit_logs table.
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                INSERT INTO audit_logs (user_id, action, details, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, details, ip_address, get_current_iso()))
    except Exception as e:
        # Avoid crashing primary operations if audit logging encounters a transient error
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")


def send_notification(
    user_id: int,
    title: str,
    message: str,
    db_path: Optional[Path] = None
) -> None:
    """
    Record an in-app notification for a user.
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                INSERT INTO notifications (user_id, title, message, is_read, created_at)
                VALUES (?, ?, ?, 0, ?)
            """, (user_id, title, message, get_current_iso()))
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to send notification: {e}")


# ============================================================================
# QR CODE PAYLOAD HELPERS
# ============================================================================

def encode_qr_payload(account_number: str, account_holder: str, account_type: str = "Savings") -> str:
    """
    Encode an internal payment target structure into a secure JSON string.
    Never includes sensitive credentials or passwords.
    """
    payload = {
        "app": "BMS",
        "action": "TRANSFER",
        "account_number": str(account_number).strip(),
        "beneficiary_name": str(account_holder).strip(),
        "account_type": str(account_type).strip(),
        "currency": "INR",
        "version": "1.0"
    }
    return json.dumps(payload)


def decode_qr_payload(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse and validate a QR code payload.
    Returns dictionary with target account information or None if invalid.
    """
    try:
        data = json.loads(raw_text.strip())
        if isinstance(data, dict) and data.get("app") == "BMS" and "account_number" in data:
            return data
    except Exception:
        # Fallback: check if the QR raw text is directly a 12-digit account number
        cleaned = raw_text.strip()
        if cleaned.isdigit() and len(cleaned) == 12:
            return {
                "app": "BMS",
                "action": "TRANSFER",
                "account_number": cleaned,
                "beneficiary_name": "Account Holder",
                "account_type": "Account",
                "currency": "INR"
            }
    return None
