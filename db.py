# db.py
import sqlite3
import os
from datetime import datetime
import json
import config

# Database file path (stored in the project root so that data persists across hosts)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bot.db")

def get_connection():
    """Returns a new SQLite connection."""
    return sqlite3.connect(DATABASE)

def init_db():
    """Initializes the database and creates tables if they do not exist."""
    conn = get_connection()
    c = conn.cursor()
    # Users table: stores user info
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
    # Referrals table: stores referral relationships
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id TEXT,
            referred_id TEXT,
            PRIMARY KEY (user_id, referred_id)
        )
    ''')
    # Platforms table: stores platform name, account stock (as JSON), and price per account
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS platforms (
            platform_name TEXT PRIMARY KEY,
            stock TEXT,
            price INTEGER DEFAULT {config.DEFAULT_ACCOUNT_CLAIM_COST}
        )
    ''')
    # Reviews table: stores user reviews
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            review TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Admin logs table: logs admin actions
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Channels table: stores channel links for required channels
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT
        )
    ''')
    # Admins table: stores admin info
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            banned INTEGER DEFAULT 0
        )
    ''')
    # Keys table: stores generated keys, their type, points, and claim status
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
    # Configurations table: stores dynamic configuration values
    c.execute('''
        CREATE TABLE IF NOT EXISTS configurations (
            config_key TEXT PRIMARY KEY,
            config_value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_config_value(key, value):
    """Sets or updates a configuration value."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO configurations (config_key, config_value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    c.close()
    conn.close()

def get_config_value(key):
    """Retrieves a configuration value by key."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT config_value FROM configurations WHERE config_key = ?", (key,))
    row = c.fetchone()
    c.close()
    conn.close()
    return row[0] if row else None

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
