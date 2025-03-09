import sqlite3

DATABASE = "bot.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Users table with correct column order
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
    
    # Other tables (unchanged)
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id TEXT,
            referred_id TEXT,
            PRIMARY KEY (user_id, referred_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS platforms (
            platform_name TEXT PRIMARY KEY,
            stock TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            review TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            banned INTEGER DEFAULT 0
        )
    ''')
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

def add_user(telegram_id, username, join_date, pending_referrer=None):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO users 
        (telegram_id, username, join_date, points, referrals, banned, pending_referrer)
        VALUES (?, ?, ?, 20, 0, 0, ?)
    ''', (telegram_id, username, join_date, pending_referrer))
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

# Keep other functions same as previous version
# ... [rest of your existing db.py functions] ...
