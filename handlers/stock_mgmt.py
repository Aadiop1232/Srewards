# stock_mgmt.py

import os
import tempfile
import zipfile
import json
import telebot
import config
from telebot import types
from db import get_connection, get_platforms, add_stock_to_platform, update_stock_for_platform
from db import get_account_claim_cost
from handlers.logs import log_event

################################
# Platform Management Callbacks
################################

def handle_platform_callback(bot, call):
    """
    Called when user taps a "Platform Mgmt" button (previously 'admin_platform').
    Displays the add/remove/rename/change price menu.
    """
    bot.answer_callback_query(call.id, text="Platform mgmt loading...")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Platform", callback_data="platform_add"),
        types.InlineKeyboardButton("➖ Remove Platform", callback_data="platform_remove")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Rename Platform", callback_data="platform_rename"),
        types.InlineKeyboardButton("💲 Change Price", callback_data="platform_changeprice")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))

    try:
        bot.edit_message_text(
            "Platform Management Options:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, "Platform Management Options:", reply_markup=markup)

def handle_platform_add(bot, call):
    """
    Asks the admin for a new platform name (account-based).
    """
    bot.answer_callback_query(call.id, text="Adding platform...")
    msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Account Platform):")
    bot.register_next_step_handler(msg, process_platform_add_account, bot)

def process_platform_add_account(message, bot):
    """
    After admin sends platform name, ask for price, then create the platform in DB.
    """
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for platform '{platform_name}':")
    bot.register_next_step_handler(msg, process_platform_price, bot, platform_name)

def process_platform_price(message, bot, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return

    response = add_platform(platform_name, price)
    bot.send_message(message.chat.id, response)

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def add_platform(platform_name, price):
    """
    Insert a new normal (account) platform in DB, set initial stock to "[]".
    """
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

    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM",
              f"[PLATFORM] Added Account Platform: {platform_name} with price {price} pts.")
    return f"Platform '{platform_name}' added successfully."

def handle_platform_add_cookie(bot, call):
    """
    Asks the admin for a new platform name (cookie-based).
    """
    bot.answer_callback_query(call.id, text="Adding cookie platform...")
    msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Cookie Platform):")
    bot.register_next_step_handler(msg, process_platform_add_cookie, bot)

def process_platform_add_cookie(message, bot):
    """
    After admin sends the cookie platform's name, ask for price, then create it in DB.
    """
    platform_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"Enter the price for cookie platform '{platform_name}':")
    bot.register_next_step_handler(msg, process_cookie_platform_price, bot, platform_name)

def process_cookie_platform_price(message, bot, platform_name):
    try:
        price = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
        return

    response = add_cookie_platform(platform_name, price)
    bot.send_message(message.chat.id, response)

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def add_cookie_platform(platform_name, price):
    """
    Insert a new 'Cookie: X' platform in DB, set stock to "[]".
    """
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

    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM",
              f"[PLATFORM] Added Cookie Platform: {cookie_platform_name} with price {price} pts.")
    return f"Cookie Platform '{cookie_platform_name}' added successfully."

def handle_platform_remove(bot, call):
    """
    Shows a list of platforms to remove.
    """
    bot.answer_callback_query(call.id, text="Removing platform...")
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms to remove.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(
            types.InlineKeyboardButton(plat_name, callback_data=f"platform_rm_{plat_name}")
        )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="platform_back"))
    bot.edit_message_text("Select a platform to remove:",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=markup)

def handle_platform_rm(bot, call, platform_name):
    """
    Actually remove the chosen platform from DB.
    """
    response = remove_platform(platform_name)
    bot.answer_callback_query(call.id, text=response)

    handle_platform_callback(bot, call)

def remove_platform(platform_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM platforms WHERE platform_name = ?", (platform_name,))
    conn.commit()
    c.close()
    conn.close()

    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM",
              f"[PLATFORM] Removed Platform: {platform_name}.")
    return f"Platform '{platform_name}' removed successfully."

def handle_platform_rename(bot, call):
    """
    Shows a list of platforms to rename.
    """
    bot.answer_callback_query(call.id, text="Renaming platform...")
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        markup.add(types.InlineKeyboardButton(plat_name, callback_data=f"platform_rename_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="platform_back"))
    bot.edit_message_text("Select a platform to rename:",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=markup)

def process_platform_rename(message, bot, old_name):
    """
    After the user typed the new platform name, rename it in DB.
    """
    new_name = message.text.strip()
    response = rename_platform(old_name, new_name)
    bot.send_message(message.chat.id, response)

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

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

    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM",
              f"[PLATFORM] Renamed Platform from '{old_name}' to '{new_name}'.")
    return f"Platform '{old_name}' renamed to '{new_name}' successfully."

def handle_platform_changeprice(bot, call):
    """
    Shows a list of platforms to change price.
    """
    bot.answer_callback_query(call.id, text="Changing platform price...")
    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms available.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for plat in platforms:
        plat_name = plat.get("platform_name")
        price = plat.get("price")
        btn_text = f"{plat_name} (Current: {price} pts)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"platform_cp_{plat_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="platform_back"))
    bot.edit_message_text("Select a platform to change its price:",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=markup)

def process_platform_changeprice(message, bot, platform_name):
    """
    After admin typed new price, update in DB.
    """
    new_price = message.text.strip()
    response = change_price(platform_name, new_price)
    bot.send_message(message.chat.id, response)

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

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

    log_event(telebot.TeleBot(config.TOKEN), "PLATFORM",
              f"[PLATFORM] Changed Price for Platform '{platform_name}' to {new_price_int} pts.")
    return f"Price for platform '{platform_name}' changed to {new_price_int} pts successfully."

################################
# Stock Management Callbacks
################################

def handle_admin_stock(bot, call):
    """
    Called when user taps a "Stock Mgmt" button.
    Shows the list of platforms, so we can add accounts/cookies to each.
    """
    bot.answer_callback_query(call.id, text="Loading stock management...")

    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, text="No platforms found.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        plat_name = p["platform_name"]
        markup.add(types.InlineKeyboardButton(
            text=plat_name,
            callback_data=f"stock_manage_{plat_name}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))

    bot.edit_message_text(
        "Please select a platform to manage stock:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

def handle_stock_platform_choice(bot, call, platform_name):
    """
    Called when callback_data starts with 'stock_manage_'
    Distinguish normal vs. 'Cookie' platforms, then ask for the stock file or text.
    """
    bot.answer_callback_query(call.id, text="Please send stock file/text...")

    if platform_name.startswith("Cookie: "):
        handle_cookie_stock(bot, call, platform_name)
    else:
        handle_account_stock(bot, call, platform_name)

def handle_account_stock(bot, call, platform_name):
    """
    Tells admin to upload a .txt file or paste lines of accounts.
    """
    msg = bot.send_message(
        call.message.chat.id,
        f"Platform: {platform_name}\n"
        "Send me a .txt file OR paste the accounts directly (one per line)."
    )
    bot.register_next_step_handler(msg, process_account_file_or_text, bot, platform_name)

def process_account_file_or_text(message, bot, platform_name):
    """
    Actually read the .txt file or the pasted text lines, then add them to the DB.
    """
    if message.content_type == 'document':
        try:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            raw_text = downloaded_file.decode('utf-8', errors='ignore')
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            resp = add_stock_to_platform(platform_name, lines)
            bot.send_message(message.chat.id, f"{resp}\n\n{len(lines)} accounts added.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error reading file: {e}")

    elif message.content_type == 'text':
        lines = [l.strip() for l in message.text.splitlines() if l.strip()]
        resp = add_stock_to_platform(platform_name, lines)
        bot.send_message(message.chat.id, f"{resp}\n\n{len(lines)} accounts added.")
    else:
        bot.send_message(message.chat.id, "Please send a .txt file or normal text lines.")

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

def handle_cookie_stock(bot, call, platform_name):
    """
    Tells admin to upload a .txt or .zip with cookie files.
    """
    msg = bot.send_message(
        call.message.chat.id,
        f"Platform: {platform_name}\n"
        "Send a .txt file (1 cookie) or a .zip (multiple .txt)."
    )
    bot.register_next_step_handler(msg, process_cookie_file, bot, platform_name)

def process_cookie_file(message, bot, platform_name):
    """
    Reads either a single .txt cookie or multiple .txt files in a .zip,
    then adds them to the DB.
    """
    if message.content_type == 'document':
        filename = message.document.file_name
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        if filename.lower().endswith(".zip"):
            tmpzip_path = ""
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmpzip:
                    tmpzip.write(downloaded_file)
                    tmpzip_path = tmpzip.name

                extracted_cookies = []
                import os
                import zipfile
                with zipfile.ZipFile(tmpzip_path, 'r') as z:
                    for name in z.namelist():
                        if name.endswith(".txt"):
                            with z.open(name) as txt_file:
                                raw_txt = txt_file.read().decode('utf-8', errors='ignore').strip()
                                extracted_cookies.append(raw_txt)

                if os.path.exists(tmpzip_path):
                    os.remove(tmpzip_path)

                if extracted_cookies:
                    resp = add_stock_to_platform(platform_name, extracted_cookies)
                    bot.send_message(message.chat.id, f"{resp}\n\nAdded {len(extracted_cookies)} cookie files.")
                else:
                    bot.send_message(message.chat.id, "No .txt files found in the zip.")
            except Exception as e:
                bot.send_message(message.chat.id, f"Error handling zip: {e}")

        elif filename.lower().endswith(".txt"):
            raw_text = downloaded_file.decode('utf-8', errors='ignore').strip()
            resp = add_stock_to_platform(platform_name, [raw_text])
            bot.send_message(message.chat.id, f"{resp}\n\nAdded 1 cookie from .txt.")
        else:
            bot.send_message(message.chat.id, "Unsupported file type. Please send .txt or .zip.")
    else:
        bot.send_message(message.chat.id, "Please send a .txt or .zip file for cookies.")

    from handlers.admin import send_admin_menu
    send_admin_menu(bot, message)

################################
# HELPER: platform_back callback
################################

def handle_platform_back(bot, call):
    """
    Called when user taps '🔙 Back' in the platform mgmt menu. 
    Just re-displays the main platform mgmt menu or admin menu as needed.
    """
    bot.answer_callback_query(call.id, text="Going back...")
    handle_platform_callback(bot, call)
