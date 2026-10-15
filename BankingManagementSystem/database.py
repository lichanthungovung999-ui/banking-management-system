"""
Database configuration, connection management, and schema initialization for the
Banking Management System.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

# Base directory for database
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "database" / "banking.db"


def get_db_path() -> Path:
    """Return the database path, allowing override via environment variable."""
    env_path = os.getenv("BMS_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


@contextmanager
def get_db_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing a SQLite database connection with row factory
    and foreign key enforcement. Automatically commits on success and rolls back on exception.
    """
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        timeout=20.0,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_path: Optional[Path] = None) -> None:
    """
    Idempotently initialize all database tables, indexes, and initial admin record.
    Preserves all existing data.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                pin_hash TEXT,
                full_name TEXT NOT NULL,
                phone TEXT,
                role TEXT NOT NULL DEFAULT 'customer',
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                lockout_until TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 2. Accounts table (balances strictly stored in integer paise: 1 INR = 100 paise)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                account_type TEXT NOT NULL DEFAULT 'Savings',
                balance_paise INTEGER NOT NULL DEFAULT 0 CHECK (balance_paise >= 0),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_ref TEXT UNIQUE NOT NULL,
                account_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
                balance_after_paise INTEGER NOT NULL CHECK (balance_after_paise >= 0),
                description TEXT,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                created_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
            );
        """)

        # 4. Transfers table (links sender and receiver transactions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_ref TEXT UNIQUE NOT NULL,
                sender_account_id INTEGER NOT NULL,
                receiver_account_id INTEGER NOT NULL,
                sender_transaction_id INTEGER,
                receiver_transaction_id INTEGER,
                amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
                description TEXT,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                created_at TEXT NOT NULL,
                FOREIGN KEY (sender_account_id) REFERENCES accounts(id),
                FOREIGN KEY (receiver_account_id) REFERENCES accounts(id),
                FOREIGN KEY (sender_transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (receiver_transaction_id) REFERENCES transactions(id)
            );
        """)

        # 5. Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 6. Audit Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT DEFAULT '127.0.0.1',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
        """)

        # Performance and Search Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_number ON accounts(account_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_ref ON transfers(transfer_ref);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);")

        # Initialize Default Administrator if not present
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1;")
        admin_exists = cursor.fetchone()

        if not admin_exists:
            # We use bcrypt to hash the initial administrator password securely
            import bcrypt
            now_iso = datetime.now().isoformat()
            default_admin_pass = os.getenv("BMS_ADMIN_PASSWORD", "Admin@BMS2026")
            hashed_admin_pass = bcrypt.hashpw(default_admin_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            cursor.execute("""
                INSERT INTO users (
                    username, email, password_hash, full_name, phone, role, is_active,
                    failed_login_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                "admin",
                "admin@bms.local",
                hashed_admin_pass,
                "System Administrator",
                "+91-9999900000",
                "admin",
                1,
                now_iso,
                now_iso
            ))

            admin_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                admin_id,
                "INITIAL_SETUP",
                "Default administrator account created. Default credentials: admin / Admin@BMS2026. Please update in profile settings.",
                now_iso
            ))


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully at:", get_db_path())
