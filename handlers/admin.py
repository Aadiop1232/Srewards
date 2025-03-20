import sqlite3
import json
import config
from datetime import datetime
from telebot import types
import telebot
from db import (
    get_user,
    ban_user,
    unban_user,
    update_user_points,
    get_account_claim_cost,
    get_admins,
    get_platforms,
    rename_platform,
    update_platform_price,
)
from handlers.logs import log_event

# IMPORTANT: If you encounter an error such as "table platforms has no column named platform_type",
# it means your existing DB file was created before adding the new column.
# To fix this, run a migration (for example, using the sqlite3 command-line):
#   ALTER TABLE platforms ADD COLUMN platform_type TEXT DEFAULT 'account';
# Or delete/reinitialize your DB if possible.

# ----------------- ADMIN CHECK -----------------

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

# ----------------- LEND POINTS -----------------

def lend_points(admin_id, user_id, points, custom_message=None):
    user = get_user(user_id)
    if not user:
        return f"User '{user_id}' not found."
    new_balance = user["points"] + points
    update_user_points(user_id, new_balance)
    log_event(telebot.TeleBot(config.TOKEN), "lend", f"Admin {admin_id} lent {points} points to user {user_id}.")
    bot_instance = telebot.TeleBot(config.TOKEN)
    msg = custom_message if custom_message else f"You have been lent {points} points. Your new balance is {new_balance} points."
    try:
        bot_instance.send_message(user_id, msg)
    except Exception as e:
        print(f"Error sending message to user {user_id}: {e}")
    return f"{points} points have been added to user {user_id}. New balance: {new_balance} points."

# ----------------- CONFIGURATION UPDATES -----------------

def update_account_claim_cost(cost):
    from db import set_config_value
    set_config_value("account_claim_cost", cost)
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Account claim cost updated to {cost} pts.")

def update_referral_bonus(bonus):
    from db import set_config_value
    set_config_value("referral_bonus", bonus)
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Referral bonus updated to {bonus} pts.")

# ----------------- KEY GENERATION AND ADDITION -----------------

def generate_normal_key():
    import random, string
    return "NKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_premium_key():
    import random, string
    return "PKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def add_key(key_str, key_type, points):
    from db import add_key as db_add_key  # Assumes your db.py contains an add_key() function.
    db_add_key(key_str, key_type, points)
    log_event(telebot.TeleBot(config.TOKEN), "key", f"Key {key_str} ({key_type}) added with {points} pts.")

# ----------------- PLATFORM MANAGEMENT -----------------

def add_platform(platform_name, price, platform_type="account"):
    """
    Add a new platform with a custom price and type.
    """
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    if c.fetchone():
        c.close()
        conn.close()
        return f"Platform '{platform_name}' already exists."
    c.execute(
        "INSERT INTO platforms (platform_name, stock, price, platform_type) VALUES (?, ?, ?, ?)", 
        (platform_name, "[]", price, platform_type)
    )
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "platform", 
              f"Platform '{platform_name}' added with price {price} pts. Type: {platform_type}.")
    return None

def remove_platform(platform_name):
    conn = __import__('db').get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM platforms WHERE platform_name = ?", (platform_name,))
    conn.commit()
    c.close()
    conn.close()
    log_event(telebot.TeleBot(config.TOKEN), "platform", f"Platform '{platform_name}' removed.")

def handle_admin_platform(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="admin_platform_remove"),
        types.InlineKeyboardButton("✏️ Rename Platform", callback_data="admin_platform_rename"),
        types.InlineKeyboardButton("💲 Change Price", callback_data="admin_platform_change_price"),
        types.InlineKeyboardButton("📋 Platform List", callback_data="admin_platform_list")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    try:
        bot.edit_message_text("Platform Management Options:", 
                              chat_id=call.message.chat.id, 
                              message_id=call.message.message_id, 
                              reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, "Platform Management Options:", reply_markup=markup)

# ---- ADD PLATFORM FLOW (Sub-menu for Account vs Cookie) ----

def handle_admin_platform_add(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Account Platform", callback_data="admin_platform_add_account"),
        types.InlineKeyboardButton("Cookie Platform", callback_data="admin_platform_add_cookie")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    try:
        bot.edit_message_text("Select platform type to add:", 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id, 
                              reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, "Select platform type to add:", reply_markup=markup)

def process_account_platform_name(bot, message):
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for account platform '{platform_name}':")
    bot.register_next_step_handler(msg, lambda m: process_account_platform_price(bot, m, platform_name))

def process_account_platform_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return
    error = add_platform(platform_name, price, platform_type="account")
    response = error if error else f"Account Platform '{platform_name}' added successfully with price {price} pts."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def process_cookie_platform_name(bot, message):
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for cookie platform '{platform_name}':")
    bot.register_next_step_handler(msg, lambda m: process_cookie_platform_price(bot, m, platform_name))

def process_cookie_platform_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return
    error = add_platform(platform_name, price, platform_type="cookie")
    response = error if error else f"Cookie Platform '{platform_name}' added successfully with price {price} pts."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

# ---- Rename Platform ----

def handle_admin_platform_rename(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_rename_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to rename:", 
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id, 
                          reply_markup=markup)

def process_platform_rename(bot, message, old_name):
    new_name = message.text.strip()
    rename_platform(old_name, new_name)
    bot.send_message(message.chat.id, f"Platform '{old_name}' renamed to '{new_name}'.")
    send_admin_menu(bot, message)

# ---- Change Price ----

def handle_admin_platform_change_price(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_change_price_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
    bot.edit_message_text("Select a platform to change price:", 
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id, 
                          reply_markup=markup)

def process_platform_change_price(bot, message, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return
    update_platform_price(platform_name, price)
    bot.send_message(message.chat.id, f"Platform '{platform_name}' price updated to {price} pts.")
    send_admin_menu(bot, message)

# ---- Platform List ----

def handle_admin_platform_list(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return
    text = "Platforms:\n"
    for plat in platforms:
        plat_name = plat.get("platform_name")
        stock = json.loads(plat.get("stock") or "[]")
        price = plat.get("price")
        p_type = plat.get("platform_type", "account")
        text += f"• {plat_name} | Type: {p_type} | Stock: {len(stock)} | Price: {price} pts\n"
    text += "\n🔙 /back to return."
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id)

# ----------------- STOCK MANAGEMENT -----------------

def handle_admin_stock(bot, call):
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available. Add one first.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_stock_detail_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("Select a platform to manage stock:", 
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id, 
                          reply_markup=markup)

def handle_admin_stock_detail(bot, call, platform_name):
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return
    platform = dict(platform)  # Convert row to dictionary
    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"]
    p_type = platform.get("platform_type", "account")
    stock_type = "Cookie file" if p_type == "cookie" else "Login pass"
    text = (f"Platform Name: {platform_name}\n"
            f"Type: {p_type}\n"
            f"Stock Type: {stock_type}\n"
            f"Accounts Available: {len(stock)}\n"
            f"Price: {price} pts")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Add Stock", callback_data=f"admin_stock_add_{platform_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_stock"))
    bot.edit_message_text(text, 
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id, 
                          reply_markup=markup)


def handle_admin_stock_add(bot, call, platform_name):
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return
    platform = dict(platform)  # Convert sqlite3.Row to dictionary
    p_type = platform.get("platform_type", "account")
    if p_type == "account":
        msg = bot.send_message(call.message.chat.id, f"Please send the stock text for account platform '{platform_name}':")
        bot.register_next_step_handler(msg, lambda m: process_stock_upload_admin(bot, m, platform_name, p_type))
    elif p_type == "cookie":
        msg = bot.send_message(call.message.chat.id, f"Please send a TXT file or ZIP file for cookie platform '{platform_name}':")
        bot.register_next_step_handler(msg, lambda m: process_stock_upload_admin(bot, m, platform_name, p_type))


def process_stock_upload_admin(bot, message, platform_name, platform_type, retries=3):
    if platform_type == "account":
        if message.content_type == "document":
            for attempt in range(retries):
                try:
                    file_info = bot.get_file(message.document.file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    try:
                        data = downloaded_file.decode('utf-8')
                    except UnicodeDecodeError:
                        data = downloaded_file.decode('latin-1', errors='replace')
                    break
                except Exception as e:
                    if attempt < retries - 1:
                        import time
                        time.sleep(2)
                        continue
                    else:
                        bot.send_message(message.chat.id, f"Error downloading file: {e}")
                        return
        else:
            data = message.text.strip()
        accounts = [line.strip() for line in data.splitlines() if line.strip()]
        from db import update_stock_for_platform
        update_stock_for_platform(platform_name, accounts)
        bot.send_message(message.chat.id, f"Stock for '{platform_name}' updated with {len(accounts)} accounts.")
        send_admin_menu(bot, message)
    elif platform_type == "cookie":
        if message.content_type != "document":
            bot.send_message(message.chat.id, "Please send a TXT or ZIP file.")
            return
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        import io
        from zipfile import ZipFile, BadZipFile
        filename = message.document.file_name.lower()
        new_stock = []
        if filename.endswith(".txt"):
            try:
                content = downloaded_file.decode('utf-8')
            except Exception:
                content = downloaded_file.decode('latin-1', errors='replace')
            new_stock.append({"type": "cookie", "content": content})
        elif filename.endswith(".zip"):
            try:
                zip_file = ZipFile(io.BytesIO(downloaded_file))
                for file in zip_file.namelist():
                    if file.lower().endswith(".txt"):
                        with zip_file.open(file) as f:
                            try:
                                content = f.read().decode('utf-8')
                            except Exception:
                                content = f.read().decode('latin-1', errors='replace')
                            new_stock.append({"type": "cookie", "content": content})
            except BadZipFile as e:
                bot.send_message(message.chat.id, f"Invalid ZIP file: {e}")
                return
        else:
            bot.send_message(message.chat.id, "Unsupported file type. Please send a TXT or ZIP file.")
            return
        import json
        conn = __import__('db').get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT stock FROM platforms WHERE platform_name = ?", (platform_name,))
        row = c.fetchone()
        current_stock = json.loads(row["stock"]) if row and row["stock"] else []
        current_stock.extend(new_stock)
        c.execute("UPDATE platforms SET stock = ? WHERE platform_name = ?", (json.dumps(current_stock), platform_name))
        conn.commit()
        c.close()
        conn.close()
        bot.send_message(message.chat.id, f"Cookie stock updated. {len(new_stock)} items added.")
        send_admin_menu(bot, message)

# ----------------- CHANNEL MANAGEMENT -----------------

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

def handle_admin_channel(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Channel", callback_data="admin_channel_add"),
        types.InlineKeyboardButton("➖ Remove Channel", callback_data="admin_channel_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("Channel Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the channel link to add:")
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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_channel"))
    bot.edit_message_text("Select a channel to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "Channel removed.")
    handle_admin_channel(bot, call)

# ----------------- ADMIN MANAGEMENT (User/Admin Lists) -----------------

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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
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
    bot.register_next_step_handler(msg, lambda m: process_admin_ban_unban(bot, m))

def process_admin_ban_unban(bot, message):
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
            unban_user(user_id)
            response = f"Admin {user_id} has been unbanned."
        else:
            ban_user(user_id)
            response = f"Admin {user_id} has been banned."
    c.close()
    conn.close()
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the admin UserID to remove:")
    bot.register_next_step_handler(msg, lambda m: process_admin_remove(bot, m))

def process_admin_remove(bot, message):
    user_id = message.text.strip()
    from db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()
    response = f"Admin {user_id} removed."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

def handle_admin_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "Please send the UserID and Username (separated by space) to add as admin:")
    bot.register_next_step_handler(msg, lambda m: process_admin_add(bot, m))

def process_admin_add(bot, message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        response = "Please provide both UserID and Username."
    else:
        user_id, username = parts[0], " ".join(parts[1:])
        from db import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)", (user_id, username, "admin"))
        conn.commit()
        c.close()
        conn.close()
        log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' ({username}) added with role 'admin'.")
        try:
            bot_instance = telebot.TeleBot(config.TOKEN)
            bot_instance.send_message(user_id, f"Congratulations, you have been added as an admin.")
        except Exception as e:
            print(f"Error notifying new admin {user_id}: {e}")
        response = f"Admin {user_id} added with username {username}."
    bot.send_message(message.chat.id, response)
    send_admin_menu(bot, message)

# ----------------- USER MANAGEMENT (Admin Panel) -----------------

def handle_user_management(bot, call):
    from db import get_connection
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    # Convert each row to a dictionary so .get() works
    users = [dict(u) for u in c.fetchall()]
    c.close()
    conn.close()
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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("User Management\nSelect a user to manage:", 
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=markup)

def handle_user_management_detail(bot, call, user_id):
    user = get_user(user_id)  # get_user returns a dictionary
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return
    status = "Banned" if user.get("banned", 0) else "Active"
    text = (f"User Management\n\n"
            f"User ID: {user.get('telegram_id')}\n"
            f"Username: {user.get('username')}\n"
            f"Join Date: {user.get('join_date')}\n"
            f"Balance: {user.get('points')} pts\n"
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
        log_event(bot, "ban", f"User {user_id} banned by admin {call.from_user.id}.", user=call.from_user)
    elif action == "unban":
        unban_user(user_id)
        result_text = f"User {user_id} has been unbanned."
        log_event(bot, "unban", f"User {user_id} unbanned by admin {call.from_user.id}.", user=call.from_user)
    else:
        result_text = "Invalid action."
    bot.answer_callback_query(call.id, result_text)
    handle_user_management_detail(bot, call, user_id)

# ----------------- ADMIN CALLBACK HANDLER -----------------

def admin_callback_handler(bot, call):
    data = call.data
    if not (str(call.from_user.id) in config.OWNERS or is_admin(call.from_user)):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_platform_add":
        handle_admin_platform_add(bot, call)
    elif data == "admin_platform_add_account":
        msg = bot.send_message(call.message.chat.id, "Please send the account platform name:")
        bot.register_next_step_handler(msg, lambda m: process_account_platform_name(bot, m))
    elif data == "admin_platform_add_cookie":
        msg = bot.send_message(call.message.chat.id, "Please send the cookie platform name:")
        bot.register_next_step_handler(msg, lambda m: process_cookie_platform_name(bot, m))
    elif data == "admin_platform_remove":
        platforms = get_platforms()
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
    elif data.startswith("admin_platform_rm_"):
        platform_name = data.split("admin_platform_rm_")[1]
        remove_platform(platform_name)
        bot.answer_callback_query(call.id, f"Platform '{platform_name}' removed.")
        handle_admin_platform(bot, call)
    elif data == "admin_platform_rename":
        handle_admin_platform_rename(bot, call)
    elif data.startswith("admin_platform_rename_"):
        old_name = data.split("admin_platform_rename_")[1]
        msg = bot.send_message(call.message.chat.id, f"Send new name for platform '{old_name}':")
        bot.register_next_step_handler(msg, lambda m: process_platform_rename(bot, m, old_name))
    elif data == "admin_platform_change_price":
        handle_admin_platform_change_price(bot, call)
    elif data.startswith("admin_platform_change_price_"):
        platform_name = data.split("admin_platform_change_price_")[1]
        msg = bot.send_message(call.message.chat.id, f"Send new price for platform '{platform_name}':")
        bot.register_next_step_handler(msg, lambda m: process_platform_change_price(bot, m, platform_name))
    elif data == "admin_platform_list":
        handle_admin_platform_list(bot, call)
    elif data == "admin_stock":
        handle_admin_stock(bot, call)
    elif data.startswith("admin_stock_detail_"):
        platform_name = data.split("admin_stock_detail_")[1]
        handle_admin_stock_detail(bot, call, platform_name)
    elif data.startswith("admin_stock_add_"):
        platform_name = data.split("admin_stock_add_")[1]
        handle_admin_stock_add(bot, call, platform_name)
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
        send_main_menu(bot, call)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")

# ----------------- SEND ADMIN MENU -----------------

def send_admin_menu(bot, update):
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
        if hasattr(update, "message") and update.message:
            bot.edit_message_text("🛠 Admin Panel", chat_id=update.message.chat.id,
                                  message_id=update.message.message_id, reply_markup=markup)
        else:
            bot.send_message(update.chat.id, "🛠 Admin Panel", reply_markup=markup)
    except Exception:
        bot.send_message(update.chat.id, "🛠 Admin Panel", reply_markup=markup)
