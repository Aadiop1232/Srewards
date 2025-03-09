# handlers/admin.py
import telebot
from telebot import types
import sqlite3
import random, string, json, re
import config

# Use config.DATABASE if defined; otherwise default to "bot.db"
def get_db_connection():
    return sqlite3.connect(getattr(config, "DATABASE", "bot.db"))

###############################
# PLATFORM MANAGEMENT FUNCTIONS
###############################
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

###############################
# CHANNEL MANAGEMENT FUNCTIONS
###############################
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

###############################
# ADMINS MANAGEMENT FUNCTIONS
###############################
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

###############################
# USERS MANAGEMENT FUNCTIONS
###############################
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

###############################
# KEYS MANAGEMENT FUNCTIONS (for /gen and /redeem)
###############################
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

###############################
# ADMIN PANEL HANDLERS & SECURITY
###############################
def is_owner(user_or_id):
    """
    Returns True if the given user (object or raw ID) matches an entry in config.OWNERS.
    Also supports matching by username (case-insensitive).
    """
    if user_or_id is None:
        return False
    try:
        tid = str(user_or_id.id)
        uname = (user_or_id.username or "").lower()
    except AttributeError:
        tid = str(user_or_id)
        uname = ""
    owners = [str(x).lower() for x in config.OWNERS]
    if tid.lower() in owners or (uname and uname in owners):
        print(f"DEBUG is_owner: {tid} or {uname} recognized as owner.")
        return True
    return False

def is_admin(user_or_id):
    """
    Returns True if the given user (object or raw ID) is recognized as an admin
    by config.ADMINS or is an owner.
    Supports matching by Telegram ID or username.
    """
    if is_owner(user_or_id):
        return True
    if user_or_id is None:
        return False
    try:
        tid = str(user_or_id.id)
        uname = (user_or_id.username or "").lower()
    except AttributeError:
        tid = str(user_or_id)
        uname = ""
    admins = [str(x).lower() for x in config.ADMINS]
    if tid.lower() in admins or (uname and uname in admins):
        print(f"DEBUG is_admin: {tid} or {uname} recognized as admin.")
        return True
    return False

def send_admin_menu(bot, message):
    """
    Displays the admin menu. Since only admins/owners see the Admin Panel button in the main menu,
    we assume this function is called only by authorized users.
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_owner(message.from_user):
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

def admin_callback_handler(bot, call):
    data = call.data
    # Check admin privileges here; if not admin, do nothing.
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
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

###############################
# PLATFORM SUB-HANDLERS
###############################
def handle_admin_platform(bot, call):
    platforms = get_platforms()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="admin_platform_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("<b>📺 Platform Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_platform_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the platform name to add:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_platform_add)

def process_platform_add(message):
    platform_name = message.text.strip()
    error = add_platform(platform_name)
    if error:
        response = f"❌ Error adding platform: {error}"
    else:
        response = f"✅ Platform <b>{platform_name}</b> added successfully!"
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

def handle_admin_platform_remove(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "😕 No platforms to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_platform_rm_{plat}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("<b>📺 Select a platform to remove:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_platform_rm(bot, call, platform):
    remove_platform(platform)
    bot.answer_callback_query(call.id, f"✅ Platform <b>{platform}</b> removed.")
    handle_admin_platform(bot, call)

###############################
# STOCK SUB-HANDLERS
###############################
def handle_admin_stock(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "😕 No platforms available. Add one first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_stock_{plat}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("<b>📈 Select a platform to add stock:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_stock_platform(bot, call, platform):
    msg = bot.send_message(call.message.chat.id, f"✏️ <b>Send the stock text for platform {platform} (each account on a new line):</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_stock_upload, platform)

def process_stock_upload(message, platform):
    data = message.text.strip()
    accounts = [line.strip() for line in data.splitlines() if line.strip()]
    add_stock_to_platform(platform, accounts)
    message.bot.send_message(message.chat.id,
                              f"✅ Stock for <b>{platform}</b> updated with {len(accounts)} accounts.",
                              parse_mode="HTML")
    send_admin_menu(message.bot, message)

###############################
# CHANNEL SUB-HANDLERS
###############################
def handle_admin_channel(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Channel", callback_data="admin_channel_add"),
        types.InlineKeyboardButton("➖ Remove Channel", callback_data="admin_channel_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("<b>🔗 Channel Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_channel_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the channel link to add:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_channel_add)

def process_channel_add(message):
    channel_link = message.text.strip()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
        conn.commit()
        conn.close()
        response = f"✅ Channel <b>{channel_link}</b> added successfully."
    except Exception as e:
        response = f"❌ Error adding channel: {e}"
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

def handle_admin_channel_remove(bot, call):
    channels = get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "😕 No channels to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for cid, link in channels:
        markup.add(types.InlineKeyboardButton(link, callback_data=f"admin_channel_rm_{cid}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_channel"))
    bot.edit_message_text("<b>🔗 Select a channel to remove:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "✅ Channel removed.")
    handle_admin_channel(bot, call)

###############################
# ADMIN MANAGEMENT SUB-HANDLERS
###############################
def handle_admin_manage(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Admin List", callback_data="admin_list"),
        types.InlineKeyboardButton("🚫 Ban/Unban Admin", callback_data="admin_ban_unban")
    )
    markup.add(
        types.InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove"),
        types.InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")
    )
    markup.add(
        types.InlineKeyboardButton("👑 Add Owner", callback_data="admin_add_owner")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("<b>👥 Admin Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_list(bot, call):
    admins = get_admins()
    if not admins:
        text = "😕 No admins found."
    else:
        text = "<b>👥 Admins:</b>\n"
        for admin in admins:
            text += f"• ID: {admin[0]}, Username: {admin[1]}, Role: {admin[2]}, Banned: {admin[3]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML")

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the admin Telegram ID to ban/unban:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_admin_ban_unban)

def process_admin_ban_unban(message):
    user_id = message.text.strip()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT banned FROM admins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row is None:
        response = "❌ Admin not found."
    else:
        if row[0] == 0:
            ban_admin(user_id)
            response = f"🚫 Admin {user_id} has been banned."
        else:
            unban_admin(user_id)
            response = f"✅ Admin {user_id} has been unbanned."
    conn.close()
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the admin Telegram ID to remove:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_admin_remove)

def process_admin_remove(message):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"✅ Admin {user_id} removed."
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

def handle_admin_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the admin Telegram ID and Username (separated by a space) to add:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_admin_add)

def process_admin_add(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        response = "❌ Please provide both Telegram ID and Username."
    else:
        user_id, username = parts[0], " ".join(parts[1:])
        add_admin(user_id, username, role="admin")
        response = f"✅ Admin {user_id} added with username {username}."
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

def handle_admin_add_owner(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the Telegram ID to add as owner:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_admin_add_owner)

def process_admin_add_owner(message):
    user_id = message.text.strip()
    add_admin(user_id, "Owner", role="owner")
    response = f"👑 Telegram ID {user_id} added as owner."
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

###############################
# USER MANAGEMENT SUB-HANDLERS
###############################
def handle_user_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ <b>Send the Telegram ID to ban/unban:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_user_ban_unban)

def process_user_ban_unban(message):
    user_id = message.text.strip()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE telegram_id=?", (user_id,))
    row = c.fetchone()
    if row is None:
        response = "❌ User not found."
    else:
        if row[0] == 0:
            ban_user(user_id)
            response = f"🚫 User {user_id} has been banned."
        else:
            unban_user(user_id)
            response = f"✅ User {user_id} has been unbanned."
    conn.close()
    message.bot.send_message(message.chat.id, response, parse_mode="HTML")
    send_admin_menu(message.bot, message)

###############################
# KEYS MANAGEMENT SUB-HANDLERS
###############################
def handle_admin_keys(bot, call):
    keys = get_keys()
    if not keys:
        text = "😕 No keys generated."
    else:
        text = "<b>🔑 Keys:</b>\n"
        for k in keys:
            text += f"• {k[0]} | {k[1]} | Points: {k[2]} | Claimed: {k[3]} | By: {k[4]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML")
