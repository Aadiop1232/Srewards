# handlers/admin.py
import telebot
from telebot import types
import sqlite3
import random, string, json
import config
from db import DATABASE, log_admin_action

def get_db_connection():
    return sqlite3.connect(DATABASE)

# --- Platforms Management ---
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
    if row:
        stock = json.loads(row[0])
    else:
        stock = []
    stock.extend(accounts)
    c.execute("UPDATE platforms SET stock=? WHERE platform_name=?", (json.dumps(stock), platform_name))
    conn.commit()
    conn.close()

# --- Channels Management ---
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

# --- Admins Management ---
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
    c.execute("INSERT OR REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, ?)", (str(user_id), username, role, 0))
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

# --- Users Management ---
def get_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id, username, banned FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def ban_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()

# --- Keys Generation ---
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

# --- Admin Panel Handlers ---
def is_admin(user_id):
    # Check if user is in the OWNERS list
    if str(user_id) in [str(x) for x in config.OWNERS]:
        return True
    # Otherwise check the admins table
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id=? AND banned=0", (str(user_id),))
    row = c.fetchone()
    conn.close()
    return row is not None

def send_admin_menu(bot, message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Access prohibited.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Platform Mgmt", callback_data="admin_platform"),
        types.InlineKeyboardButton("Stock Mgmt", callback_data="admin_stock"),
        types.InlineKeyboardButton("Channel Mgmt", callback_data="admin_channel"),
        types.InlineKeyboardButton("Admin Mgmt", callback_data="admin_manage"),
        types.InlineKeyboardButton("User Mgmt", callback_data="admin_users"),
        types.InlineKeyboardButton("Key Generation", callback_data="admin_keys")
    )
    markup.add(types.InlineKeyboardButton("Back", callback_data="admin_back"))
    bot.send_message(message.chat.id, "Admin Panel", reply_markup=markup)

# (The rest of the admin functions remain unchanged as in the previous complete admin module implementation.)
# ...
# Finally, include a callback router:
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
    elif data == "admin_add_owner":
        handle_admin_add_owner(bot, call)
    elif data == "admin_logs":
        handle_admin_logs(bot, call)
    elif data == "admin_users":
        handle_admin_users(bot, call)
    elif data == "user_ban_unban":
        handle_user_ban_unban(bot, call)
    elif data == "admin_keys":
        handle_admin_keys(bot, call)
    elif data == "gen_normal_keys":
        handle_gen_normal_keys(bot, call)
    elif data == "gen_premium_keys":
        handle_gen_premium_keys(bot, call)
    elif data == "view_keys":
        handle_view_keys(bot, call)
    elif data == "admin_back":
        send_admin_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")
    
