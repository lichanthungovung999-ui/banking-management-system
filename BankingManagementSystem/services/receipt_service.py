"""
Receipt service for generating visual on-screen receipts and downloadable PDF documents
using fpdf2.
"""

from datetime import datetime
from typing import Any, Dict
from fpdf import FPDF
import streamlit as st

from utils import format_datetime, mask_account_number


class BankReceiptPDF(FPDF):
    """Custom PDF template for professional banking receipts."""

    def header(self):
        # Header banner
        self.set_fill_color(15, 23, 42)  # Dark navy
        self.rect(0, 0, 210, 32, "F")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 18)
        self.set_xy(15, 8)
        self.cell(0, 8, "BMS BANK", ln=True)

        self.set_font("Helvetica", "", 9)
        self.set_xy(15, 17)
        self.cell(0, 5, "Official Transaction Receipt | Secure Banking Platform", ln=True)
        self.ln(12)

    def footer(self):
        self.set_y(-25)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, "This is a computer-generated transaction receipt from BMS Bank educational simulation.", align="C", ln=True)
        self.cell(0, 5, f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | Confidential", align="C")


def generate_receipt_pdf(receipt_data: Dict[str, Any]) -> bytes:
    """
    Generate a high-quality PDF receipt binary stream.
    """
    pdf = BankReceiptPDF(orientation="P", unit="mm", format="A5")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Status Pill Box
    status = receipt_data.get("status", "SUCCESS")
    if status == "SUCCESS":
        pdf.set_fill_color(220, 252, 231)  # Soft green
        pdf.set_text_color(21, 128, 61)     # Green text
    else:
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(185, 28, 28)

    pdf.set_font("Helvetica", "B", 10)
    pdf.rect(15, 38, 118, 10, "F")
    pdf.set_xy(15, 39)
    pdf.cell(118, 8, f"TRANSACTION STATUS: {status}", align="C", ln=True)
    pdf.ln(6)

    # Key Value Rows
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)

    fields = [
        ("Reference Number", str(receipt_data.get("reference_no", "N/A"))),
        ("Date & Time", format_datetime(receipt_data.get("timestamp"))),
        ("Transaction Type", str(receipt_data.get("type", "N/A"))),
        ("Amount", str(receipt_data.get("amount_formatted", "N/A"))),
        ("Account", mask_account_number(str(receipt_data.get("account_number", receipt_data.get("sender_account", "N/A"))))),
    ]

    if "recipient_account" in receipt_data:
        fields.append(("Beneficiary Account", mask_account_number(str(receipt_data.get("recipient_account")))))
    if "recipient_name" in receipt_data:
        fields.append(("Beneficiary Name", str(receipt_data.get("recipient_name"))))
    if "balance_after_formatted" in receipt_data:
        fields.append(("Updated Balance", str(receipt_data.get("balance_after_formatted"))))

    fields.append(("Description", str(receipt_data.get("description", "Standard Transaction"))))

    pdf.set_xy(15, 54)
    for label, val in fields:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(50, 7, label, border="B")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(68, 7, val, border="B", align="R", ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(118, 5, "Please retain this receipt for your records. For customer service or dispute inquiries, quote the reference number above.")

    # Return bytes output
    return bytes(pdf.output())


def render_receipt_html(receipt_data: Dict[str, Any]) -> None:
    """Render an aesthetic on-screen transaction receipt card."""
    ref_no = receipt_data.get("reference_no", "N/A")
    timestamp = format_datetime(receipt_data.get("timestamp"))
    txn_type = receipt_data.get("type", "N/A")
    amount = receipt_data.get("amount_formatted", "₹0.00")
    account = mask_account_number(str(receipt_data.get("account_number", receipt_data.get("sender_account", "N/A"))))
    desc = receipt_data.get("description", "N/A")
    status = receipt_data.get("status", "SUCCESS")
    balance_after = receipt_data.get("balance_after_formatted", "")

    html = f"""
    <div class="bms-receipt-box">
        <div class="bms-receipt-header">
            <div style="font-size: 1.3rem; font-weight: 800; color: #0f172a;">🏛️ BMS BANK</div>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 2px;">Official Transaction Receipt</div>
            <div style="margin-top: 10px;">
                <span class="bms-badge bms-badge-success">{status}</span>
            </div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 12px;">{amount}</div>
        </div>
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Reference Number:</span>
            <span class="bms-receipt-value" style="font-family: monospace;">{ref_no}</span>
        </div>
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Timestamp:</span>
            <span class="bms-receipt-value">{timestamp}</span>
        </div>
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Transaction Type:</span>
            <span class="bms-receipt-value">{txn_type}</span>
        </div>
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Account Number:</span>
            <span class="bms-receipt-value">{account}</span>
        </div>
    """

    if "recipient_account" in receipt_data:
        html += f"""
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Beneficiary Account:</span>
            <span class="bms-receipt-value">{mask_account_number(str(receipt_data.get("recipient_account")))}</span>
        </div>
        """

    if balance_after:
        html += f"""
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Updated Balance:</span>
            <span class="bms-receipt-value">{balance_after}</span>
        </div>
        """

    html += f"""
        <div class="bms-receipt-row">
            <span class="bms-receipt-label">Description:</span>
            <span class="bms-receipt-value">{desc}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
