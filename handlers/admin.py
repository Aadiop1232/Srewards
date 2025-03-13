import sqlite3
from telebot import types
import json
import config

# Function to send the admin menu with platform management options
def send_admin_menu(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📺 Platform Mgmt", callback_data="admin_platform"),
        types.InlineKeyboardButton("📈 Stock Mgmt", callback_data="admin_stock"),
        types.InlineKeyboardButton("👤 User Mgmt", callback_data="admin_users"),
        types.InlineKeyboardButton("🔑 Key Management", callback_data="admin_keys"),
        types.InlineKeyboardButton("🛠 Admin Settings", callback_data="admin_settings")
    )
    bot.send_message(message.chat.id, "<b>🛠 Admin Panel</b>", parse_mode="HTML", reply_markup=markup)

# Handle the 'Platform Mgmt' section of the admin panel
def handle_admin_platform(bot, call):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="add_platform"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="remove_platform")
    )
    bot.edit_message_text("Select an option for platform management:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

# Handle the 'Stock Mgmt' section of the admin panel
def handle_admin_stock(bot, call):
    platforms = get_platforms()  # Get platforms from the database
    if not platforms:
        bot.send_message(call.message.chat.id, "❌ No platforms found. Please add a platform first.")
        send_admin_menu(bot, call.message)
        return

    markup = types.InlineKeyboardMarkup()
    for platform in platforms:
        markup.add(types.InlineKeyboardButton(f"Add stock to {platform[0]}", callback_data=f"add_stock_{platform[0]}"))

    bot.edit_message_text("Select a platform to add stock:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

# Handle adding stock to a platform
def handle_add_stock(bot, call, platform_name):
    msg = bot.send_message(call.message.chat.id, f"Please send the stock (accounts) to add to '{platform_name}'.")
    bot.register_next_step_handler(msg, process_add_stock, platform_name)

# Process the stock input and add it to the selected platform
def process_add_stock(bot, message, platform_name):
    stock_data = message.text.strip()

    if not stock_data:
        bot.send_message(message.chat.id, "❌ Stock data cannot be empty.")
        return

    # Assuming stock is entered as a list of accounts (comma-separated)
    stock_list = stock_data.split(',')

    # Update the platform's stock
    update_platform_stock(platform_name, stock_list)
    bot.send_message(message.chat.id, f"✅ Stock added to platform '{platform_name}'.")
    send_admin_menu(bot, message)

# Update the stock for a specific platform
def update_platform_stock(platform_name, stock):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE platforms SET stock=? WHERE platform_name=?", (json.dumps(stock), platform_name))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error updating stock for platform {platform_name}: {e}")

# Add a platform to the database
def add_platform(platform_name):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO platforms (platform_name, stock) VALUES (?, ?)", (platform_name, json.dumps([])))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding platform: {e}")

# Function to get all platforms
def get_platforms():
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("SELECT platform_name FROM platforms")
        rows = c.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"❌ Error fetching platforms: {e}")
        return []

# Function to handle user management in the admin panel
def handle_admin_users(bot, call):
    users = get_users()  # Get all users from the database
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

# Fetch specific user by telegram_id
def get_user(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user
    except sqlite3.Error as e:
        print(f"❌ Error fetching user {user_id}: {e}")
        return None

# Function to fetch all users
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

# Ban a user
def ban_user(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=1 WHERE telegram_id=?", (user_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error banning user: {e}")

# Unban a user
def unban_user(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET banned=0 WHERE telegram_id=?", (user_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error unbanning user: {e}")

# Function to handle adding and removing admins
def handle_admin_actions(bot, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Admin", callback_data="add_admin"),
        types.InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin"),
        types.InlineKeyboardButton("👤 Admin Info", callback_data="admin_info")
    )
    bot.edit_message_text("<b>🛠 Admin Panel - Admin Management</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

# Function to add an admin
def add_admin(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)", (user_id, "admin"))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding admin: {e}")

# Function to remove an admin
def remove_admin(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error removing admin: {e}")

