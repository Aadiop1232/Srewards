import sqlite3
import json
import config

# The database file (use a relative or absolute path)
DATABASE = "bot.db"

def init_db():
    """
    Initialize the database with necessary tables.
    This function creates tables for users, admins, platforms, keys, etc.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # Users table: stores user data like Telegram ID, username, join date, points, referrals, banned flag, etc.
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

        # Referrals table: keeps track of who referred whom
        c.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                user_id TEXT,
                referred_id TEXT,
                PRIMARY KEY (user_id, referred_id)
            )
        ''')

        # Platforms table: stores platform name and JSON-encoded stock (accounts)
        c.execute('''
            CREATE TABLE IF NOT EXISTS platforms (
                platform_name TEXT PRIMARY KEY,
                stock TEXT
            )
        ''')

        # Reviews table: stores user reviews/feedback
        c.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                review TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Admin logs table: stores admin actions (e.g., banning/unbanning users)
        c.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id TEXT,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Channels table: stores channels for verification
        c.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_link TEXT
            )
        ''')

        # Admins table: stores admins and their roles
        c.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                role TEXT,
                banned INTEGER DEFAULT 0
            )
        ''')

        # Keys table: stores keys, their type, points, and whether they are claimed
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

        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!")
    except sqlite3.Error as e:
        print(f"❌ Error initializing database: {e}")

# Functions for managing users
def add_user(telegram_id, username, join_date, pending_referrer=None):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (telegram_id, username, join_date, pending_referrer) VALUES (?, ?, ?, ?)",
                  (telegram_id, username, join_date, pending_referrer))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding user: {e}")

def get_user(telegram_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        user = c.fetchone()
        conn.close()
        return user
    except sqlite3.Error as e:
        print(f"❌ Error fetching user: {e}")
        return None

def update_user_pending_referral(telegram_id, pending_referrer):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET pending_referrer=? WHERE telegram_id=?", (pending_referrer, telegram_id))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error updating pending referral: {e}")

def clear_pending_referral(telegram_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET pending_referrer=NULL WHERE telegram_id=?", (telegram_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error clearing pending referral: {e}")

def add_referral(referrer_id, referred_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM referrals WHERE referred_id=?", (referred_id,))
        if c.fetchone():
            conn.close()
            return
        c.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        c.execute("UPDATE users SET points = points + 4, referrals = referrals + 1 WHERE telegram_id=?", (referrer_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding referral: {e}")

# Functions for handling keys
def add_key(key, key_type, points):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO keys (key, type, points, claimed) VALUES (?, ?, ?, 0)", (key, key_type, points))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding key: {e}")

def get_key(key):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT key, type, points, claimed FROM keys WHERE key=?", (key,))
        result = c.fetchone()
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"❌ Error fetching key: {e}")
        return None

def claim_key_in_db(key, telegram_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT claimed, type, points FROM keys WHERE key=?", (key,))
        row = c.fetchone()
        if not row:
            conn.close()
            return "Key not found."
        if row[0] != 0:
            conn.close()
            return "Key already claimed."
        points = row[2]
        c.execute("UPDATE keys SET claimed=1, claimed_by=? WHERE key=?", (telegram_id, key))
        c.execute("UPDATE users SET points = points + ? WHERE telegram_id=?", (points, telegram_id))
        conn.commit()
        conn.close()
        return f"Key redeemed successfully. You've been awarded {points} points."
    except sqlite3.Error as e:
        print(f"❌ Error claiming key: {e}")
        return "An error occurred while claiming the key."

# Functions for managing admins
def get_admins():
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT user_id, username, role, banned FROM admins")
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"❌ Error fetching admins: {e}")
        return []

def add_admin(user_id, username, role="admin"):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)", 
                  (str(user_id), username, role))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding admin: {e}")

def remove_admin(user_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id=?", (str(user_id),))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error removing admin: {e}")

def ban_admin(user_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE admins SET banned=1 WHERE user_id=?", (str(user_id),))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error banning admin: {e}")

def unban_admin(user_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE admins SET banned=0 WHERE user_id=?", (str(user_id),))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error unbanning admin: {e}")
        
