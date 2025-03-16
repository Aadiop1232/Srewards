import sqlite3
import os
from datetime import datetime
import json
import config

# Global database file path. This file is created in the project root.
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bot.db")

def get_connection():
    """
    Creates and returns a new connection to the SQLite database.
    Using a new connection for each operation ensures thread safety.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def init_db():
    """
    Initialize the database schema.
    Creates tables if they do not exist.
    This function is idempotent and can be run on startup.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Create users table: stores user information
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
    
    # Create referrals table: stores referral relationships between users
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id TEXT,
            referred_id TEXT,
            PRIMARY KEY (user_id, referred_id)
        )
    ''')
    
    # Create platforms table: stores platform name, account stock (as JSON), and price per account
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS platforms (
            platform_name TEXT PRIMARY KEY,
            stock TEXT,
            price INTEGER DEFAULT {config.DEFAULT_ACCOUNT_CLAIM_COST}
        )
    ''')
    
    # Create reviews table: stores reviews submitted by users
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            review TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create admin logs table: stores logs of admin actions
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create channels table: stores channel links (for membership verification)
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT
        )
    ''')
    
    # Create admins table: stores admin accounts and roles
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            banned INTEGER DEFAULT 0
        )
    ''')
    
    # Create keys table: stores reward keys (normal/premium), their points, and claim status
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
    
    # Create configurations table: stores dynamic configuration values
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
    """
    Sets or updates a configuration value.
    Example: set_config_value("account_claim_cost", 15)
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("REPLACE INTO configurations (config_key, config_value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    except Exception as e:
        print(f"Error setting config value for {key}: {e}")
    finally:
        c.close()
        conn.close()

def get_config_value(key):
    """
    Retrieves the configuration value for a given key.
    Returns the value as a string (or None if not set).
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT config_value FROM configurations WHERE config_key = ?", (key,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row[0] if row else None

def set_account_claim_cost(cost):
    """Set the default cost for claiming an account."""
    set_config_value("account_claim_cost", cost)

def get_account_claim_cost():
    """Retrieve the account claim cost; use default if not set."""
    cost = get_config_value("account_claim_cost")
    return int(cost) if cost is not None else config.DEFAULT_ACCOUNT_CLAIM_COST

def set_referral_bonus(bonus):
    """Set the referral bonus value."""
    set_config_value("referral_bonus", bonus)

def get_referral_bonus():
    """Retrieve the referral bonus; use default if not set."""
    bonus = get_config_value("referral_bonus")
    return int(bonus) if bonus is not None else config.DEFAULT_REFERRAL_BONUS

# -----------------------
# User Functions
# -----------------------

def add_user(telegram_id, username, join_date, pending_referrer=None):
    """
    Adds a new user to the database if they don't exist.
    Returns the user record.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    if not user:
        try:
            c.execute("""
                INSERT INTO users (telegram_id, username, join_date, pending_referrer)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, username, join_date, pending_referrer))
            conn.commit()
        except Exception as e:
            print(f"Error adding user {telegram_id}: {e}")
    c.close()
    conn.close()
    return get_user(telegram_id)

def get_user(telegram_id):
    """
    Retrieves a user record by Telegram ID.
    Returns a dictionary of the user data or None if not found.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    c.close()
    conn.close()
    return dict(user) if user else None

def update_user_points(telegram_id, new_points):
    """
    Updates a user's point balance.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET points = ? WHERE telegram_id = ?", (new_points, telegram_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating points for {telegram_id}: {e}")
    finally:
        c.close()
        conn.close()

def ban_user(telegram_id):
    """Set the banned flag for a user."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET banned = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    except Exception as e:
        print(f"Error banning user {telegram_id}: {e}")
    finally:
        c.close()
        conn.close()

def unban_user(telegram_id):
    """Unset the banned flag for a user."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET banned = 0 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    except Exception as e:
        print(f"Error unbanning user {telegram_id}: {e}")
    finally:
        c.close()
        conn.close()

# -----------------------
# Referral Functions
# -----------------------

def add_referral(referrer_id, referred_id):
    """
    Inserts a referral record if one doesn't exist, then awards bonus points to the referrer.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,))
    if not c.fetchone():
        try:
            c.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
            conn.commit()
            bonus = get_referral_bonus()
            c.execute("UPDATE users SET points = points + ?, referrals = referrals + 1 WHERE telegram_id = ?", (bonus, referrer_id))
            conn.commit()
        except Exception as e:
            print(f"Error adding referral for {referred_id}: {e}")
    c.close()
    conn.close()

def clear_pending_referral(telegram_id):
    """Clears any pending referrer for a user."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET pending_referrer = NULL WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    except Exception as e:
        print(f"Error clearing pending referral for {telegram_id}: {e}")
    finally:
        c.close()
        conn.close()

# -----------------------
# Review Functions
# -----------------------

def add_review(user_id, review_text):
    """
    Inserts a new review into the reviews table.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO reviews (user_id, review, timestamp) VALUES (?, ?, ?)", (user_id, review_text, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"Error adding review for {user_id}: {e}")
    finally:
        c.close()
        conn.close()

# -----------------------
# Admin Logs Functions
# -----------------------

def log_admin_action(admin_id, action):
    """
    Inserts a log entry into the admin_logs table.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admin_logs (admin_id, action, timestamp) VALUES (?, ?, ?)", (admin_id, action, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"Error logging admin action: {e}")
    finally:
        c.close()
        conn.close()

# -----------------------
# Key Functions
# -----------------------

def get_key(key_str):
    """
    Retrieves a key record by key string.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE key = ?", (key_str,))
    key_doc = c.fetchone()
    c.close()
    conn.close()
    return dict(key_doc) if key_doc else None

def claim_key_in_db(key_str, telegram_id):
    """
    Claims a key for a user. If the key is valid and unclaimed, marks it as claimed,
    awards the points, and updates the user's balance.
    """
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
    try:
        c.execute("UPDATE keys SET claimed = 1, claimed_by = ?, timestamp = ? WHERE key = ?",
                  (telegram_id, datetime.now(), key_str))
        conn.commit()
        c.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (points_awarded, telegram_id))
        conn.commit()
    except Exception as e:
        print(f"Error claiming key {key_str}: {e}")
    c.close()
    conn.close()
    return f"Key redeemed successfully. You've been awarded {points_awarded} points."

def add_key(key_str, key_type, points):
    """
    Inserts a new key into the keys table.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO keys (key, type, points, claimed, claimed_by, timestamp) VALUES (?, ?, ?, 0, NULL, ?)",
                  (key_str, key_type, points, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"Error adding key {key_str}: {e}")
    finally:
        c.close()
        conn.close()

def get_keys():
    """
    Retrieves all keys as a list of dictionaries.
    """
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
    """
    Returns a leaderboard of users sorted by points in descending order.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    leaderboard = c.fetchall()
    c.close()
    conn.close()
    return [dict(row) for row in leaderboard]

def get_admin_dashboard():
    """
    Returns a tuple (total_users, banned_users, total_points) for dashboard purposes.
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

# -----------------------
# New Functions for Platforms
# -----------------------
# Note: get_platforms and update_stock_for_platform are already defined above

# -----------------------
# Main Execution
# -----------------------

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
