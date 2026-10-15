# 🏛️ Banking Management System (BMS)
### Complete Python Application with Modern UI, Interactive Dashboard & Secure Transactions

> **Tagline:** Secure Banking. Simple Transactions.  
> **Currency:** Indian Rupees (₹)  
> **Platform:** Streamlit, SQLite, Python 3  

---

## 🌟 Overview

The **Banking Management System (BMS)** is a comprehensive, production-grade educational digital banking platform engineered in Python. It provides the visual polish, security paradigms, and operational workflows of a modern digital bank, including multi-account portfolio management, atomic fund transfers, QR-code peer payments, fraud prevention lockout controls, and real-time analytical dashboards.

---

## 🚀 Key Features

### 1. 🔐 Enterprise-Grade Authentication & Security
- **Bcrypt Password Hashing:** All passwords and transaction PINs are cryptographically salted and hashed using `bcrypt` (work-factor 12).
- **Brute-Force Lockout Defense:** Automatically locks an account for 10 minutes upon 5 consecutive failed login attempts.
- **Role-Based Authorization:** Strict separation between standard **Customer** and **Administrator** access privileges.
- **Session Protection:** All private banking pages enforce real-time authentication checks and prevent unauthorized session access.

### 2. 💰 Financial Accuracy & Zero-Overdraft Guarantee
- **Integer Paise Storage:** All balances and transaction amounts are strictly stored in integer paise (1 INR = 100 paise) within SQLite, preventing floating-point calculation drift.
- **ACID Database Transactions:** Balance debit and credit operations are wrapped in atomic database transactions (`PRAGMA foreign_keys = ON;`) with automated rollback on any error.
- **Strict Overdraft Prevention:** Withdrawals and transfers exceeding the cleared available balance are rejected at the database level with a `CHECK (balance_paise >= 0)` constraint.

### 3. 💳 Multi-Account Portfolio Management
- **Automatic Account Allocation:** Generating a unique 12-digit account number (e.g. `1001XXXXXXXX`) upon customer onboarding.
- **Multiple Account Types:** Support for both **Savings** and **Current** accounts.
- **Interactive Card Widget:** Ultra-modern debit card visualizer rendering account number masking (`•••• •••• 1234`), balance, cardholder name, and operational status.

### 4. 🔁 Atomic Transfers & Optional PIN Verification
- **Peer-to-Peer Transfers:** Instant account-to-account funds transfer with live beneficiary name validation.
- **Transaction PIN Protection:** Optional 4 or 6-digit numeric PIN for high-value transfer authorization.
- **Self-Transfer Prevention:** Rejects duplicate transfer attempts to the source account.

### 5. 📱 QR-Code Payment System
- **Branded QR Generation:** Generates personalized QR codes encoding payment recipient information using `qrcode` and `Pillow`.
- **Computer-Vision Scanning:** Decodes uploaded payment QR code images using `opencv-python-headless` (`cv2.QRCodeDetector`).
- **Simulated Demonstration:** Clear regulatory disclaimers explaining the simulated educational environment.

### 6. 📊 Real-Time Analytics & Plotly Dashboards
- **KPI Metrics:** Total balance across accounts, active account count, total inflow (deposits), and total outflow (withdrawals).
- **Interactive Visualizations:**
  - Monthly Inflow vs Outflow grouped bar charts powered by `Plotly`.
  - Category and transaction type breakdown donut charts.
- **Notification Center:** Real-time in-app alerts for deposits, transfers, and security events.

### 7. 🧾 Digital Receipts & PDF Export
- **On-Screen Receipts:** Formatted digital transaction receipts featuring timestamps, reference IDs, and masked account numbers.
- **Official PDF Downloads:** Automatically generates printable PDF receipts using `fpdf2`.
- **CSV Ledger Export:** One-click export of complete transaction history to CSV.

### 8. 🛡️ Administrator Terminal
- **Bank-Wide Metrics:** Aggregated metrics of total registered customers, total accounts, total bank deposits, and transaction volume.
- **Account Freeze / Unfreeze:** Administrative controls to freeze suspected accounts with mandatory audit reasoning.
- **Immutable Audit Trail:** Comprehensive event log tracking logins, lockouts, password modifications, account creation, and transfers.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Core Language** | Python 3.10+ (Tested up to Python 3.14) |
| **Frontend UI** | Streamlit, HTML5, Custom CSS (`styles.py`) |
| **Database** | SQLite3 (Persistent with Foreign Keys enabled) |
| **Security / Crypto** | bcrypt |
| **Data Processing** | pandas |
| **Interactive Charts** | Plotly Express & Plotly Graph Objects |
| **QR Code Engine** | qrcode, Pillow, opencv-python-headless |
| **PDF Generation** | fpdf2 |
| **Testing Suite** | pytest |

---

## 📂 Project Structure

```text
BankingManagementSystem/
├── .streamlit/
│   └── config.toml               # Streamlit theme & server configuration
├── assets/
│   └── logo.png                  # Banking logo asset
├── database/
│   ├── .gitkeep
│   └── banking.db                # SQLite persistent database (auto-generated)
├── pages/
│   ├── 1_Dashboard.py            # Overview, KPI metrics & Plotly charts
│   ├── 2_My_Accounts.py          # View accounts, debit card UI & new accounts
│   ├── 3_Deposit.py              # Deposit money & get PDF receipt
│   ├── 4_Withdraw.py             # Withdraw money with overdraft protection
│   ├── 5_Transfer.py             # P2P atomic transfers with PIN check
│   ├── 6_QR_Payments.py          # Generate QR & upload/scan QR payment
│   ├── 7_Check_Balance.py        # Live balance inquiry & account ledger
│   ├── 8_Transaction_History.py  # Filters, CSV export & receipt viewer
│   ├── 9_Profile_Settings.py     # Profile info, password update & PIN setup
│   └── 10_Admin_Dashboard.py     # Administrative metrics & audit logs
├── services/
│   ├── __init__.py
│   ├── account_service.py        # Account queries, creation & status controls
│   ├── transaction_service.py    # Atomic deposits, withdrawals, transfers & analytics
│   ├── qr_service.py             # QR generation (Pillow) & decoding (OpenCV)
│   └── receipt_service.py        # On-screen receipts & PDF creation (fpdf2)
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Isolated temporary test database fixture
│   ├── test_auth.py              # Registration, bcrypt, lockout & PIN tests
│   ├── test_accounts.py          # Account creation, isolation & freeze tests
│   ├── test_transactions.py      # Deposit & withdrawal tests
│   └── test_transfers.py         # Atomic transfers, PIN check & QR tests
├── app.py                        # Main entry point & authentication hub
├── auth.py                       # Authentication, bcrypt & session management
├── database.py                   # Schema initialization & connection management
├── styles.py                     # Custom CSS and bank UI component renderers
├── utils.py                      # Currency formatting (₹), identifiers & helpers
├── requirements.txt              # Complete dependency specifications
├── .gitignore                    # Git exclusion rules
└── README.md                     # Project documentation
```

---

## 💻 Installation & Setup Instructions (Windows)

### Prerequisites
- Python 3.10 or newer installed on your computer.

### Step 1: Open Terminal in Project Directory
Navigate to the project root directory:
```powershell
cd "c:\Users\sulan\OneDrive\Desktop\BankingManagementSystem"
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
streamlit run app.py
```
Your default web browser will open automatically at `http://localhost:8501`.

---

## 🔑 Demo Credentials

| Role | Username | Password | Notes |
|---|---|---|---|
| **Administrator** | `admin` | `Admin@BMS2026` | Full access to Admin Console and Audit Trail |
| **New Customer** | *(Register in UI)* | *(Choose in UI)* | Generates a 12-digit account number automatically |

---

## 🧪 Running Automated Unit Tests

A comprehensive test suite of 19 automated tests is included, using an isolated temporary SQLite database so test runs never touch production data:

```powershell
.venv\Scripts\pytest -v
```

All 19 test cases cover:
- ✅ Password strength calculation & bcrypt hashing
- ✅ Customer registration & duplicate detection
- ✅ Login lockout after 5 consecutive failed attempts
- ✅ Account creation, ownership isolation & admin freeze
- ✅ Atomic deposits and zero-overdraft withdrawal protection
- ✅ Multi-account transfers with rollback verification
- ✅ Transaction PIN authorization
- ✅ QR code generation & OpenCV image decoding round-trip

---

## 📜 Disclaimer
This software is an educational simulation developed for academic demonstration. It is not connected to real banking payment gateways (e.g. UPI, SWIFT, NEFT) and should not be used to process real monetary transactions.
