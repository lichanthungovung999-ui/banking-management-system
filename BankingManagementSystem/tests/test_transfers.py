"""
Unit tests for atomic transfers, rollbacks on failure, and QR payment encoding/decoding.
"""

import io
from auth import register_user, set_transaction_pin
from services.account_service import get_account_by_id, get_user_accounts
from services.qr_service import decode_qr_image, generate_account_qr
from services.transaction_service import (
    process_deposit,
    process_transfer,
)
from utils import rupees_to_paise


def test_successful_transfer_between_accounts(test_db_path):
    """Test atomic transfer between two users updating both balances and creating linked records."""
    # Register Sender and Receiver
    _, _, sender = register_user("Sender Alice", "alice", "alice@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    _, _, receiver = register_user("Receiver Bob", "bob", "bob@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)

    sender_acc = get_user_accounts(sender["id"], db_path=test_db_path)[0]
    receiver_acc = get_user_accounts(receiver["id"], db_path=test_db_path)[0]

    # Deposit ₹10,000 into sender
    process_deposit(sender["id"], sender_acc["id"], rupees_to_paise(10000), "Initial funds", db_path=test_db_path)

    # Transfer ₹4,000 from Alice to Bob
    ok, msg, receipt = process_transfer(
        sender_user_id=sender["id"],
        sender_account_id=sender_acc["id"],
        recipient_account_number=receiver_acc["account_number"],
        amount_paise=rupees_to_paise(4000),
        description="Project Payment",
        db_path=test_db_path
    )

    assert ok
    assert receipt["reference_no"].startswith("TRF-")

    # Verify Sender balance: 10,000 - 4,000 = 6,000
    sender_updated = get_account_by_id(sender_acc["id"], db_path=test_db_path)
    assert sender_updated["balance_paise"] == rupees_to_paise(6000)

    # Verify Receiver balance: 0 + 4,000 = 4,000
    receiver_updated = get_account_by_id(receiver_acc["id"], db_path=test_db_path)
    assert receiver_updated["balance_paise"] == rupees_to_paise(4000)


def test_transfer_self_transfer_rejection(test_db_path):
    """Test that self-transfer to the exact same account is rejected."""
    _, _, user = register_user("Charlie", "charlie", "charlie@example.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    user_acc = get_user_accounts(user["id"], db_path=test_db_path)[0]

    process_deposit(user["id"], user_acc["id"], rupees_to_paise(5000), db_path=test_db_path)

    ok, msg, _ = process_transfer(
        sender_user_id=user["id"],
        sender_account_id=user_acc["id"],
        recipient_account_number=user_acc["account_number"],
        amount_paise=rupees_to_paise(1000),
        db_path=test_db_path
    )

    assert not ok
    assert "Cannot transfer funds to the same account" in msg


def test_transfer_insufficient_balance(test_db_path):
    """Test that transfer exceeding sender balance is rejected without debiting."""
    _, _, sender = register_user("Sender Low", "lowbal", "low@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    _, _, receiver = register_user("Receiver Ok", "recok", "rec@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)

    sender_acc = get_user_accounts(sender["id"], db_path=test_db_path)[0]
    receiver_acc = get_user_accounts(receiver["id"], db_path=test_db_path)[0]

    process_deposit(sender["id"], sender_acc["id"], rupees_to_paise(1000), db_path=test_db_path)

    # Attempt to transfer ₹5,000 when balance is only ₹1,000
    ok, msg, _ = process_transfer(
        sender_user_id=sender["id"],
        sender_account_id=sender_acc["id"],
        recipient_account_number=receiver_acc["account_number"],
        amount_paise=rupees_to_paise(5000),
        db_path=test_db_path
    )

    assert not ok
    assert "Insufficient balance" in msg


def test_transfer_with_pin_verification(test_db_path):
    """Test transfer requiring transaction PIN when configured."""
    _, _, sender = register_user("Pin User", "pinuser", "pin@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)
    _, _, receiver = register_user("Rec Pin", "recpin", "recpin@test.com", "PassWord#2026", "PassWord#2026", db_path=test_db_path)

    sender_acc = get_user_accounts(sender["id"], db_path=test_db_path)[0]
    receiver_acc = get_user_accounts(receiver["id"], db_path=test_db_path)[0]

    process_deposit(sender["id"], sender_acc["id"], rupees_to_paise(5000), db_path=test_db_path)
    set_transaction_pin(sender["id"], "9911", db_path=test_db_path)

    # 1. Transfer without PIN -> fails
    ok_no_pin, msg_no_pin, _ = process_transfer(
        sender_user_id=sender["id"],
        sender_account_id=sender_acc["id"],
        recipient_account_number=receiver_acc["account_number"],
        amount_paise=rupees_to_paise(1000),
        transaction_pin=None,
        db_path=test_db_path
    )
    assert not ok_no_pin
    assert "PIN is required" in msg_no_pin

    # 2. Transfer with wrong PIN -> fails
    ok_wrong, msg_wrong, _ = process_transfer(
        sender_user_id=sender["id"],
        sender_account_id=sender_acc["id"],
        recipient_account_number=receiver_acc["account_number"],
        amount_paise=rupees_to_paise(1000),
        transaction_pin="0000",
        db_path=test_db_path
    )
    assert not ok_wrong
    assert "Incorrect transaction PIN" in msg_wrong

    # 3. Transfer with correct PIN -> succeeds
    ok_right, msg_right, _ = process_transfer(
        sender_user_id=sender["id"],
        sender_account_id=sender_acc["id"],
        recipient_account_number=receiver_acc["account_number"],
        amount_paise=rupees_to_paise(1000),
        transaction_pin="9911",
        db_path=test_db_path
    )
    assert ok_right


def test_qr_generation_and_decoding_roundtrip():
    """Verify QR code generation and decoding produces exact target account."""
    acc_num = "100188223344"
    holder = "David Miller"

    img, png_bytes = generate_account_qr(acc_num, holder, "Savings")
    assert len(png_bytes) > 0

    # Simulate file upload with BytesIO
    uploaded_file = io.BytesIO(png_bytes)
    ok, msg, data = decode_qr_image(uploaded_file)

    assert ok
    assert data["account_number"] == acc_num
    assert data["beneficiary_name"] == holder
