# admin.py

import config
import telebot
from telebot import types
from db import get_admins
from handlers.logs import log_event

def is_admin(user_or_id):
    """
    Checks if the given user (object or ID) is in OWNERS or the admins table.
    """
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

def send_admin_menu(bot, update):
    """
    Sends the main Admin Panel menu with Platform/Stock mgmt, 
    User mgmt, Admin mgmt, etc.
    """
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
    """
    Processes all callback_data that begins with 'admin'.
    Delegates to stock_mgmt or user_mgmt or other handlers as needed.
    """
    data = call.data
    # If not admin or owner, reject
    if not (str(call.from_user.id) in config.OWNERS or is_admin(call.from_user)):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return

    # Lazy import to avoid circular references
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

    if data == "admin_platform":
        # Go to platform mgmt
        bot.answer_callback_query(call.id, "Loading platform management...")
        handle_platform_callback(bot, call)

    elif data == "platform_add":
        handle_platform_add(bot, call)
    elif data == "platform_add_cookie":
        handle_platform_add_cookie(bot, call)
    elif data == "platform_remove":
        handle_platform_remove(bot, call)
    elif data.startswith("platform_rm_"):
        plat_name = data.replace("platform_rm_", "", 1)
        handle_platform_rm(bot, call, plat_name)
    elif data == "platform_rename":
        handle_platform_rename(bot, call)
    elif data.startswith("platform_rename_"):
        old_name = data.replace("platform_rename_", "", 1)
        msg = bot.send_message(call.message.chat.id, f"Enter new name for platform '{old_name}':")
        bot.register_next_step_handler(msg, process_platform_rename, bot, old_name)
    elif data == "platform_changeprice":
        handle_platform_changeprice(bot, call)
    elif data.startswith("platform_cp_"):
        plat_name = data.replace("platform_cp_", "", 1)
        msg = bot.send_message(call.message.chat.id, f"Enter new price for platform '{plat_name}':")
        bot.register_next_step_handler(msg, process_platform_changeprice, bot, plat_name)
    elif data == "platform_back":
        handle_platform_callback(bot, call)

    elif data == "admin_stock":
        bot.answer_callback_query(call.id, "Loading stock mgmt...")
        handle_admin_stock(bot, call)
    elif data.startswith("stock_manage_"):
        plat_name = data.replace("stock_manage_", "", 1)
        handle_stock_platform_choice(bot, call, plat_name)

    elif data == "admin_channel":
        # Not implemented, just respond
        bot.answer_callback_query(call.id, "Channel management is not implemented yet.")

    # Admin Management
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

    # User Management
    elif data == "admin_users":
        handle_user_management(bot, call)
    elif data.startswith("admin_user_") and data.count("_") == 2:
        user_id = data.split("_")[2]
        handle_user_management_detail(bot, call, user_id)
    elif data.startswith("admin_user_") and data.count("_") == 3:
        # e.g. "admin_user_123456_ban"
        _, _, user_id, action = data.split("_", 3)
        handle_user_ban_action(bot, call, user_id, action)

    elif data == "back_main":
        # Return to admin menu
        from handlers.main_menu import send_main_menu
        send_admin_menu(bot, call.message)

    elif data == "back_admin":
        # Also show the admin menu again
        send_admin_menu(bot, call.message)

    else:
        # Fallback
        bot.answer_callback_query(call.id, "Unknown admin command.")
