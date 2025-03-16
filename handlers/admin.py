# handlers/admin.py
import sqlite3
import json
import config
from datetime import datetime
from telebot import types
import telebot
from db import get_user, ban_user, unban_user, update_user_points, get_account_claim_cost
from handlers.logs import log_event

# Check if a user is admin or owner
def is_admin(user_or_id):
    try:
        user_id = str(user_or_id.id)
    except AttributeError:
        user_id = str(user_or_id)
    return user_id in config.OWNERS or user_id in config.ADMINS

# -----------------------
# PLATFORM MANAGEMENT FUNCTIONS
# -----------------------

def add_platform(platform_name, price):
    """
    Add a new platform with a custom price.
    """
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    if c.fetchone():
        c.close()
        conn.close()
        return f"Platform '{platform_name}' already exists."
    c.execute("INSERT INTO platforms (platform_name, stock, price) VALUES (?, ?, ?)", 
              (platform_name, "[]", price))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "platform", f"Platform '{platform_name}' added with price {price} points.")
    return None

def remove_platform(platform_name):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM platforms WHERE platform_name = ?", (platform_name,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "platform", f"Platform '{platform_name}' removed.")

def get_platforms():
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms")
    platforms = c.fetchall()
    c.close()
    conn.close()
    return [dict(p) for p in platforms]

def add_stock_to_platform(platform_name, accounts):
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT stock FROM platforms WHERE platform_name = ?", (platform_name,))
    row = c.fetchone()
    current_stock = json.loads(row["stock"]) if row and row["stock"] else []
    new_stock = current_stock + accounts
    c.execute("UPDATE platforms SET stock = ? WHERE platform_name = ?", (json.dumps(new_stock), platform_name))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "stock", f"Added {len(accounts)} accounts to platform '{platform_name}'.")
    return f"Stock updated with {len(accounts)} accounts."

def update_stock_for_platform(platform_name, stock):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("UPDATE platforms SET stock = ? WHERE platform_name = ?", (json.dumps(stock), platform_name))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "stock", f"Platform '{platform_name}' stock updated to {len(stock)} accounts.")

# -----------------------
# CHANNEL MANAGEMENT FUNCTIONS
# -----------------------

def add_channel(channel_link):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "channel", f"Channel '{channel_link}' added.")

def remove_channel(channel_id):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "channel", f"Channel with ID '{channel_id}' removed.")

def get_channels():
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM channels")
    channels = c.fetchall()
    c.close()
    conn.close()
    return [dict(ch) for ch in channels]

# -----------------------
# ADMINS MANAGEMENT FUNCTIONS
# -----------------------

def get_admins():
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    admins = c.fetchall()
    c.close()
    conn.close()
    return [dict(a) for a in admins]

def add_admin(user_id, username, role="admin"):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)", (user_id, username, role))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' ({username}) added with role '{role}'.")

def remove_admin(user_id):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' removed.")

def ban_admin(user_id):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' banned.")

def unban_admin(user_id):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' unbanned.")

# -----------------------
# KEY FUNCTIONS
# -----------------------

def generate_normal_key():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_premium_key():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def add_key(key_str, key_type, points):
    from db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO keys (key, type, points, claimed, claimed_by, timestamp) VALUES (?, ?, ?, 0, NULL, ?)",
              (key_str, key_type, points, datetime.now()))
    conn.commit()
    c.close()
    conn.close()

# -----------------------
# LENDING POINTS
# -----------------------

def lend_points(admin_id, user_id, points, custom_message=None):
    user = get_user(user_id)
    if not user:
        return f"User '{user_id}' not found."
    new_balance = user["points"] + points
    update_user_points(user_id, new_balance)
    log_event(telebot.TeleBot(config.TOKEN), "lend", f"Admin {admin_id} lent {points} points to user {user_id}.")
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
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Account claim cost updated to {cost} points.")

def update_referral_bonus(bonus):
    from db import set_config_value
    set_config_value("referral_bonus", bonus)
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Referral bonus updated to {bonus} points.")

# -----------------------
# USER MANAGEMENT (for Admin Panel)
# -----------------------

def get_all_users():
    from db import get_connection
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    c.close()
    conn.close()
    return [dict(u) for u in users]

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

# New flow: When adding a platform, ask for platform name then for price.
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
