# user_mgmt.py

import telebot
import config
from telebot import types
from db import get_connection, get_all_users, get_user
from handlers.logs import log_event
from handlers.admin import is_admin

####################################
# Admin Management
####################################

def handle_admin_manage(bot, call):
    """
    Called when user taps "Admin Mgmt".
    Shows the admin management menu (list, ban/unban, remove, add).
    """
    bot.answer_callback_query(call.id, "Admin management loading...")

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

    bot.edit_message_text(
        "Admin Management",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

def handle_admin_list(bot, call):
    """
    Displays a list of all admins.
    """
    bot.answer_callback_query(call.id, "Listing admins...")
    from db import get_admins

    admins = get_admins()
    if not admins:
        text = "No admins found."
    else:
        text = "Admins:\n"
        for admin in admins:
            text += (f"• {admin.get('username')} ({admin.get('user_id')}), "
                     f"Role: {admin.get('role')}, Banned: {admin.get('banned')}\n")

    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

def handle_admin_ban_unban(bot, call):
    """
    Initiates the ban/unban flow for an admin by asking for the admin's user ID.
    """
    bot.answer_callback_query(call.id, "Ban/unban admin...")
    msg = bot.send_message(call.message.chat.id, "Please send the admin UserID to ban/unban:")
    bot.register_next_step_handler(msg, process_admin_ban_unban, bot)

def process_admin_ban_unban(message, bot):
    user_id = message.text.strip()
    conn = get_connection()
    conn.row_factory = None
    c = conn.cursor()

    c.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    admin_doc = c.fetchone()
    if not admin_doc:
        response = "Admin not found."
    else:
        # 'banned' is the 4th column in admins table (0-based index 3)
        if admin_doc[3] == 1:
            unban_admin(user_id)
            response = f"Admin {user_id} has been unbanned."
        else:
            ban_admin(user_id)
            response = f"Admin {user_id} has been banned."

    c.close()
    conn.close()

    bot.send_message(message.chat.id, response)
    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def ban_admin(user_id):
    """
    Sets banned=1 for this user in the admins table.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()

def unban_admin(user_id):
    """
    Sets banned=0 for this user in the admins table.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE admins SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()

def handle_admin_remove(bot, call):
    """
    Asks for which admin ID to remove entirely from the admins table.
    """
    bot.answer_callback_query(call.id, "Removing admin...")
    msg = bot.send_message(call.message.chat.id, "Please send the admin UserID to remove:")
    bot.register_next_step_handler(msg, process_admin_remove, bot)

def process_admin_remove(message, bot):
    user_id = message.text.strip()
    remove_admin(user_id)
    response = f"Admin {user_id} removed."
    bot.send_message(message.chat.id, response)

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def remove_admin(user_id):
    """
    Deletes from admins table where user_id matches.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    c.close()
    conn.close()

    log_event(telebot.TeleBot(config.TOKEN), "ADMIN", f"[ADMIN] Removed admin {user_id}.")

def handle_admin_add(bot, call):
    """
    Asks for a new admin's user ID & username, then adds them to the admins table.
    """
    bot.answer_callback_query(call.id, "Adding new admin...")
    msg = bot.send_message(
        call.message.chat.id,
        "Please send the UserID and Username (space-separated) to add as admin (private chat only):"
    )
    bot.register_next_step_handler(msg, process_admin_add, bot)

def process_admin_add(message, bot):
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
    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def add_admin(user_id, username, role="admin"):
    """
    Replaces or inserts a record in the admins table with banned=0.
    Also sends a message to that user ID to notify them.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO admins (user_id, username, role, banned) VALUES (?, ?, ?, 0)",
              (user_id, username, role))
    conn.commit()
    c.close()
    conn.close()

    log_event(telebot.TeleBot(config.TOKEN), "ADMIN",
              f"[ADMIN] Added admin {username} ({user_id}) with role '{role}'.")

    try:
        bot_instance = telebot.TeleBot(config.TOKEN)
        bot_instance.send_message(user_id, "Congratulations, you have been added as an admin.")
    except Exception as e:
        print(f"Error notifying new admin {user_id}: {e}")

####################################
# Normal User Management
####################################

def handle_user_management(bot, call):
    """
    Shows a list of all users (from the 'users' table), 
    so an admin can manage each user (ban/unban).
    """
    bot.answer_callback_query(call.id, "Loading user management...")
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

    bot.edit_message_text(
        "User Management\nSelect a user to manage:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

def handle_user_management_detail(bot, call, user_id):
    """
    Displays details for one user, with a ban/unban button.
    """
    bot.answer_callback_query(call.id, "User management detail...")
    user = get_user(user_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return

    status = "Banned" if user.get("banned", 0) else "Active"
    text = (
        f"User Management\n\n"
        f"User ID: {user.get('telegram_id')}\n"
        f"Username: {user.get('username')}\n"
        f"Join Date: {user.get('join_date')}\n"
        f"Balance: {user.get('points')} points\n"
        f"Total Referrals: {user.get('referrals')}\n"
        f"Status: {status}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    if user.get("banned", 0):
        markup.add(types.InlineKeyboardButton("Unban", callback_data=f"admin_user_{user_id}_unban"))
    else:
        markup.add(types.InlineKeyboardButton("Ban", callback_data=f"admin_user_{user_id}_ban"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_users"))

    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def handle_user_ban_action(bot, call, user_id, action):
    """
    Bans or unbans a normal user from the 'users' table.
    """
    from db import ban_user, unban_user
    if action == "ban":
        ban_user(user_id)
        result_text = f"User {user_id} has been banned."
        log_event(bot, "BAN", f"[BAN] Banned user {user_id}.", user=call.from_user)
    elif action == "unban":
        unban_user(user_id)
        result_text = f"User {user_id} has been unbanned."
        log_event(bot, "UNBAN", f"[UNBAN] Unbanned user {user_id}.", user=call.from_user)
    else:
        result_text = "Invalid action."

    bot.answer_callback_query(call.id, result_text)
    handle_user_management_detail(bot, call, user_id)
