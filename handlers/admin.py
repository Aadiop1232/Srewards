# handlers/admin.py
import telebot
from telebot import types
import sqlite3
import random, string, json, re
import config
from db import DATABASE, log_admin_action, get_user, ban_user, unban_user

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

###############################
# KEYS MANAGEMENT FUNCTIONS
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

def claim_key_in_db(key, user_id):
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
    c.execute("UPDATE keys SET claimed=1, claimed_by=? WHERE key=?", (user_id, key))
    c.execute("UPDATE users SET points = points + ? WHERE telegram_id=?", (points, user_id))
    conn.commit()
    conn.close()
    return f"Key redeemed successfully. You've been awarded {points} points."

###############################
# ADMIN PANEL HANDLERS & SECURITY
###############################
def is_owner(user_or_id):
    if user_or_id is None:
        return False
    try:
        tid = str(user_or_id.id)
    except AttributeError:
        tid = str(user_or_id)
    return tid in config.OWNERS

def is_admin(user_or_id):
    if is_owner(user_or_id):
        return True
    try:
        user_id = str(user_or_id.id)
    except AttributeError:
        user_id = str(user_or_id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return True if row else False

def send_admin_menu(bot, update):
    # Determine chat_id, message_id, and user correctly for both messages and callback queries
    if hasattr(update, "message"):
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        user_obj = update.from_user
    elif hasattr(update, "data"):
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        user_obj = update.from_user
    else:
        chat_id = update.chat.id
        message_id = update.message.message_id
        user_obj = update.from_user
    markup = types.InlineKeyboardMarkup(row_width=2)
    # All admin functions are shown:
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

###############################
# PLATFORM SUB-HANDLERS
###############################
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
    bot.register_next_step_handler(msg, lambda m: process_platform_add(bot, m))

def process_platform_add(bot, message):
    platform_name = message.text.strip()
    error = add_platform(platform_name)
    if error:
        response = f"Error adding platform: {error}"
    else:
        response = f"Platform '{platform_name}' added successfully!"
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_platform_remove(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_platform_rm_{plat}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_platform_rm(bot, call, platform):
    remove_platform(platform)
    bot.answer_callback_query(call.id, f"Platform '{platform}' removed.")
    handle_admin_platform(bot, call)

###############################
# STOCK SUB-HANDLERS
###############################
def handle_admin_stock(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available. Add one first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        markup.add(types.InlineKeyboardButton(plat, callback_data=f"admin_stock_{plat}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Select a platform to add stock:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_stock_platform(bot, call, platform):
    msg = bot.send_message(call.message.chat.id, f"âœï¸ Send the stock text for platform {platform} (type or attach a .txt file):")
    bot.register_next_step_handler(msg, process_stock_upload, platform)

def process_stock_upload(message, platform):
    bot_instance = telebot.TeleBot(config.TOKEN)
    if message.content_type == "document":
        file_info = bot_instance.get_file(message.document.file_id)
        downloaded_file = bot_instance.download_file(file_info.file_path)
        try:
            data = downloaded_file.decode('utf-8')
        except Exception as e:
            bot_instance.send_message(message.chat.id, f"Error decoding file: {e}")
            return
    else:
        data = message.text.strip()
    import re
    email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+")
    accounts = []
    current_account = ""
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if email_pattern.match(line):
            if current_account:
                accounts.append(current_account.strip())
            current_account = line
        else:
            current_account += " " + line
    if current_account:
        accounts.append(current_account.strip())
    add_stock_to_platform(platform, accounts)
    bot_instance.send_message(message.chat.id,
                              f"Stock for {platform} updated with {len(accounts)} accounts.")
    from handlers.admin import send_admin_menu
    send_admin_menu(bot_instance, message)

###############################
# CHANNEL SUB-HANDLERS (Owners Only)
###############################
def handle_admin_channel(bot, call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Access prohibited. Only owners can manage channels.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("âž• Add Channel", callback_data="admin_channel_add"),
        types.InlineKeyboardButton("âž– Remove Channel", callback_data="admin_channel_remove")
    )
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("Channel Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_add(bot, call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the channel link to add:")
    bot.register_next_step_handler(msg, lambda m: process_channel_add(bot, m))

def process_channel_add(bot, message):
    channel_link = message.text.strip()
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
        conn.commit()
        conn.close()
        response = f"Channel '{channel_link}' added successfully."
    except Exception as e:
        response = f"Error adding channel: {e}"
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_channel_remove(bot, call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    channels = get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "No channels to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for cid, link in channels:
        markup.add(types.InlineKeyboardButton(link, callback_data=f"admin_channel_rm_{cid}"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_channel"))
    bot.edit_message_text("Select a channel to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "Channel removed.")
    handle_admin_channel(bot, call)

###############################
# ADMIN MANAGEMENT (Owners Only)
###############################
def handle_admin_manage(bot, call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Access prohibited. Only owners can manage admins.")
        return
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
            text += f"â€¢ UserID: {admin[0]}, Username: {admin[1]}, Role: {admin[2]}, Banned: {admin[3]}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id)

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the admin UserID to ban/unban:")
    bot.register_next_step_handler(msg, lambda m: process_admin_ban_unban(bot, m))

def process_admin_ban_unban(bot, message):
    user_id = message.text.strip()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT banned FROM admins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row is None:
        response = "Admin not found."
    else:
        if row[0] == 0:
            ban_admin(user_id)
            response = f"Admin {user_id} has been banned."
            try:
                bot.send_message(user_id, "You have been banned by an administrator.")
            except Exception as e:
                print(f"Error notifying banned admin: {e}")
        else:
            unban_admin(user_id)
            response = f"Admin {user_id} has been unbanned."
            try:
                bot.send_message(user_id, "You have been unbanned by an administrator.")
            except Exception as e:
                print(f"Error notifying unbanned admin: {e}")
    conn.close()
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the admin UserID to remove:")
    bot.register_next_step_handler(msg, lambda m: process_admin_remove(bot, m))

def process_admin_remove(bot, message):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"Admin {user_id} removed."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_add(bot, call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "Access prohibited. Only owners can add admins.")
        return
    msg = bot.send_message(call.message.chat.id, "âœï¸ Send the UserID and Username (separated by a space) to add as admin:")
    bot.register_next_step_handler(msg, lambda m: process_admin_add(bot, m))

def process_admin_add(bot, message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        response = "Please provide both UserID and Username."
    else:
        user_id, username = parts[0], " ".join(parts[1:])
        add_admin(user_id, username, role="admin")
        response = f"Admin {user_id} added with username {username}."
        try:
            bot.send_message(user_id, "You have been added as an admin.")
        except Exception as e:
            print(f"Error notifying new admin: {e}")
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

###############################
# USER MANAGEMENT SUB-HANDLERS
###############################
def handle_user_management(bot, call):
    users = get_users()
    if not users:
        bot.answer_callback_query(call.id, "No users found.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        user_id, username, banned = u
        status = "Banned" if banned else "Active"
        btn_text = f"{username} ({user_id}) - {status}"
        callback_data = f"user_{user_id}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="back_main"))
    bot.edit_message_text("User Management\nSelect a user to manage:", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, reply_markup=markup)

def handle_user_management_detail(bot, call, user_id):
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return
    # Order: [telegram_id, username, join_date, points, referrals, banned, pending_referrer]
    status = "Banned" if user[5] else "Active"
    text = (f"User Management\n\n"
            f"User ID: {user[0]}\n"
            f"Username: {user[1]}\n"
            f"Join Date: {user[2]}\n"
            f"Balance: {user[3]} points\n"
            f"Total Referrals: {user[4]}\n"
            f"Status: {status}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    if user[5]:
        markup.add(types.InlineKeyboardButton("Unban", callback_data=f"user_{user_id}_unban"))
    else:
        markup.add(types.InlineKeyboardButton("Ban", callback_data=f"user_{user_id}_ban"))
    markup.add(types.InlineKeyboardButton("ðŸ”™ Back", callback_data="admin_users"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

def handle_user_ban_action(bot, call, user_id, action):
    if action == "ban":
        ban_user(user_id)
        text = f"User {user_id} has been banned."
    elif action == "unban":
        unban_user(user_id)
        text = f"User {user_id} has been unbanned."
    else:
        text = "Invalid action."
    bot.answer_callback_query(call.id, text)
    handle_user_management_detail(bot, call, user_id)

###############################
# CALLBACK ROUTER
###############################
def admin_callback_handler(bot, call):
    data = call.data
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
    elif data == "admin_users":
        handle_user_management(bot, call)
    elif data.startswith("user_") and data.count("_") == 1:
        user_id = data.split("_")[1]
        handle_user_management_detail(bot, call, user_id)
    elif data.startswith("user_") and data.count("_") == 2:
        parts = data.split("_")
        user_id = parts[1]
        action = parts[2]
        handle_user_ban_action(bot, call, user_id, action)
    elif data == "back_main":
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")