# handlers/admin.py
import telebot
from telebot import types
import sqlite3
import random, string, json, re
import config
from db import DATABASE, log_admin_action

def get_db_connection():
    return sqlite3.connect(DATABASE)

# ----------------------
# Platform Management Functions
# ----------------------
def add_platform(platform_name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO platforms (platform_name, stock) VALUES (?, ?)", (platform_name, json.dumps([])))
        conn.commit()
    except Exception as e:
        conn.close()
        return str(e)
    conn.close()
    return None

def remove_platform(platform_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM platforms WHERE platform_name=?", (platform_name,))
    conn.commit()
    conn.close()

def get_platforms():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT platform_name FROM platforms")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_stock_to_platform(platform_name, accounts):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT stock FROM platforms WHERE platform_name=?", (platform_name,))
    row = c.fetchone()
    if row and row[0]:
        stock = json.loads(row[0])
    else:
        stock = []
    stock.extend(accounts)
    c.execute("UPDATE platforms SET stock=? WHERE platform_name=?", (json.dumps(stock), platform_name))
    conn.commit()
    conn.close()

# ----------------------
# Channels Management Functions
# ----------------------
def get_channels():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, channel_link FROM channels")
    rows = c.fetchall()
    conn.close()
    return rows

def add_channel(channel_link):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
    conn.commit()
    conn.close()

def remove_channel(channel_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id=?", (channel_id,))
    conn.commit()
    conn.close()

# ----------------------
# Admins Management Functions
# ----------------------
def get_admins():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, username, role, banned FROM admins")
    rows = c.fetchall()
    conn.close()
    return rows

def add_admin(user_id, username, role="admin"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)", 
              (str(user_id), username, role))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()

def ban_admin(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned=1 WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()

def unban_admin(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned=0 WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()

# ----------------------
# Users Management Functions
# ----------------------
def get_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, banned FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def ban_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE telegram_id=?", (str(user_id),))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE telegram_id=?", (str(user_id),))
    conn.commit()
    conn.close()

# ----------------------
# Keys Functions (for /gen and /redeem)
# ----------------------
def generate_normal_key():
    return "NKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_premium_key():
    return "PKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def add_key(key, key_type, points):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO keys (key, type, points, claimed) VALUES (?, ?, ?, 0)", (key, key_type, points))
    conn.commit()
    conn.close()

def get_keys():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT key, type, points, claimed, claimed_by FROM keys")
    rows = c.fetchall()
    conn.close()
    return rows

def claim_key_in_db(key, telegram_id):
    conn = get_db_connection()
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

def update_user_points(telegram_id, points):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET points=? WHERE telegram_id=?", (points, telegram_id))
    conn.commit()
    conn.close()

# ----------------------
# Admin Panel Handlers & Security (Using Telegram IDs directly)
# ----------------------
def is_owner(telegram_id):
    # Directly compare the Telegram ID with the ones in config.OWNERS
    return telegram_id in config.OWNERS

def is_admin(telegram_id):
    # Directly compare the Telegram ID with the ones in config.OWNERS or config.ADMINS
    return telegram_id in config.OWNERS or telegram_id in config.ADMINS

def send_admin_menu(bot, message):
    telegram_id = str(message.from_user.id)
    if not is_admin(telegram_id):
        bot.send_message(message.chat.id, "🚫 <b>Access prohibited!</b>", parse_mode="HTML")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_owner(telegram_id):
        markup.add(
            types.InlineKeyboardButton("📺 Platform Mgmt", callback_data="admin_platform"),
            types.InlineKeyboardButton("📈 Stock Mgmt", callback_data="admin_stock"),
            types.InlineKeyboardButton("🔗 Channel Mgmt", callback_data="admin_channel"),
            types.InlineKeyboardButton("👥 Admin Mgmt", callback_data="admin_manage"),
            types.InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("📺 Platform Mgmt", callback_data="admin_platform"),
            types.InlineKeyboardButton("📈 Stock Mgmt", callback_data="admin_stock"),
            types.InlineKeyboardButton("👤 User Mgmt", callback_data="admin_users")
        )
    markup.add(types.InlineKeyboardButton("📢 Notify", callback_data="admin_notify"))
    markup.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="back_main"))
    bot.send_message(message.chat.id, "<b>🛠 Admin Panel</b> 🛠", parse_mode="HTML", reply_markup=markup)

def handle_admin_notify(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Enter notification text to send to all verification channels:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_admin_notify)

def process_admin_notify(message):
    notify_text = message.text.strip()
    if not notify_text:
        message.bot.send_message(message.chat.id, "🚫 <b>Notification text cannot be empty.</b>", parse_mode="HTML")
        return
    formatted = f"<b>Notification:</b>\n\n{notify_text}"
    bot_instance = telebot.TeleBot(config.TOKEN)
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.rstrip('/').split("/")[-1]
            bot_instance.send_message("@" + channel_username, formatted, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending notification to {channel}: {e}")
    bot_instance.send_message(message.chat.id, "✅ <b>Notification sent to all verification channels.</b>", parse_mode="HTML")
    send_admin_menu(bot_instance, message)

# ----------------------
# Callback Router for Admin Commands
# ----------------------
def admin_callback_handler(bot, call):
    data = call.data
    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_platform_add":
        handle_admin_platform_add(bot, call)
    elif data == "admin_platform_remove":
        handle_admin_platform_remove(bot, call)
    elif data.startswith("admin_platform_rm_"):
        platform = data.split("admin_platform_rm_")[1]
        handle_admin_platform_rm(bot, call, platform)
    elif data == "admin_stock":
        handle_admin_stock(bot, call)
    elif data.startswith("admin_stock_"):
        platform = data.split("admin_stock_")[1]
        handle_admin_stock_platform(bot, call, platform)
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
    elif data == "admin_add_owner":
        handle_admin_add_owner(bot, call)
    elif data == "admin_logs":
        bot.answer_callback_query(call.id, "Admin logs not implemented.")
    elif data == "admin_users":
        bot.answer_callback_query(call.id, "User management not implemented.")
    elif data == "user_ban_unban":
        handle_user_ban_unban(bot, call)
    elif data == "admin_keys":
        handle_admin_keys(bot, call)
    elif data == "admin_notify":
        handle_admin_notify(bot, call)
    elif data == "back_main":
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "❓ Unknown admin command.")
    
