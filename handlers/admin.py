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
    if row and row[0]:
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
    c.execute("INSERT OR REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, ?)", 
              (str(user_id), username, role, 0))
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
    uid = str(user_id)
    # Check if user is in the OWNERS list
    if uid in config.OWNERS:
        return True
    # Otherwise, check the admins table
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id=? AND banned=0", (uid,))
    row = c.fetchone()
    conn.close()
    return row is not None

def send_admin_menu(bot, message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 *Access prohibited!*", parse_mode="Markdown")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📺 Platform Mgmt", callback_data="admin_platform"),
        types.InlineKeyboardButton("📈 Stock Mgmt", callback_data="admin_stock"),
        types.InlineKeyboardButton("🔗 Channel Mgmt", callback_data="admin_channel"),
        types.InlineKeyboardButton("👥 Admin Mgmt", callback_data="admin_manage"),
        types.InlineKeyboardButton("👤 User Mgmt", callback_data="admin_users"),
        types.InlineKeyboardButton("🔑 Key Gen", callback_data="admin_keys")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.send_message(message.chat.id, "🛠 *Admin Panel* 🛠", parse_mode="Markdown", reply_markup=markup)

# --- PLATFORM MANAGEMENT HANDLERS ---
def handle_admin_platform(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="admin_platform_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text("📺 *Platform Management* 📺", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_platform_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the platform name to add:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_platform_add)

def process_platform_add(message):
    platform_name = message.text.strip()
    error = add_platform(platform_name)
    bot = telebot.TeleBot(config.TOKEN)
    if error:
        response = f"❌ Error adding platform: {error}"
    else:
        response = f"✅ Platform *{platform_name}* added successfully!"
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_admin_platform_remove(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "😕 No platforms to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_platform_rm_{plat}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("📺 *Select a platform to remove:*", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_platform_rm(bot, call, platform):
    remove_platform(platform)
    bot.answer_callback_query(call.id, f"✅ Platform *{platform}* removed.")
    handle_admin_platform(bot, call)

# --- STOCK MANAGEMENT HANDLERS ---
def handle_admin_stock(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "😕 No platforms available. Add one first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_stock_{plat}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text("📈 *Select a platform to add stock:*", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_stock_platform(bot, call, platform):
    msg = bot.send_message(call.message.chat.id, f"✏️ *Send the stock text for platform {platform}:*\n(Each account on a new line)", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_stock_upload, platform)

def process_stock_upload(message, platform):
    data = message.text.strip()
    accounts = data.splitlines()
    add_stock_to_platform(platform, accounts)
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, f"✅ Stock for *{platform}* updated with {len(accounts)} accounts.", parse_mode="Markdown")
    send_admin_menu(bot, message)

# --- CHANNEL MANAGEMENT HANDLERS ---
def handle_admin_channel(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Channel", callback_data="admin_channel_add"),
        types.InlineKeyboardButton("➖ Remove Channel", callback_data="admin_channel_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text("🔗 *Channel Management* 🔗", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_channel_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the channel link to add:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_channel_add)

def process_channel_add(message):
    channel_link = message.text.strip()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
        conn.commit()
        conn.close()
        response = f"✅ Channel *{channel_link}* added successfully."
    except Exception as e:
        response = f"❌ Error adding channel: {e}"
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_admin_channel_remove(bot, call):
    channels = get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "😕 No channels to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for cid, link in channels:
        markup.add(types.InlineKeyboardButton(link, callback_data=f"admin_channel_rm_{cid}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_channel"))
    bot.edit_message_text("🔗 *Select a channel to remove:*", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "✅ Channel removed.")
    handle_admin_channel(bot, call)

# --- ADMIN MANAGEMENT (For Owners Only) ---
def handle_admin_manage(bot, call):
    if str(call.from_user.id) not in [str(x) for x in config.OWNERS]:
        bot.answer_callback_query(call.id, "🚫 Access prohibited.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 Admin List", callback_data="admin_list"),
        types.InlineKeyboardButton("🚫 Ban/Unban Admin", callback_data="admin_ban_unban"),
        types.InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove"),
        types.InlineKeyboardButton("👑 Add Owner", callback_data="admin_add_owner"),
        types.InlineKeyboardButton("📝 Admin Logs", callback_data="admin_logs")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text("👥 *Admin Management* 👥", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_admin_list(bot, call):
    admins = get_admins()
    if not admins:
        text = "😕 No admins found."
    else:
        text = "👥 *Admins:*\n"
        for admin in admins:
            text += f"• *UserID:* {admin[0]}, *Username:* {admin[1]}, *Role:* {admin[2]}, *Banned:* {admin[3]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown")

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the admin UserID to ban/unban:*", parse_mode="Markdown")
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
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the admin UserID to remove:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_admin_remove)

def process_admin_remove(message):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"✅ Admin {user_id} removed."
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_admin_add_owner(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the UserID to add as owner:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_admin_add_owner)

def process_admin_add_owner(message):
    user_id = message.text.strip()
    username = message.from_user.username or message.from_user.first_name
    add_admin(user_id, username, role="owner")
    response = f"👑 User {user_id} added as owner."
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_admin_logs(bot, call):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    if not rows:
        text = "😕 No admin logs available."
    else:
        text = "📝 *Admin Logs:*\n"
        for row in rows:
            text += f"• {row[2]} by {row[1]} at {row[3]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown")

# --- USER MANAGEMENT HANDLERS ---
def handle_admin_users(bot, call):
    users = get_users()
    if not users:
        text = "😕 No users found."
    else:
        text = "👤 *Users:*\n"
        for user in users:
            text += f"• *UserID:* {user[0]}, *Username:* {user[1]}, *Banned:* {user[2]}\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚫 Ban/Unban User", callback_data="user_ban_unban"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_user_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Send the UserID to ban/unban:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_user_ban_unban)

def process_user_ban_unban(message):
    user_id = message.text.strip()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
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
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

# --- KEYS GENERATION HANDLERS ---
def handle_admin_keys(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 Generate Normal Keys", callback_data="gen_normal_keys"),
        types.InlineKeyboardButton("🔑 Generate Premium Keys", callback_data="gen_premium_keys")
    )
    markup.add(types.InlineKeyboardButton("👀 View Keys", callback_data="view_keys"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
    bot.edit_message_text("🔑 *Key Generation System* 🔑", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def handle_gen_normal_keys(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Enter quantity of normal keys to generate:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_gen_normal_keys)

def process_gen_normal_keys(message):
    try:
        qty = int(message.text.strip())
    except:
        qty = 1
    generated = []
    for _ in range(qty):
        key = generate_normal_key()
        add_key(key, "normal", 15)
        generated.append(key)
    response = "✅ *Normal Keys Generated:*\n" + "\n".join(generated)
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_gen_premium_keys(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ *Enter quantity of premium keys to generate:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_gen_premium_keys)

def process_gen_premium_keys(message):
    try:
        qty = int(message.text.strip())
    except:
        qty = 1
    generated = []
    for _ in range(qty):
        key = generate_premium_key()
        add_key(key, "premium", 35)
        generated.append(key)
    response = "✅ *Premium Keys Generated:*\n" + "\n".join(generated)
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    send_admin_menu(bot, message)

def handle_view_keys(bot, call):
    keys = get_keys()
    if not keys:
        text = "😕 No keys generated."
    else:
        text = "🔑 *Keys:*\n"
        for k in keys:
            text += f"• {k[0]} | {k[1]} | Points: {k[2]} | Claimed: {k[3]} | By: {k[4]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                            message_id=call.message.message_id, parse_mode="Markdown")

# --- Callback Router ---
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
        bot.answer_callback_query(call.id, "❓ Unknown admin command.")
