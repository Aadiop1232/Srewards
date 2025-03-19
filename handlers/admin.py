import sqlite3
import json
import config
from datetime import datetime
from telebot import types
import telebot
from db import get_user, ban_user, unban_user, update_user_points, get_account_claim_cost, get_admins, get_connection, get_all_users
from handlers.logs import log_event


def is_admin(user_or_id):
    try:
        if isinstance(user_or_id, dict):
            user_id = str(user_or_id.get("telegram_id"))
        else:
            user_id = str(user_or_id.id)
    except AttributeError:
        user_id = str(user_or_id)
    db_admins = get_admins()
    db_admin_ids = [admin.get("user_id") for admin in db_admins]
    return user_id in config.OWNERS or user_id in db_admin_ids

# ----------------------------------------------------------------
# The function main.py needs:
def send_admin_menu(bot, update):
    # This function is called in main.py to show the Admin Panel.
    if hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        user = update.message.from_user
        message_id = update.message.message_id
    elif hasattr(update, "from_user") and update.from_user:
        chat_id = update.message.chat.id if hasattr(update, "message") and update.message else update.chat.id
        user = update.from_user
        message_id = update.message.message_id if hasattr(update, "message") and update.message else None
    else:
        chat_id = update.chat.id
        user = update.from_user
        message_id = None

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📺 Platform Mgmt", callback_data="admin_platform"),
        types.InlineKeyboardButton("📈 Stock Mgmt", callback_data="admin_stock"),
        types.InlineKeyboardButton("🔗 Channel Mgmt", callback_data="admin_channel"),
        types.InlineKeyboardButton("👥 Admin Mgmt", callback_data="admin_manage"),
        types.InlineKeyboardButton("👤 User Mgmt", callback_data="admin_users"),
        types.InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")
    )
    markup.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="back_main"))
    try:
        if message_id:
            bot.edit_message_text("🛠 Admin Panel", chat_id=chat_id, message_id=message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, "🛠 Admin Panel", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, "🛠 Admin Panel", reply_markup=markup)

def add_platform(platform_name, price):
    conn = get_connection()
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
    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM", f"[PLATFORM] {config.OWNERS[0]} added Account Platform: {platform_name} with price {price} pts.")
    return f"Platform '{platform_name}' added successfully."

def add_cookie_platform(platform_name, price):
    cookie_platform_name = f"Cookie: {platform_name}"
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (cookie_platform_name,))
    if c.fetchone():
        c.close()
        conn.close()
        return f"Platform '{cookie_platform_name}' already exists."
    c.execute("INSERT INTO platforms (platform_name, stock, price) VALUES (?, ?, ?)",
              (cookie_platform_name, "[]", price))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM", f"[PLATFORM] {config.OWNERS[0]} added Cookie Platform: {cookie_platform_name} with price {price} pts.")
    return f"Cookie Platform '{cookie_platform_name}' added successfully."

def remove_platform(platform_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM platforms WHERE platform_name = ?", (platform_name,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM", f"[PLATFORM] Removed Platform: {platform_name}.")
    return f"Platform '{platform_name}' removed successfully."

def rename_platform(old_name, new_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (new_name,))
    if c.fetchone():
        c.close()
        conn.close()
        return f"Platform name '{new_name}' already exists. Choose a different name."
    c.execute("UPDATE platforms SET platform_name = ? WHERE platform_name = ?", (new_name, old_name))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM", f"[PLATFORM] Renamed Platform from '{old_name}' to '{new_name}'.")
    return f"Platform '{old_name}' renamed to '{new_name}' successfully."

def change_price(platform_name, new_price):
    conn = get_connection()
    c = conn.cursor()
    try:
        new_price_int = int(new_price)
    except ValueError:
        c.close()
        conn.close()
        return "Price must be a number."
    c.execute("UPDATE platforms SET price = ? WHERE platform_name = ?", (new_price_int, platform_name))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM", f"[PLATFORM] Changed Price for Platform '{platform_name}' to {new_price_int} pts.")
    return f"Price for platform '{platform_name}' changed to {new_price_int} pts successfully."

def get_platforms_list():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms")
    platforms = c.fetchall()
    c.close()
    conn.close()
    return [dict(p) for p in platforms]

def add_stock_to_platform(platform_name, accounts):
    conn = get_connection()
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
    log_event(telebot.TeleBot(config.TOKEN), "STOCK", f"[STOCK] Stock updated for Platform '{platform_name}'; added {len(accounts)} items.")
    return f"Stock updated with {len(accounts)} items."

def update_stock_for_platform(platform_name, stock):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE platforms SET stock = ? WHERE platform_name = ?", (json.dumps(stock), platform_name))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "STOCK", f"[STOCK] Platform '{platform_name}' stock updated to {len(stock)} items.")

def add_channel(channel_link):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (channel_link) VALUES (?)", (channel_link,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "CHANNEL", f"[CHANNEL] Added Channel: {channel_link}.")

def remove_channel(channel_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "CHANNEL", f"[CHANNEL] Removed Channel with ID: {channel_id}.")

def get_channels():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM channels")
    channels = c.fetchall()
    c.close()
    conn.close()
    return [dict(ch) for ch in channels]

def get_admins():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM admins")
    admins = c.fetchall()
    c.close()
    conn.close()
    return [dict(a) for a in admins]

def add_admin(user_id, username, role="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)", (user_id, username, role))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "ADMIN", f"[ADMIN] Added admin {username} ({user_id}) with role '{role}'.")
    try:
        bot_instance = telebot.TeleBot(config.TOKEN)
        bot_instance.send_message(user_id, f"Congratulations, you have been added as an admin.")
    except Exception as e:
        print(f"Error notifying new admin {user_id}: {e}")

def remove_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "ADMIN", f"[ADMIN] Removed admin {user_id}.")

def ban_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "ADMIN", f"[ADMIN] Banned admin {user_id}.")

def unban_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "ADMIN", f"[ADMIN] Unbanned admin {user_id}.")

def get_all_users():
    return get_all_users()  # Assuming get_all_users() is imported from db

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    bot.edit_message_text("User Management\nSelect a user to manage:", 
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=markup)

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
    try:
        bot.edit_message_text(text, 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, 
                              reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def handle_user_ban_action(bot, call, user_id, action):
    if action == "ban":
        ban_user(user_id)
        result_text = f"User {user_id} has been banned."
        log_event(bot, "BAN", f"[BAN] {call.from_user.username or call.from_user.first_name} ({call.from_user.id}) banned user {user_id}.", user=call.from_user)
    elif action == "unban":
        unban_user(user_id)
        result_text = f"User {user_id} has been unbanned."
        log_event(bot, "UNBAN", f"[UNBAN] {call.from_user.username or call.from_user.first_name} ({call.from_user.id}) unbanned user {user_id}.", user=call.from_user)
    else:
        result_text = "Invalid action."
    bot.answer_callback_query(call.id, result_text)
    handle_user_management_detail(bot, call, user_id)

def admin_callback_handler(bot, call):
    data = call.data
    if not (str(call.from_user.id) in config.OWNERS or is_admin(call.from_user)):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_platform_add":
        # Show inline keyboard to choose platform type
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Account Platform", callback_data="admin_platform_add_account"),
            types.InlineKeyboardButton("Cookie Platform", callback_data="admin_platform_add_cookie")
        )
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
        bot.edit_message_text("Select platform type to add:", chat_id=call.message.chat.id,
                                message_id=call.message.message_id, reply_markup=markup)
    elif data == "admin_platform_add_account":
        handle_admin_platform_add(bot, call)
    elif data == "admin_platform_add_cookie":
        handle_admin_platform_add_cookie(bot, call)
    elif data == "admin_platform_remove":
        handle_admin_platform_remove(bot, call)
    elif data.startswith("admin_platform_rm_"):
        platform_name = data.split("admin_platform_rm_")[1]
        handle_admin_platform_rm(bot, call, platform_name)
    elif data.startswith("admin_platform_rename_"):
        old_name = data.split("admin_platform_rename_")[1]
        msg = bot.send_message(call.message.chat.id, f"Enter new name for platform '{old_name}':")
        bot.register_next_step_handler(msg, process_platform_rename, bot, old_name)
    elif data == "admin_platform_rename":
        handle_admin_platform_rename(bot, call)
    elif data.startswith("admin_platform_cp_"):
        platform_name = data.split("admin_platform_cp_")[1]
        msg = bot.send_message(call.message.chat.id, f"Enter new price for platform '{platform_name}':")
        bot.register_next_step_handler(msg, process_platform_changeprice, bot, platform_name)
    elif data == "admin_platform_changeprice":
        handle_admin_platform_changeprice(bot, call)
    elif data == "admin_stock":
        bot.send_message(call.message.chat.id, "Stock management is not implemented yet.")
    elif data == "admin_channel":
        bot.send_message(call.message.chat.id, "Channel management is not implemented yet.")
    elif data.startswith("admin_manage"):
        handle_admin_manage(bot, call)
    elif data.startswith("admin_list"):
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
    elif data == "back_admin":
        send_admin_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")

def handle_admin_platform(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="admin_platform_remove")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Rename Platform", callback_data="admin_platform_rename"),
        types.InlineKeyboardButton("💲 Change Price", callback_data="admin_platform_changeprice")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    try:
        bot.edit_message_text("Platform Management Options:", chat_id=call.message.chat.id, 
                                message_id=call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, "Platform Management Options:", reply_markup=markup)

def handle_admin_platform_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Account Platform):")
    bot.register_next_step_handler(msg, process_platform_add_account, bot)

def process_platform_add_account(bot, message):
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for platform '{platform_name}':")
    bot.register_next_step_handler(msg, process_platform_price, bot, platform_name)

def process_platform_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return
    response = add_platform(platform_name, price)
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_platform_add_cookie(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Cookie Platform):")
    bot.register_next_step_handler(msg, process_platform_add_cookie, bot)

def process_platform_add_cookie(bot, message):
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for cookie platform '{platform_name}':")
    bot.register_next_step_handler(msg, process_cookie_platform_price, bot, platform_name)

def process_cookie_platform_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return
    response = add_cookie_platform(platform_name, price)
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_platform_remove(bot, call):
    platforms = get_platforms_list()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms to remove.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_rm_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_platform_rm(bot, call, platform_name):
    response = remove_platform(platform_name)
    bot.answer_callback_query(call.id, response)
    handle_admin_platform(bot, call)

def handle_admin_platform_rename(bot, call):
    platforms = get_platforms_list()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_rename_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to rename:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def process_platform_rename(bot, message, old_name):
    new_name = message.text.strip()
    response = rename_platform(old_name, new_name)
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_platform_changeprice(bot, call):
    platforms = get_platforms_list()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        price = plat.get("price")
        btn_text = f"{plat_name} (Current: {price} pts)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"admin_platform_cp_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to change its price:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def process_platform_changeprice(bot, message, platform_name):
    new_price = message.text.strip()
    response = change_price(platform_name, new_price)
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    bot.edit_message_text("Admin Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_list(bot, call):
    admins = get_admins()
    if not admins:
        text = "No admins found."
    else:
        text = "Admins:\n"
        for admin in admins:
            text += f"• UserID: {admin.get('user_id')}, Username: {admin.get('username')}, Role: {admin.get('role')}, Banned: {admin.get('banned')}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id)

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the admin UserID to ban/unban:")
    bot.register_next_step_handler(msg, process_admin_ban_unban, bot)

def process_admin_ban_unban(bot, message):
    user_id = message.text.strip()
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
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the admin UserID to remove:")
    bot.register_next_step_handler(msg, process_admin_remove, bot)

def process_admin_remove(bot, message):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"Admin {user_id} removed."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the UserID and Username (separated by space) to add as admin (private chat only):")
    bot.register_next_step_handler(msg, process_admin_add, bot)

def process_admin_add(bot, message):
    if message.chat.type != "private":
        bot.send_message(message.chat.id, "Please use this command in a private chat.")
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        response = "Please provide both UserID and Username."
    else:
        user_id, username = parts[0], " ".join(parts[1:])
        add_admin(user_id, username, role="admin")
        response = f"Admin {user_id} added with username {username}."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    bot.edit_message_text("User Management\nSelect a user to manage:", 
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=markup)

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
    try:
        bot.edit_message_text(text, 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, 
                              reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def handle_user_ban_action(bot, call, user_id, action):
    if action == "ban":
        ban_user(user_id)
        result_text = f"User {user_id} has been banned."
        log_event(bot, "BAN", f"[BAN] {call.from_user.username or call.from_user.first_name} ({call.from_user.id}) banned user {user_id}.", user=call.from_user)
    elif action == "unban":
        unban_user(user_id)
        result_text = f"User {user_id} has been unbanned."
        log_event(bot, "UNBAN", f"[UNBAN] {call.from_user.username or call.from_user.first_name} ({call.from_user.id}) unbanned user {user_id}.", user=call.from_user)
    else:
        result_text = "Invalid action."
    bot.answer_callback_query(call.id, result_text)
    handle_user_management_detail(bot, call, user_id)

def admin_callback_handler(bot, call):
    data = call.data
    if not (str(call.from_user.id) in config.OWNERS or is_admin(call.from_user)):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_platform_add":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Account Platform", callback_data="admin_platform_add_account"),
            types.InlineKeyboardButton("Cookie Platform", callback_data="admin_platform_add_cookie")
        )
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
        bot.edit_message_text("Select platform type to add:", chat_id=call.message.chat.id,
                                message_id=call.message.message_id, reply_markup=markup)
    elif data == "admin_platform_add_account":
        handle_admin_platform_add(bot, call)
    elif data == "admin_platform_add_cookie":
        handle_admin_platform_add_cookie(bot, call)
    elif data == "admin_platform_remove":
        handle_admin_platform_remove(bot, call)
    elif data.startswith("admin_platform_rm_"):
        platform_name = data.split("admin_platform_rm_")[1]
        handle_admin_platform_rm(bot, call, platform_name)
    elif data.startswith("admin_platform_rename_"):
        old_name = data.split("admin_platform_rename_")[1]
        msg = bot.send_message(call.message.chat.id, f"Enter new name for platform '{old_name}':")
        bot.register_next_step_handler(msg, process_platform_rename, bot, old_name)
    elif data == "admin_platform_rename":
        handle_admin_platform_rename(bot, call)
    elif data.startswith("admin_platform_cp_"):
        platform_name = data.split("admin_platform_cp_")[1]
        msg = bot.send_message(call.message.chat.id, f"Enter new price for platform '{platform_name}':")
        bot.register_next_step_handler(msg, process_platform_changeprice, bot, platform_name)
    elif data == "admin_platform_changeprice":
        handle_admin_platform_changeprice(bot, call)
    elif data == "admin_stock":
        bot.send_message(call.message.chat.id, "Stock management is not implemented yet.")
    elif data == "admin_channel":
        bot.send_message(call.message.chat.id, "Channel management is not implemented yet.")
    elif data.startswith("admin_manage"):
        handle_admin_manage(bot, call)
    elif data.startswith("admin_list"):
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
    elif data == "back_admin":
        send_admin_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")
