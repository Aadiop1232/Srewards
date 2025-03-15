# handlers/admin.py
import telebot
from telebot import types
import random, string, json
import config
from datetime import datetime

from db import (
    get_user,
    ban_user,
    unban_user,
    add_key,
    claim_key_in_db,
    update_user_points,
    add_referral,
    set_account_claim_cost,
    get_account_claim_cost,
    set_referral_bonus,
    get_referral_bonus,
    get_leaderboard,
    get_admin_dashboard
)
from db import db  # global MongoDB object

# Collections for platforms, channels, admins, and users
platforms_collection = db.platforms
channels_collection = db.channels
admins_collection = db.admins
users_collection = db.users

from handlers.logs import log_event

# -----------------------
# Platform Management Functions
# -----------------------

def add_platform(platform_name):
    if platforms_collection.find_one({"platform_name": platform_name}):
        return f"Platform '{platform_name}' already exists."
    # Insert platform with an empty stock list and a price field (default from config)
    platform = {
        "platform_name": platform_name,
        "stock": [],
        "price": get_account_claim_cost()
    }
    platforms_collection.insert_one(platform)
    # Log the event
    log_event(telebot.TeleBot(config.TOKEN), "platform", f"Platform '{platform_name}' added.")
    return None

def remove_platform(platform_name):
    platforms_collection.delete_one({"platform_name": platform_name})
    log_event(telebot.TeleBot(config.TOKEN), "platform", f"Platform '{platform_name}' removed.")

def get_platforms():
    return list(platforms_collection.find())

def add_stock_to_platform(platform_name, accounts):
    platform = platforms_collection.find_one({"platform_name": platform_name})
    if not platform:
        return f"Platform '{platform_name}' not found."
    current_stock = platform.get("stock", [])
    new_stock = current_stock + accounts
    platforms_collection.update_one(
        {"platform_name": platform_name},
        {"$set": {"stock": new_stock}}
    )
    log_event(telebot.TeleBot(config.TOKEN), "stock", f"Added {len(accounts)} accounts to platform '{platform_name}'.")
    return f"Stock updated with {len(accounts)} accounts."

def update_stock_for_platform(platform_name, stock):
    platforms_collection.update_one(
        {"platform_name": platform_name},
        {"$set": {"stock": stock}}
    )
    log_event(telebot.TeleBot(config.TOKEN), "stock", f"Platform '{platform_name}' stock updated to {len(stock)} accounts.")

# -----------------------
# Channel Management Functions
# -----------------------

def add_channel(channel_link):
    channels_collection.insert_one({"channel_link": channel_link})
    log_event(telebot.TeleBot(config.TOKEN), "channel", f"Channel '{channel_link}' added.")

def remove_channel(channel_id):
    channels_collection.delete_one({"_id": channel_id})
    log_event(telebot.TeleBot(config.TOKEN), "channel", f"Channel with ID '{channel_id}' removed.")

def get_channels():
    return list(channels_collection.find())

# -----------------------
# Admin Management Functions
# -----------------------

def get_admins():
    return list(admins_collection.find())

def add_admin(user_id, username, role="admin"):
    admins_collection.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "role": role, "banned": False}},
        upsert=True
    )
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' ({username}) added with role '{role}'.")

def remove_admin(user_id):
    admins_collection.delete_one({"user_id": user_id})
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' removed.")

def ban_admin(user_id):
    admins_collection.update_one(
        {"user_id": user_id},
        {"$set": {"banned": True}}
    )
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' banned.")

def unban_admin(user_id):
    admins_collection.update_one(
        {"user_id": user_id},
        {"$set": {"banned": False}}
    )
    log_event(telebot.TeleBot(config.TOKEN), "admin", f"Admin '{user_id}' unbanned.")

# -----------------------
# User Management Functions (For Admin Panel)
# -----------------------

def get_all_users():
    return list(users_collection.find())

# -----------------------
# Lending Points Function (Admin Command)
# -----------------------

def lend_points(admin_id, user_id, points):
    user = get_user(user_id)
    if not user:
        return f"User '{user_id}' not found."
    new_balance = user["points"] + points
    update_user_points(user_id, new_balance)
    log_event(telebot.TeleBot(config.TOKEN), "lend", f"Admin {admin_id} added {points} points to user {user_id}.")
    return f"{points} points have been added to user {user_id}. New balance: {new_balance} points."

# -----------------------
# Dynamic Configuration Commands (For Account Price and Referral Bonus)
# -----------------------

# (These helper functions are in db.py; commands are handled in main.py, but here we wrap them if needed)
def update_account_claim_cost(cost):
    set_account_claim_cost(cost)
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Account claim cost updated to {cost} points.")

def update_referral_bonus(bonus):
    set_referral_bonus(bonus)
    log_event(telebot.TeleBot(config.TOKEN), "config", f"Referral bonus updated to {bonus} points.")

# -----------------------
# Admin Panel Callback Handlers & Sub-Handlers
# -----------------------

def send_admin_menu(bot, update):
    if hasattr(update, "message"):
        chat_id = update.message.chat.id
        message_id = update.message.message_id
    elif hasattr(update, "data"):
        chat_id = update.message.chat.id
        message_id = update.message.message_id
    else:
        chat_id = update.chat.id
        message_id = update.message.message_id
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
        bot.edit_message_text("🛠 Admin Panel", chat_id=chat_id, message_id=message_id, reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, "🛠 Admin Panel", reply_markup=markup)

def handle_admin_platform(bot, call):
    platforms = get_platforms()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="admin_platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="admin_platform_remove")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("Platform Management", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_platform_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ Send the platform name to add:")
    bot.register_next_step_handler(msg, lambda m: process_platform_add(bot, m))

def process_platform_add(bot, message):
    platform_name = message.text.strip()
    error = add_platform(platform_name)
    if error:
        response = error
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
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"admin_platform_rm_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_platform"))
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
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("Select a platform to update stock:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_stock_platform(bot, call, platform_name):
    msg = bot.send_message(call.message.chat.id, f"✏️ Send the stock text for platform {platform_name} (attach a file or type text):")
    bot.register_next_step_handler(msg, process_stock_upload_admin, platform_name)

def process_stock_upload_admin(message, platform_name):
    bot_instance = telebot.TeleBot(config.TOKEN)
    if message.content_type == "document":
        try:
            file_info = bot_instance.get_file(message.document.file_id)
            downloaded_file = bot_instance.download_file(file_info.file_path)
            try:
                data = downloaded_file.decode('utf-8')
            except UnicodeDecodeError:
                data = downloaded_file.decode('latin-1', errors='replace')
        except Exception as e:
            bot_instance.send_message(message.chat.id, f"❌ Error downloading file: {e}")
            return
    else:
        data = message.text.strip()
    if "\n\n" in data:
        accounts = [block.strip() for block in data.split("\n\n") if block.strip()]
    else:
        accounts = [line.strip() for line in data.splitlines() if line.strip()]
    update_stock_for_platform(platform_name, accounts)
    bot_instance.send_message(message.chat.id,
                              f"✅ Stock for {platform_name} updated with {len(accounts)} accounts.")
    send_admin_menu(bot_instance, message)

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
    msg = bot.send_message(call.message.chat.id, "✏️ Send the channel link to add:")
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
        cid = str(channel.get("_id"))
        link = channel.get("channel_link")
        markup.add(types.InlineKeyboardButton(link, callback_data=f"admin_channel_rm_{cid}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_channel"))
    bot.edit_message_text("Select a channel to remove:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

def handle_admin_channel_rm(bot, call, channel_id):
    remove_channel(channel_id)
    bot.answer_callback_query(call.id, "Channel removed.")
    handle_admin_channel(bot, call)

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
        text = "👥 Admins:\n"
        for admin in admins:
            text += f"• UserID: {admin.get('user_id')}, Username: {admin.get('username')}, Role: {admin.get('role')}, Banned: {admin.get('banned')}\n"
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id)

def handle_admin_ban_unban(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ Send the admin UserID to ban/unban:")
    bot.register_next_step_handler(msg, process_admin_ban_unban)

def process_admin_ban_unban(message):
    user_id = message.text.strip()
    bot_instance = telebot.TeleBot(config.TOKEN)
    admin_doc = admins_collection.find_one({"user_id": user_id})
    if not admin_doc:
        response = "Admin not found."
    else:
        if admin_doc.get("banned", False):
            unban_admin(user_id)
            response = f"Admin {user_id} has been unbanned."
        else:
            ban_admin(user_id)
            response = f"Admin {user_id} has been banned."
    bot_instance.send_message(message.chat.id, response)
    send_admin_menu(bot_instance, message)

def handle_admin_remove(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ Send the admin UserID to remove:")
    bot.register_next_step_handler(msg, process_admin_remove)

def process_admin_remove(message):
    user_id = message.text.strip()
    bot_instance = telebot.TeleBot(config.TOKEN)
    remove_admin(user_id)
    response = f"Admin {user_id} removed."
    bot_instance.send_message(message.chat.id, response)
    send_admin_menu(bot_instance, message)

def handle_admin_add(bot, call):
    msg = bot.send_message(call.message.chat.id, "✏️ Send the UserID and Username (separated by space) to add as admin:")
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
# User Management (Admin Panel)
# -----------------------

def handle_user_management(bot, call):
    users = list(users_collection.find())
    if not users:
        bot.answer_callback_query(call.id, "No users found.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        uid = u.get("telegram_id")
        username = u.get("username")
        banned = u.get("banned", False)
        status = "Banned" if banned else "Active"
        btn_text = f"{username} ({uid}) - {status}"
        callback_data = f"admin_user_{uid}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.edit_message_text("User Management\nSelect a user to manage:", chat_id=call.message.chat.id,
                            message_id=call.message.message_id, reply_markup=markup)

def handle_user_management_detail(bot, call, user_id):
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return
    status = "Banned" if user.get("banned", False) else "Active"
    text = (f"User Management\n\n"
            f"User ID: {user.get('telegram_id')}\n"
            f"Username: {user.get('username')}\n"
            f"Join Date: {user.get('join_date')}\n"
            f"Balance: {user.get('points')} points\n"
            f"Total Referrals: {user.get('referrals')}\n"
            f"Status: {status}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    if user.get("banned", False):
        markup.add(types.InlineKeyboardButton("Unban", callback_data=f"admin_user_{user_id}_unban"))
    else:
        markup.add(types.InlineKeyboardButton("Ban", callback_data=f"admin_user_{user_id}_ban"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
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
# Lending Points Command (Admin)
# -----------------------

def handle_lend_command(bot, message):
    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /lend <user_id> <points>")
        return
    user_id = parts[1]
    try:
        points = int(parts[2])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    result = lend_points(message.from_user.id, user_id, points)
    bot.reply_to(message, result)

# -----------------------
# Dynamic Configuration Commands (For Account Price and Referral Bonus)
# Only owners can use these
# -----------------------

def handle_uprice_command(bot, message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /Uprice <points>")
        return
    try:
        price = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "Access denied.")
        return
    update_account_claim_cost(price)
    bot.reply_to(message, f"Account claim cost updated to {price} points.")
    
def handle_rpoints_command(bot, message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /Rpoints <points>")
        return
    try:
        bonus = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "Access denied.")
        return
    update_referral_bonus(bonus)
    bot.reply_to(message, f"Referral bonus updated to {bonus} points.")

# -----------------------
# Admin Callback Router
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
        # Format: admin_user_{user_id}
        user_id = data.split("_")[2]
        handle_user_management_detail(bot, call, user_id)
    elif data.startswith("admin_user_") and data.count("_") == 3:
        # Format: admin_user_{user_id}_ban or admin_user_{user_id}_unban
        parts = data.split("_")
        user_id = parts[2]
        action = parts[3]
        handle_user_ban_action(bot, call, user_id, action)
    elif data == "back_main":
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call)
    else:
        bot.answer_callback_query(call.id, "Unknown admin command.")
