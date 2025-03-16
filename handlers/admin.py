# db.py
import sqlite3
import os
from datetime import datetime
import json
import config

# Global database file path (bot.db is created in the project root)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bot.db")

def get_connection():
    """Creates and returns a new connection to the SQLite database."""
    return sqlite3.connect(DATABASE)

def is_admin(user_or_id):
    try:
        user_id = str(user_or_id.id)
    except AttributeError:
        user_id = str(user_or_id)
    return user_id in config.OWNERS or user_id in config.ADMINS


def init_db():
    """Initializes the database and creates tables if they do not exist."""
    conn = get_connection()
    c = conn.cursor()
    
    # Users table: stores user information.
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
    
    # Referrals table: stores referral relationships between users.
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id TEXT,
            referred_id TEXT,
            PRIMARY KEY (user_id, referred_id)
        )
    ''')
    
    # Platforms table: stores platform name, stock (as JSON), and price per account.
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS platforms (
            platform_name TEXT PRIMARY KEY,
            stock TEXT,
            price INTEGER DEFAULT {config.DEFAULT_ACCOUNT_CLAIM_COST}
        )
    ''')
    
    # Reviews table: stores user reviews.
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            review TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Admin logs table: stores logs of admin actions.
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Channels table: stores channel links.
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT
        )
    ''')
    
    # Admins table: stores admin information.
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            banned INTEGER DEFAULT 0
        )
    ''')
    
    # Keys table: stores reward keys.
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
    
    # Configurations table: stores dynamic configuration values.
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
# USER MANAGEMENT (for Admin Panel)
# -----------------------

def get_all_users():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    c.close()
    conn.close()
    return [dict(u) for u in users]

# -----------------------
# ADMIN KEYS
# -----------------------

def generate_normal_key():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_premium_key():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

# -----------------------
# LENDING POINTS
# -----------------------

def lend_points(admin_id, user_id, points, custom_message=None):
    user = get_user(user_id)
    if not user:
        return f"User '{user_id}' not found."
    new_balance = user["points"] + points
    update_user_points(user_id, new_balance)
    log_admin_action(admin_id, f"Lent {points} points to user {user_id}.")
    bot_instance = telebot.TeleBot(config.TOKEN)
    if custom_message:
        msg = custom_message
    else:
        msg = f"You have been lent {points} points. Your new balance is {new_balance} points."
    try:
        bot_instance.send_message(user_id, msg)
    except Exception as e:
        print(f"Error sending message to user {user_id}: {e}")
    return f"{points} points have been added to user {user_id}. New balance: {new_balance} points."

# -----------------------
# DYNAMIC CONFIGURATION COMMANDS
# -----------------------

def update_account_claim_cost(cost):
    from db import set_config_value
    set_config_value("account_claim_cost", cost)
    log_admin_action("system", f"Account claim cost updated to {cost} points.")

def update_referral_bonus(bonus):
    from db import set_config_value
    set_config_value("referral_bonus", bonus)
    log_admin_action("system", f"Referral bonus updated to {bonus} points.")

# -----------------------
# ADMIN PANEL CALLBACK ROUTER AND HANDLERS
# -----------------------

def send_admin_menu(bot, update):
    if isinstance(update, telebot.types.Message):
        chat_id = update.chat.id
        message_id = update.message_id
    elif isinstance(update, telebot.types.CallbackQuery):
        chat_id = update.message.chat.id
        message_id = update.message.message_id
    else:
        chat_id = update.chat.id
        message_id = update.message_id

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("ðŸ“º Platform Mgmt", callback_data="admin_platform"),
        types.InlineKeyboardButton("ðŸ“ˆ Stock Mgmt", callback_data="admin_stock"),
        types.InlineKeyboardButton("ðŸ”— Channel Mgmt", callback_data="admin_channel"),
        types.InlineKeyboardButton("ðŸ‘¥ Admin Mgmt", callback_data="admin_manage"),
        types.InlineKeyboardButton("ðŸ‘¤ User Mgmt", callback_data="admin_users"),
        types.InlineKeyboardButton("âž• Add Admin", callback_data="admin_add")
    )
    markup.add(types.InlineKeyboardButton("ðŸ”™ Main Menu", callback_data="back_main"))
    try:
        bot.edit_message_text("ðŸ›  Admin Panel", chat_id=chat_id, message_id=message_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, "ðŸ›  Admin Panel", reply_markup=markup)

def handle_admin_platform(bot, call):
    platforms = get_platforms()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("âž• Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("âž– Remove Platform", callback_data="admin_platform_remove")
    )
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Platform Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_platform_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the platform name to add:")
    bot.register_next_step_handler(msg, process_platform_add)

def process_platform_add(bot, message):
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the account price for platform '{platform_name}':")
    bot.register_next_step_handler(msg, process_platform_price, platform_name)

def process_platform_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a number.")
        return
    error = add_platform(platform_name, price)
    if error:
        response = error
    else:
        response = f"Platform '{platform_name}' added successfully with price {price} points."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_platform_remove(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_rm_{plat_name}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_platform_rm(bot, call, platform_name):
    remove_platform(platform_name)
    bot.answer_callback_query(call.id, f"Platform '{platform_name}' removed.")
    handle_admin_platform(bot, call)

def handle_admin_stock(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available. Add one first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_stock_{plat_name}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Select a platform to update stock:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_stock_platform(bot, call, platform_name):
    msg = bot.send_message(call.message.chat.id, f"âœï¸ Send the stock text for platform '{platform_name}' (attach file or type text):")
    bot.register_next_step_handler(msg, process_stock_upload_admin, platform_name)

def process_stock_upload_admin(message, platform_name):
    if message.content_type == "document":
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            try:
                data = downloaded_file.decode('utf-8')
            except UnicodeDecodeError:
                data = downloaded_file.decode('latin-1', errors='replace')
        except Exception as e:
            bot.send_message(message.chat.id, f"âŒ Error downloading file: {e}")
            return
    else:
        data = message.text.strip()
    if "\n\n" in data:
        accounts = [block.strip() for block in data.split("\n\n") if block.strip()]
    else:
        accounts = [line.strip() for line in data.splitlines() if line.strip()]
    update_stock_for_platform(platform_name, accounts)
    bot.send_message(message.chat.id, f"âœ… Stock for '{platform_name}' updated with {len(accounts)} accounts.")
    send_admin_menu(bot, message)

def handle_admin_channel(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("âž• Add Channel", callback_data="admin_channel_add"),
        types.InlineKeyboardButton("âž– Remove Channel", callback_data="admin_channel_remove")
    )
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Channel Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the channel link to add:")
    bot.register_next_step_handler(msg, lambda m: process_channel_add(bot, m))

def process_channel_add(bot, message):
    channel_link = message.text.strip()
    add_channel(channel_link)
    response = f"Channel '{channel_link}' added successfully."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_channel_remove(bot, call):
    channels = get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "No channels to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in channels:
        cid = str(channel.get("id"))
        link = channel.get("channel_link")
        markup.add(types.InlineKeyboardButton(link, callback_data=f"admin_channel_rm_{cid}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_channel"))
    bot.edit_message_text("Select a channel to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "Channel removed.")
    handle_admin_channel(bot, call)

def handle_admin_manage(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("ðŸ‘¥ Admin List", callback_data="admin_list"),
        types.InlineKeyboardButton("ðŸš« Ban/Unban Admin", callback_data="admin_ban_unban")
    )
    markup.add(
        types.InlineKeyboardButton("âŒ Remove Admin", callback_data="admin_remove"),
        types.InlineKeyboardButton("âž• Add Admin", callback_data="admin_add")
    )
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Admin Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_list(bot, call):
    admins = get_admins()
    if not admins:
        text = "No admins found."
    else:
        text = "ðŸ‘¥ Admins:\n"
        for admin in admins:
            text += f"â€¢ UserID: {admin.get('user_id')}, Username: {admin.get('username')}, Role: {admin.get('role')}, Banned: {admin.get('banned')}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id)

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the admin UserID to ban/unban:")
    bot.register_next_step_handler(msg, process_admin_ban_unban)

def process_admin_ban_unban(message):
    user_id = message.text.strip()
    from db import get_connection
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    admin_doc = c.fetchone()
    if not admin_doc:
        response = "Admin not found."
    else:
        if admin_doc["banned"]:
            unban_admin(user_id)
            response = f"Admin {user_id} has been unbanned."
        else:
            ban_admin(user_id)
            response = f"Admin {user_id} has been banned."
    c.close()
    conn.close()
    bot_instance = telebot.TeleBot(config.TOKEN)
    bot_instance.send_message(message.chat.id, response)
    send_admin_menu(bot_instance, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the admin UserID to remove:")
    bot.register_next_step_handler(msg, process_admin_remove)

def process_admin_remove(message):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"Admin {user_id} removed."
    bot_instance = telebot.TeleBot(config.TOKEN)
    bot_instance.send_message(message.chat.id, response)
    send_admin_menu(bot_instance, message)

def handle_admin_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the UserID and Username (separated by space) to add as admin:")
    bot.register_next_step_handler(msg, process_admin_add)

def process_admin_add(message):
    parts = message.text.strip().split()
    bot_instance = telebot.TeleBot(config.TOKEN)
    if len(parts) < 2:
        response = "Please provide both UserID and Username."
    else:
        user_id, username = parts[0], " ".join(parts[1:])
        add_admin(user_id, username, role="admin")
        response = f"Admin {user_id} added with username {username}."
    bot_instance.send_message(message.chat.id, response)
    send_admin_menu(bot_instance, message)

# -----------------------
# USER MANAGEMENT (Admin Panel)
# -----------------------

def handle_user_management(bot, call):
    users = get_all_users()
    if not users:
        bot.answer_callback_query(call.id, "No users found.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        uid = u.get("telegram_id")
        username = u.get("username")
        banned = u.get("banned", 0)
        status = "Banned" if banned else "Active"
        btn_text = f"{username} ({uid}) - {status}"
        callback_data = f"admin_user_{uid}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("User Management\nSelect a user to manage:", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, reply_markup=markup)

def handle_user_management_detail(bot, call, user_id):
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return
    status = "Banned" if user.get("banned", 0) else "Active"
    text = (f"User Management\n\n"
            f"User ID: {user.get('telegram_id')}\n"
            f"Username: {user.get('username')}\n"
            f"Join Date: {user.get('join_date')}\n"
            f"Balance: {user.get('points')} points\n"
            f"Total Referrals: {user.get('referrals')}\n"
            f"Status: {status}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    if user.get("banned", 0):
        markup.add(types.InlineKeyboardButton("Unban", callback_data=f"admin_user_{user_id}_unban"))
    else:
        markup.add(types.InlineKeyboardButton("Ban", callback_data=f"admin_user_{user_id}_ban"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_users"))
    try:
        bot.edit_message_text(
            text, 
            chat_id=call.message.chat.id,
            message_id=call.message.message_id, 
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def handle_user_ban_action(bot, call, user_id, action):
    if action == "ban":
        ban_user(user_id)
        result_text = f"User {user_id} has been banned."
        log_event(bot, "ban", f"User {user_id} banned by admin {call.from_user.id}.")
    elif action == "unban":
        unban_user(user_id)
        result_text = f"User {user_id} has been unbanned."
        log_event(bot, "unban", f"User {user_id} unbanned by admin {call.from_user.id}.")
    else:
        result_text = "Invalid action."
    bot.answer_callback_query(call.id, result_text)
    handle_user_management_detail(bot, call, user_id)

# -----------------------
# ADMIN CALLBACK ROUTER
# -----------------------

def admin_callback_handler(bot, call):
    data = call.data
    if not (str(call.from_user.id) in config.ADMINS or str(call.from_user.id) in config.OWNERS):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return

    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_platform_add":
        handle_admin_platform_add(bot, call)
    elif data == "admin_platform_remove":
        handle_admin_platform_remove(bot, call)
    elif data.startswith("admin_platform_rm_"):
        platform_name = data.split("admin_platform_rm_")[1]
        handle_admin_platform_rm(bot, call, platform_name)
    elif data == "admin_stock":
        handle_admin_stock(bot, call)
    elif data.startswith("admin_stock_"):
        platform_name = data.split("admin_stock_")[1]
        handle_admin_stock_platform(bot, call, platform_name)
    elif data == "admin_channel":
        handle_admin_channel(bot, call)
    elif data == "admin_channel_add":
        handle_admin_channel_add(bot, call)
    elif data == "admin_channel_remove":
        handle_admin_channel_remove(bot, call)
    elif data.startswith("admin_channel_rm_"):
        channel_id = data.split("admin_channel_rm_")[1]
        handle_admin_channel_rm(bot, call, channel_id)
    elif data == "admin_manage":
        handle_admin_manage(bot, call)
    elif data == "admin_list":
        handle_admin_list(bot, call)
    elif data == "admin_ban_unban":
        handle_admin_ban_unban(bot, call)
    elif data == "admin_remove":
        handle_admin_remove(bot, call)
    elif data == "admin_add":
        handle_admin_add(bot, call)
    elif data == "admin_users":
        handle_user_management(bot, call)
    elif data.startswith("admin_user_") and data.count("_") == 2:
        user_id = data.split("_")[2]
        handle_user_management_detail(bot, call, user_id)
    elif data.startswith("admin_user_") and data.count("_") == 3:
        parts = data.split("_")
        user_id = parts[2]
        action = parts[3]
        handle_user_ban_action(bot, call, user_id, action)
    elif data == "back_main":
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")
       