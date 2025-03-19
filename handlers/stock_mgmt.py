import os
import tempfile
import zipfile
import json
from telebot import types
from db import get_platforms, add_stock_to_platform
from db import update_stock_for_platform
from db import get_connection
from db import get_account_claim_cost
from handlers.logs import log_event

def handle_admin_stock(bot, call):
    # Immediately answer the callback so spinner stops
    bot.answer_callback_query(call.id, text="Loading stock management...")

    platforms = get_platforms()
    if not platforms:
        bot.answer_callback_query(call.id, "No platforms found.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for p in platforms:
        plat_name = p["platform_name"]
        markup.add(
            types.InlineKeyboardButton(
                text=plat_name,
                callback_data=f"stock_manage_{plat_name}"
            )
        )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_admin"))
    bot.edit_message_text(
        "Please select a platform to manage stock:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

def handle_stock_platform_choice(bot, call, platform_name):
    # Immediately answer the callback so spinner stops
    bot.answer_callback_query(call.id, text="Please send stock file or text...")

    if platform_name.startswith("Cookie: "):
        handle_cookie_stock(bot, call, platform_name)
    else:
        handle_account_stock(bot, call, platform_name)

def handle_account_stock(bot, call, platform_name):
    msg = bot.send_message(
        call.message.chat.id,
        f"Platform: {platform_name}\n"
        "Send me a .txt file OR paste the accounts directly (one per line)."
    )
    bot.register_next_step_handler(msg, process_account_file_or_text, bot, platform_name)

def process_account_file_or_text(message, bot, platform_name):
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
    msg = bot.send_message(
        call.message.chat.id,
        f"Platform: {platform_name}\n"
        "Send a .txt file (1 cookie) or a .zip (multiple .txt)."
    )
    bot.register_next_step_handler(msg, process_cookie_file, bot, platform_name)

def process_cookie_file(message, bot, platform_name):
    if message.content_type == 'document':
        filename = message.document.file_name
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        if filename.lower().endswith(".zip"):
            tmpzip_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmpzip:
                    tmpzip.write(downloaded_file)
                    tmpzip_path = tmpzip.name

                extracted_cookies = []
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
