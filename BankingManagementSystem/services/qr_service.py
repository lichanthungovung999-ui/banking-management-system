"""
QR code service for generating and decoding payment codes using qrcode and OpenCV.
Simulates modern mobile QR payments securely without leaking passwords or PINs.
"""

import io
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import qrcode

from utils import decode_qr_payload, encode_qr_payload


def generate_account_qr(
    account_number: str,
    account_holder: str,
    account_type: str = "Savings"
) -> Tuple[Image.Image, bytes]:
    """
    Generate a branded QR code encoding recipient account details.
    Returns: (PIL.Image, bytes_png)
    """
    payload_str = encode_qr_payload(account_number, account_holder, account_type)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)

    # Standard high-contrast QR pattern on pure white background for optical scanning
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    return img, png_bytes


def decode_qr_image(uploaded_file) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Decode an uploaded QR code image using OpenCV.
    Returns: (success: bool, message: str, payload_dict)
    """
    if uploaded_file is None:
        return False, "No file uploaded.", None

    try:
        # Load image into PIL and convert to OpenCV RGB numpy array
        image = Image.open(uploaded_file).convert("RGB")
        image_np = np.array(image)

        # Detect and decode QR code
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(image_np)

        if not data or not data.strip():
            # Try OpenCV grayscale conversion fallback
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            data, _, _ = detector.detectAndDecode(gray)

        if not data or not data.strip():
            return False, "Could not detect a valid QR code in the uploaded image. Please ensure the code is clear and not blurry.", None

        parsed_data = decode_qr_payload(data)
        if not parsed_data or "account_number" not in parsed_data:
            return False, "This QR code does not contain a recognized BMS banking payment target.", None

        return True, "Payment QR code verified successfully!", parsed_data

    except Exception as e:
        return False, f"Failed to decode QR code: {str(e)}", None
