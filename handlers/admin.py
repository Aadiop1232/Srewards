# admin.py

import config
import telebot
from telebot import types
from db import get_admins
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

def lend_points(admin_id, user_id, points, custom_message=None):
    from db import get_user, update_user_points

    user = get_user(user_id)
    if not user:
        return f"User '{user_id}' not found."

    new_balance = user["points"] + points
    update_user_points(user_id, new_balance)

    log_event(
        telebot.TeleBot(config.TOKEN),
        "LEND",
        f"[LEND] Admin {admin_id} lent {points} points to user {user_id}."
    )

    bot_instance = telebot.TeleBot(config.TOKEN)
    if custom_message:
        msg = (
            f"{custom_message}\n"
            f"Points added: {points}\n"
            f"New balance: {new_balance} points."
        )
    else:
        msg = (
            f"You have been lent {points} points. "
            f"Your new balance is {new_balance} points."
        )

    try:
        bot_instance.send_message(user_id, msg)
    except Exception as e:
        print(f"Error sending message to user {user_id}: {e}")

    return msg

def generate_normal_key():
    import random, string
    return "NKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_premium_key():
    import random, string
    return "PKEY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def add_key(key_str, key_type, points):
    from db import get_connection
    from datetime import datetime
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO keys (\"key\", type, points, claimed, claimed_by, timestamp) VALUES (?, ?, ?, 0, NULL, ?)",
        (key_str, key_type, points, datetime.now())
    )
    conn.commit()
    c.close()
    conn.close()

def send_admin_menu(bot, update):
    if hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
    elif hasattr(update, "from_user") and update.from_user:
        chat_id = update.message.chat.id if hasattr(update, "message") and update.message else update.chat.id
        message_id = update.message.message_id if hasattr(update, "message") and update.message else None
    else:
        chat_id = update.chat.id
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
            bot.edit_message_text(
                "🛠 Admin Panel",
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, "🛠 Admin Panel", reply_markup=markup)
    except Exception:
        bot.send_message(chat_id, "🛠 Admin Panel", reply_markup=markup)

def admin_callback_handler(bot, call):
    # DEBUG print to confirm we got the callback
    print(f"[DEBUG admin_callback_handler] data='{call.data}' from_user_id={call.from_user.id}")

    data = call.data
    if not (str(call.from_user.id) in config.OWNERS or is_admin(call.from_user)):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return

    from handlers.stock_mgmt import (
        handle_platform_callback, handle_platform_add, handle_platform_add_cookie,
        handle_platform_remove, handle_platform_rm, handle_platform_rename,
        process_platform_rename, handle_platform_changeprice, process_platform_changeprice,
        handle_admin_stock, handle_stock_platform_choice
    )
    from handlers.user_mgmt import (
        handle_admin_manage, handle_admin_list, handle_admin_ban_unban,
        handle_admin_remove, handle_admin_add, handle_user_management,
        handle_user_management_detail, handle_user_ban_action
    )

    # ---- PLATFORM MGMT ----

    if data == "admin_platform":
        bot.answer_callback_query(call.id, "Loading platform management...")
        handle_platform_callback(bot, call)

    elif data == "platform_add":
        bot.answer_callback_query(call.id, "Adding platform...")
        handle_platform_add(bot, call)

    elif data == "platform_add_cookie":
        bot.answer_callback_query(call.id, "Adding cookie platform...")
        handle_platform_add_cookie(bot, call)

    elif data == "platform_remove":
        bot.answer_callback_query(call.id, "Removing platform...")
        handle_platform_remove(bot, call)

    elif data.startswith("platform_rm_"):
        bot.answer_callback_query(call.id, "Removing platform...")
        plat_name = data.replace("platform_rm_", "", 1)
        handle_platform_rm(bot, call, plat_name)

    elif data == "platform_rename":
        bot.answer_callback_query(call.id, "Renaming platform...")
        handle_platform_rename(bot, call)

    elif data.startswith("platform_rename_"):
        bot.answer_callback_query(call.id, "Renaming platform...")
        old_name = data.replace("platform_rename_", "", 1)
        msg = bot.send_message(call.message.chat.id, f"Enter new name for platform '{old_name}':")
        bot.register_next_step_handler(msg, process_platform_rename, bot, old_name)

    elif data == "platform_changeprice":
        bot.answer_callback_query(call.id, "Changing platform price...")
        handle_platform_changeprice(bot, call)

    elif data.startswith("platform_cp_"):
        bot.answer_callback_query(call.id, "Changing platform price...")
        plat_name = data.replace("platform_cp_", "", 1)
        msg = bot.send_message(call.message.chat.id, f"Enter new price for platform '{plat_name}':")
        bot.register_next_step_handler(msg, process_platform_changeprice, bot, plat_name)

    elif data == "platform_back":
        bot.answer_callback_query(call.id, "Going back to platform menu...")
        handle_platform_callback(bot, call)

    # ---- STOCK MGMT ----

    elif data == "admin_stock":
        bot.answer_callback_query(call.id, "Loading stock mgmt...")
        handle_admin_stock(bot, call)

    elif data.startswith("stock_manage_"):
        bot.answer_callback_query(call.id, "Updating stock for platform...")
        plat_name = data.replace("stock_manage_", "", 1)
        handle_stock_platform_choice(bot, call, plat_name)

    # ---- CHANNEL MGMT (Not Implemented) ----

    elif data == "admin_channel":
        bot.answer_callback_query(call.id, "Channel management is not implemented yet.")

    # ---- ADMIN MGMT ----

    elif data.startswith("admin_manage"):
        bot.answer_callback_query(call.id, "Admin management loading...")
        handle_admin_manage(bot, call)

    elif data.startswith("admin_list"):
        bot.answer_callback_query(call.id, "Listing admins...")
        handle_admin_list(bot, call)

    elif data == "admin_ban_unban":
        bot.answer_callback_query(call.id, "Ban/unban admin...")
        handle_admin_ban_unban(bot, call)

    elif data == "admin_remove":
        bot.answer_callback_query(call.id, "Removing admin...")
        handle_admin_remove(bot, call)

    elif data == "admin_add":
        bot.answer_callback_query(call.id, "Adding new admin...")
        handle_admin_add(bot, call)

    # ---- USER MGMT ----

    elif data == "admin_users":
        bot.answer_callback_query(call.id, "Loading user management...")
        handle_user_management(bot, call)

    elif data.startswith("admin_user_") and data.count("_") == 2:
        bot.answer_callback_query(call.id, "Loading user detail...")
        user_id = data.split("_")[2]
        handle_user_management_detail(bot, call, user_id)

    elif data.startswith("admin_user_") and data.count("_") == 3:
        bot.answer_callback_query(call.id, "Updating user ban/unban...")
        _, _, user_id, action = data.split("_", 3)
        handle_user_ban_action(bot, call, user_id, action)

    # ---- BACK / UNKNOWN ----

    elif data == "back_main":
        bot.answer_callback_query(call.id, "Returning to main menu...")
        from handlers.main_menu import send_main_menu
        send_admin_menu(bot, call.message)

    elif data == "back_admin":
        bot.answer_callback_query(call.id, "Returning to admin panel...")
        send_admin_menu(bot, call.message)

    else:
        bot.answer_callback_query(call.id, f"Unknown admin command: {data}")
