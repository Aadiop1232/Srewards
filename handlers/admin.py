import telebot
from telebot import types
import sqlite3
import random
import json
import config

def get_db_connection():
    return sqlite3.connect(config.DATABASE)

###############################
# PLATFORM MANAGEMENT FUNCTIONS
###############################
def add_platform(platform_name):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO platforms (platform_name, stock) VALUES (?, ?)", (platform_name, json.dumps([])))
        conn.commit()
        conn.close()
        return None
    except Exception as e:
        print(f"Error adding platform: {e}")
        return str(e)

def remove_platform(platform_name):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM platforms WHERE platform_name=?", (platform_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error removing platform: {e}")
        return str(e)

def get_platforms():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT platform_name FROM platforms")
        rows = c.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error fetching platforms: {e}")
        return []

###############################
# USER MANAGEMENT FUNCTIONS
###############################
def handle_admin_users(bot, call):
    """
    Handle the user management section of the admin panel.
    This includes viewing all users, banning/unbanning users, etc.
    """
    users = get_users()  # Get all users
    markup = types.InlineKeyboardMarkup(row_width=2)
    if not users:
        bot.send_message(call.message.chat.id, "😢 No users found.")
        return
    for user in users:
        user_id, username, banned = user
        status = "Banned" if banned else "Active"
        markup.add(types.InlineKeyboardButton(f"{username} ({status})", callback_data=f"admin_user_{user_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    bot.edit_message_text("<b>👥 Admin Panel - User Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def get_users():
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("SELECT telegram_id, username, banned FROM users")
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"❌ Error fetching users: {e}")
        return []

def ban_user(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=1 WHERE telegram_id=?", (str(user_id),))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error banning user: {e}")

def unban_user(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=0 WHERE telegram_id=?", (str(user_id),))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error unbanning user: {e}")

###############################
# ADMIN MANAGEMENT FUNCTIONS
###############################

def is_owner(user_or_id):
    """ Check if the user is an owner """
    try:
        tid = str(user_or_id.id)
        uname = (user_or_id.username or "").lower()
    except AttributeError:
        tid = str(user_or_id)
        uname = ""
    owners = [str(x).lower() for x in config.OWNERS]
    if tid.lower() in owners or (uname and uname in owners):
        return True
    return False

def is_admin(user_or_id):
    """ Check if the user is an admin """
    if is_owner(user_or_id):
        return True
    try:
        tid = str(user_or_id.id)
        uname = (user_or_id.username or "").lower()
    except AttributeError:
        tid = str(user_or_id)
        uname = ""
    admins = [str(x).lower() for x in config.ADMINS]
    if tid.lower() in admins or (uname and uname in admins):
        return True
    return False

def send_admin_menu(bot, message):
    """ Send admin menu based on permissions """
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
    markup.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="back_main"))
    bot.send_message(message.chat.id, "<b>🛠 Admin Panel</b> 🛠", parse_mode="HTML", reply_markup=markup)

###############################
# KEYS MANAGEMENT FUNCTIONS
###############################

def generate_normal_key():
    return "NKEY-" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10))

def generate_premium_key():
    return "PKEY-" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10))

def add_key(key, key_type, points):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO keys (key, type, points, claimed) VALUES (?, ?, ?, 0)", (key, key_type, points))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding key: {e}")

def get_keys():
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("SELECT key, type, points, claimed, claimed_by FROM keys")
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"❌ Error fetching keys: {e}")
        return []

def claim_key_in_db(key, user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
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
    except sqlite3.Error as e:
        print(f"❌ Error claiming key: {e}")
        return "An error occurred while claiming the key."

###############################
# ADMIN PANEL HANDLERS & SECURITY
###############################

def admin_callback_handler(bot, call):
    data = call.data
    if not is_admin(call.from_user):
        bot.answer_callback_query(call.id, "Access prohibited.")
        return
    if data == "admin_platform":
        handle_admin_platform(bot, call)
    elif data == "admin_users":
        handle_admin_users(bot, call)  # Calls the user management handler
    elif data == "admin_keys":
        handle_admin_keys(bot, call)
    elif data == "admin_manage":
        handle_admin_manage(bot, call)
    elif data == "admin_add":
        if is_owner(call.from_user):
            handle_admin_add(bot, call)
        else:
            bot.answer_callback_query(call.id, "🚫 Only owners can add admins.")
    # Add more admin routes as needed

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

def handle_admin_keys(bot, call):
    keys = get_keys()
    text = "<b>🔑 Keys:</b>\n"
    if keys:
        for key in keys:
            text += f"• {key[0]} | {key[1]} | Points: {key[2]} | Claimed: {key[3]} | By: {key[4]}\n"
    else:
        text = "😕 No keys available."
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML")

def handle_admin_manage(bot, call):
    """
    Admin management functionality, such as managing admin roles.
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 View Admins", callback_data="admin_view_admins"),
        types.InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_admin")
    )
    bot.edit_message_text("<b>👥 Admin Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

def handle_admin_add(bot, call):
    """
    Adds a new admin by getting their user ID and username.
    """
    msg = bot.send_message(call.message.chat.id, "✏️ Please send the User ID of the user you want to add as an admin.")
    bot.register_next_step_handler(msg, process_admin_add)

def process_admin_add(bot, message):
    """
    Process the user input to add a new admin.
    """
    user_id = message.text.strip()
    # Check if the user exists and is valid
    add_admin(user_id)
    bot.send_message(message.chat.id, f"✅ User {user_id} has been added as an admin.")
    send_admin_menu(bot, message)

def add_admin(user_id):
    """
    Add a new admin to the database.
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)", (user_id, "admin"))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding admin: {e}")
        return "An error occurred while adding the admin."
    
