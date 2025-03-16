import sqlite3
import os
from datetime import datetime
import json
import config

# Path to the SQLite database file. This file will be created in the project root.
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
            pending_referrer TEXT
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

def set_account_claim_cost(cost):
    set_config_value("account_claim_cost", cost)

def get_account_claim_cost():
    cost = get_config_value("account_claim_cost")
    return int(cost) if cost is not None else config.DEFAULT_ACCOUNT_CLAIM_COST

def set_referral_bonus(bonus):
    set_config_value("referral_bonus", bonus)

def get_referral_bonus():
    bonus = get_config_value("referral_bonus")
    return int(bonus) if bonus is not None else config.DEFAULT_REFERRAL_BONUS

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

def update_user_points(telegram_id, new_points):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET points = ? WHERE telegram_id = ?", (new_points, telegram_id))
    conn.commit()
    c.close()
    conn.close()

def ban_user(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    c.close()
    conn.close()

def unban_user(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned = 0 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    c.close()
    conn.close()

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
# Review Functions
# -----------------------

def add_review(user_id, review_text):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reviews (user_id, review, timestamp) VALUES (?, ?, ?)", (user_id, review_text, datetime.now()))
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
    conn.row_factory = sqlite3.Row
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

def add_key(key_str, key_type, points):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO keys (key, type, points, claimed, claimed_by, timestamp) VALUES (?, ?, ?, 0, NULL, ?)",
              (key_str, key_type, points, datetime.now()))
    conn.commit()
    c.close()
    conn.close()

def get_keys():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM keys")
    keys = c.fetchall()
    c.close()
    conn.close()
    return [dict(k) for k in keys]

# -----------------------
# Additional Functions
# -----------------------

def get_leaderboard(limit=10):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    leaderboard = c.fetchall()
    c.close()
    conn.close()
    return [dict(row) for row in leaderboard]

def get_admin_dashboard():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    banned_users = c.fetchone()[0]
    c.execute("SELECT SUM(points) FROM users")
    total_points = c.fetchone()[0] or 0
    c.close()
    conn.close()
    return total_users, banned_users, total_points

# -----------------------
# NEW FUNCTION: get_platforms
# -----------------------

def get_platforms():
    """
    Retrieve all platforms from the database as a list of dictionaries.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms")
    platforms = c.fetchall()
    c.close()
    conn.close()
    return [dict(p) for p in platforms]

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
