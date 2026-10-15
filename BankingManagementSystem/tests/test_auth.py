"""
Unit tests for user registration, authentication, bcrypt hashing, and account lockout.
"""

from auth import (
    authenticate_user,
    change_password,
    hash_secret,
    register_user,
    set_transaction_pin,
    verify_secret,
    verify_user_pin,
)
from utils import check_password_strength


def test_password_strength_validator():
    """Verify password strength evaluator flags weak and strong passwords."""
    weak = check_password_strength("weak")
    assert not weak["is_valid"]
    assert "At least 8 characters required" in weak["feedback"]

    strong = check_password_strength("SuperSecret@2026")
    assert strong["is_valid"]
    assert strong["score"] >= 4


def test_bcrypt_hashing_and_verification():
    """Test bcrypt hashing and verification correctness."""
    plain = "MySecretPass#123"
    hashed = hash_secret(plain)

    assert hashed != plain
    assert verify_secret(plain, hashed)
    assert not verify_secret("WrongPassword", hashed)


def test_user_registration_success(test_db_path):
    """Test standard customer registration with automatic account generation."""
    success, msg, user = register_user(
        full_name="Rajesh Sharma",
        username="rajesh",
        email="rajesh@example.com",
        password="SecurePass@2026",
        confirm_password="SecurePass@2026",
        phone="+91-9876543210",
        db_path=test_db_path
    )

    assert success
    assert user is not None
    assert user["username"] == "rajesh"
    assert user["role"] == "customer"
    assert len(user["primary_account"]) == 12


def test_duplicate_username_rejection(test_db_path):
    """Test prevention of duplicate usernames."""
    register_user(
        full_name="User One",
        username="testuser",
        email="user1@example.com",
        password="ValidPass@123",
        confirm_password="ValidPass@123",
        db_path=test_db_path
    )

    dup_success, dup_msg, _ = register_user(
        full_name="User Two",
        username="testuser",
        email="user2@example.com",
        password="ValidPass@123",
        confirm_password="ValidPass@123",
        db_path=test_db_path
    )

    assert not dup_success
    assert "Username is already taken" in dup_msg


def test_duplicate_email_rejection(test_db_path):
    """Test prevention of duplicate emails."""
    register_user(
        full_name="User One",
        username="user1",
        email="common@example.com",
        password="ValidPass@123",
        confirm_password="ValidPass@123",
        db_path=test_db_path
    )

    dup_success, dup_msg, _ = register_user(
        full_name="User Two",
        username="user2",
        email="common@example.com",
        password="ValidPass@123",
        confirm_password="ValidPass@123",
        db_path=test_db_path
    )

    assert not dup_success
    assert "Email address is already registered" in dup_msg


def test_login_success_and_failure(test_db_path):
    """Test authentication success and failure handling."""
    register_user(
        full_name="Amit Patel",
        username="amit",
        email="amit@example.com",
        password="MyPassword@999",
        confirm_password="MyPassword@999",
        db_path=test_db_path
    )

    # Success with username
    auth_ok, msg, user = authenticate_user("amit", "MyPassword@999", db_path=test_db_path)
    assert auth_ok
    assert user["full_name"] == "Amit Patel"

    # Success with email
    auth_email_ok, _, _ = authenticate_user("amit@example.com", "MyPassword@999", db_path=test_db_path)
    assert auth_email_ok

    # Failure with wrong password
    fail_ok, fail_msg, _ = authenticate_user("amit", "WrongPass@000", db_path=test_db_path)
    assert not fail_ok
    assert "Invalid username or password" in fail_msg


def test_account_lockout_after_max_failed_attempts(test_db_path):
    """Verify that 5 failed attempts lock the account."""
    register_user(
        full_name="Lockout Target",
        username="lockme",
        email="lockme@example.com",
        password="GoodPass@1234",
        confirm_password="GoodPass@1234",
        db_path=test_db_path
    )

    for i in range(4):
        ok, msg, _ = authenticate_user("lockme", "BadPass", db_path=test_db_path)
        assert not ok
        assert "attempt(s) remaining" in msg

    # 5th attempt triggers lockout
    ok_5, msg_5, _ = authenticate_user("lockme", "BadPass", db_path=test_db_path)
    assert not ok_5
    assert "locked" in msg_5.lower()

    # Even right password is now rejected while locked
    locked_ok, locked_msg, _ = authenticate_user("lockme", "GoodPass@1234", db_path=test_db_path)
    assert not locked_ok
    assert "temporarily locked" in locked_msg.lower()


def test_password_and_pin_change(test_db_path):
    """Test updating user password and transaction PIN."""
    _, _, user = register_user(
        full_name="Pooja Rao",
        username="pooja",
        email="pooja@example.com",
        password="InitialPassword@1",
        confirm_password="InitialPassword@1",
        db_path=test_db_path
    )
    user_id = user["id"]

    # Wrong current password
    pw_ok, _ = change_password(user_id, "WrongOld", "NewPassword@2026", db_path=test_db_path)
    assert not pw_ok

    # Correct current password
    pw_ok2, _ = change_password(user_id, "InitialPassword@1", "NewPassword@2026", db_path=test_db_path)
    assert pw_ok2

    # Set Transaction PIN
    pin_ok, _ = set_transaction_pin(user_id, "8844", db_path=test_db_path)
    assert pin_ok
    assert verify_user_pin(user_id, "8844", db_path=test_db_path)
    assert not verify_user_pin(user_id, "0000", db_path=test_db_path)
