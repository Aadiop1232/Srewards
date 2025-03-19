# db.py

import os
import sqlite3
from datetime import datetime
import json
import config
import telebot
from handlers.logs import log_event

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bot.db")

def get_connection():
    """
    Returns a connection to the SQLite database.
    """
    return sqlite3.connect(DATABASE)

def init_db():
    """
    Creates all required tables if they don't already exist.
    """
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

    # Admin logs
    c.execute('''
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id TEXT,
        action TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Channels table (unused in default code, but you can store channel links)
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
        "key" TEXT PRIMARY KEY,
        type TEXT,
        points INTEGER,
        claimed INTEGER DEFAULT 0,
        claimed_by TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Configurations table for storing settings
    c.execute('''
    CREATE TABLE IF NOT EXISTS configurations (
        config_key TEXT PRIMARY KEY,
        config_value TEXT
    )
    ''')

    conn.commit()
    c.close()
    conn.close()

    # Check if the 'verified' column is present; if not, add it
    add_verified_column()

def add_verified_column():
    """
    Ensures the 'verified' column exists in the 'users' table, 
    in case older DB versions didn't have it.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'verified' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
        conn.commit()
    c.close()
    conn.close()

######################
# Config Values
######################

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

######################
# User / Referrals
######################

def add_user(telegram_id, username, join_date, pending_referrer=None):
    """
    Inserts a new user if they don't exist. 
    Returns the user record as a dict.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (telegram_id, username, join_date, pending_referrer) VALUES (?, ?, ?, ?)",
                  (telegram_id, username, join_date, pending_referrer))
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

def add_referral(referrer_id, referred_id):
    """
    Inserts a referral record if it doesn't already exist,
    awards the referrer +10 points and increments their referral count.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
    if not c.fetchone():
        c.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        conn.commit()
        bonus = 10  # Always add 10 points for referral
        c.execute("UPDATE users SET points = points + ?, referrals = referrals + 1 WHERE telegram_id = ?",
                  (bonus, referrer_id))
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

def update_user_verified(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET verified = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    c.close()
    conn.close()

######################
# Reviews
######################

def add_review(user_id, review_text):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reviews (user_id, review, timestamp) VALUES (?, ?, ?)",
              (user_id, review_text, datetime.now()))
    conn.commit()
    c.close()
    conn.close()

######################
# Admin Logs
######################

def log_admin_action(admin_id, action):
    """
    Inserts a log record (admin_id, action, timestamp) into admin_logs.
    Called by log_event in logs.py.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO admin_logs (admin_id, action, timestamp) VALUES (?, ?, ?)",
        (admin_id, action, datetime.now())
    )
    conn.commit()
    c.close()
    conn.close()

######################
# Admins
######################

def get_admins():
    """
    Returns a list of admins from the 'admins' table as dicts.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    admins = c.fetchall()
    c.close()
    conn.close()
    return [dict(a) for a in admins]

######################
# Keys
######################

def get_key(key_str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE \"key\" = ?", (key_str,))
    key_doc = c.fetchone()
    c.close()
    conn.close()
    return dict(key_doc) if key_doc else None

def claim_key_in_db(key_str, telegram_id):
    """
    If key is valid and unclaimed, claim it, awarding the user the key's points.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE \"key\" = ?", (key_str,))
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
    c.execute("UPDATE keys SET claimed = 1, claimed_by = ?, timestamp = ? WHERE \"key\" = ?",
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
    c.execute(
        "INSERT INTO keys (\"key\", type, points, claimed, claimed_by, timestamp) VALUES (?, ?, ?, 0, NULL, ?)",
        (key_str, key_type, points, datetime.now())
    )
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

######################
# Leaderboard
######################

def get_leaderboard(limit=10):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    leaderboard = c.fetchall()
    c.close()
    conn.close()
    return [dict(row) for row in leaderboard]

######################
# Admin Dashboard
######################

def get_admin_dashboard():
    """
    Returns (total_users, banned_users, total_points)
    for an admin stats view if needed.
    """
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

######################
# Platforms / Stock
######################

def get_platforms():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms")
    platforms = c.fetchall()
    c.close()
    conn.close()
    return [dict(p) for p in platforms]

def add_stock_to_platform(platform_name, accounts):
    """
    Adds a list of 'accounts' strings to the existing stock for the given platform.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT stock FROM platforms WHERE platform_name = ?", (platform_name,))
    row = c.fetchone()
    if not row:
        c.close()
        conn.close()
        return f"Platform '{platform_name}' not found."
    current_stock = json.loads(row["stock"]) if row["stock"] else []
    new_stock = current_stock + accounts

    c.execute(
        "UPDATE platforms SET stock = ? WHERE platform_name = ?",
        (json.dumps(new_stock), platform_name)
    )
    conn.commit()
    c.close()
    conn.close()

    log_event(telebot.TeleBot(config.TOKEN), "STOCK",
              f"[STOCK] Stock updated for Platform '{platform_name}'; added {len(accounts)} items.")
    return f"Stock updated with {len(accounts)} items."

def update_stock_for_platform(platform_name, stock):
    """
    Replaces the entire stock array for a given platform.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE platforms SET stock = ? WHERE platform_name = ?",
        (json.dumps(stock), platform_name)
    )
    conn.commit()
    c.close()
    conn.close()

    log_event(telebot.TeleBot(config.TOKEN), "STOCK",
              f"[STOCK] Platform '{platform_name}' stock updated to {len(stock)} items.")

def get_all_users():
    """
    Returns a list of all user records from the 'users' table as dicts.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    c.close()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == '__main__':
    # Initialize DB if run directly
    init_db()
    print("Database initialized.")
