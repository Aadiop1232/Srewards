import sqlite3
import os
from datetime import datetime
import json
import config
import telebot
from handlers.logs import log_event

# Path to the SQLite database file.
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bot.db")

def get_connection():
    """Returns a new connection to the SQLite database."""
    return sqlite3.connect(DATABASE)

def init_db():
    """Initializes the database schema by creating all necessary tables if they do not exist."""
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id TEXT PRIMARY KEY,
            username TEXT,
            join_date TEXT,
            points INTEGER DEFAULT 20,
            referrals INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            pending_referrer TEXT,
            verified INTEGER DEFAULT 0
        )
    ''')

    # Referrals table
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id TEXT,
            referred_id TEXT,
            PRIMARY KEY (user_id, referred_id)
        )
    ''')

    # Platforms table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS platforms (
            platform_name TEXT PRIMARY KEY,
            stock TEXT,
            price INTEGER DEFAULT {config.DEFAULT_ACCOUNT_CLAIM_COST}
        )
    ''')

    # Reviews table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            review TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Admin logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Channels table
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT
        )
    ''')

    # Admins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            banned INTEGER DEFAULT 0
        )
    ''')

    # Keys table
    c.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            type TEXT,
            points INTEGER,
            claimed INTEGER DEFAULT 0,
            claimed_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Configurations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS configurations (
            config_key TEXT PRIMARY KEY,
            config_value TEXT
        )
    ''')

    conn.commit()
    c.close()
    conn.close()
    print("Database initialized.")


# -----------------------
# New Verified User Handling
# -----------------------

def add_verified_column():
    """Adds the 'verified' column to the 'users' table if it doesn't already exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'verified' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
        conn.commit()
    c.close()
    conn.close()

def update_user_verified(telegram_id):
    """Marks a user as verified."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET verified = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    c.close()
    conn.close()

# -----------------------
# Dynamic Configuration Functions
# -----------------------

def set_config_value(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO configurations (config_key, config_value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    c.close()
    conn.close()

def get_config_value(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT config_value FROM configurations WHERE config_key = ?", (key,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row[0] if row else None

# -----------------------
# User Functions
# -----------------------

def add_user(telegram_id, username, join_date, pending_referrer=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    if not user:
        c.execute("""
            INSERT INTO users (telegram_id, username, join_date, pending_referrer)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, username, join_date, pending_referrer))
        conn.commit()
    c.close()
    conn.close()
    return get_user(telegram_id)

def get_user(telegram_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    c.close()
    conn.close()
    return dict(user) if user else None

# -----------------------
# Referral Functions
# -----------------------

def add_referral(referrer_id, referred_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
    if not c.fetchone():
        c.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.commit()
        bonus = get_referral_bonus()
        c.execute("UPDATE users SET points = points + ?, referrals = referrals + 1 WHERE telegram_id = ?", (bonus, referrer_id))
        conn.commit()
    c.close()
    conn.close()

def clear_pending_referral(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET pending_referrer = NULL WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    c.close()
    conn.close()

# -----------------------
# Admin Logs Functions
# -----------------------

def log_admin_action(admin_id, action):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO admin_logs (admin_id, action, timestamp) VALUES (?, ?, ?)", (admin_id, action, datetime.now()))
    conn.commit()
    c.close()
    conn.close()

def get_admins():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    admins = c.fetchall()
    c.close()
    conn.close()
    return [dict(a) for a in admins]

# -----------------------
# Key Functions
# -----------------------

def get_key(key_str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE key = ?", (key_str,))
    key_doc = c.fetchone()
    c.close()
    conn.close()
    return dict(key_doc) if key_doc else None

def claim_key_in_db(key_str, telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE key = ?", (key_str,))
    key_doc = c.fetchone()
    if not key_doc:
        c.close()
        conn.close()
        return "Key not found."
    if key_doc["claimed"]:
        c.close()
        conn.close()
        return "Key already claimed."
    points_awarded = key_doc["points"]
    c.execute("UPDATE keys SET claimed = 1, claimed_by = ?, timestamp = ? WHERE key = ?",
              (telegram_id, datetime.now(), key_str))
    conn.commit()
    c.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (points_awarded, telegram_id))
    conn.commit()
    c.close()
    conn.close()
    return f"Key redeemed successfully. You've been awarded {points_awarded} points."

# -----------------------
# Final Execution
# -----------------------

if __name__ == '__main__':
    init_db()
    add_verified_column()
    print("Database initialized with verified column added.")
