import os
import tempfile
import zipfile
import json
import telebot
import config
from telebot import types
from db import get_platforms, add_stock_to_platform, update_stock_for_platform, get_account_claim_cost
from handlers.logs import log_event

def handle_platform_callback(bot, call):
    try:
        print(f"[DEBUG handle_platform_callback] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Platform management loading...")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Add Platform", callback_data="platform_add"),
            types.InlineKeyboardButton("➖ Remove Platform", callback_data="platform_remove")
        )
        markup.add(
            types.InlineKeyboardButton("✏️ Rename Platform", callback_data="platform_rename"),
            types.InlineKeyboardButton("💲 Change Price", callback_data="platform_changeprice")
        )
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="platform_back"))
        try:
            bot.edit_message_text(
                "Platform Management Options:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Edit message failed: {e}")
            bot.send_message(call.message.chat.id, "Platform Management Options:", reply_markup=markup)
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_callback: {e}")

def handle_platform_add(bot, call):
    try:
        print(f"[DEBUG handle_platform_add] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Adding platform...")
        msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Account Platform):")
        bot.register_next_step_handler(msg, process_platform_add_account, bot)
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_add: {e}")

def process_platform_add_account(message, bot):
    try:
        print(f"[DEBUG process_platform_add_account] text='{message.text}', from_user_id={message.from_user.id}")
        platform_name = message.text.strip()
        msg = bot.send_message(message.chat.id, f"Enter the price for platform '{platform_name}':")
        bot.register_next_step_handler(msg, process_platform_price, bot, platform_name)
    except Exception as e:
        print(f"Error in process_platform_add_account: {e}")

def process_platform_price(message, bot, platform_name):
    from db import add_platform
    try:
        print(f"[DEBUG process_platform_price] text='{message.text}', user_id={message.from_user.id}, platform='{platform_name}'")
        try:
            price = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
            return
        response = add_platform(platform_name, price)
        bot.send_message(message.chat.id, response)
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_platform_price: {e}")

def handle_platform_add_cookie(bot, call):
    try:
        print(f"[DEBUG handle_platform_add_cookie] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Adding cookie platform...")
        msg = bot.send_message(call.message.chat.id, "Please send the platform name to add (Cookie Platform):")
        bot.register_next_step_handler(msg, process_platform_add_cookie, bot)
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_add_cookie: {e}")

def process_platform_add_cookie(message, bot):
    from db import add_cookie_platform
    try:
        print(f"[DEBUG process_platform_add_cookie] text='{message.text}', user_id={message.from_user.id}")
        platform_name = message.text.strip()
        msg = bot.send_message(message.chat.id, f"Enter the price for cookie platform '{platform_name}':")
        bot.register_next_step_handler(msg, process_cookie_platform_price, bot, platform_name)
    except Exception as e:
        print(f"Error in process_platform_add_cookie: {e}")

def process_cookie_platform_price(message, bot, platform_name):
    from db import add_cookie_platform
    try:
        print(f"[DEBUG process_cookie_platform_price] text='{message.text}', user_id={message.from_user.id}, platform='{platform_name}'")
        try:
            price = int(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "Invalid price. Please enter a valid number.")
            return
        response = add_cookie_platform(platform_name, price)
        bot.send_message(message.chat.id, response)
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_cookie_platform_price: {e}")

def handle_platform_remove(bot, call):
    try:
        print(f"[DEBUG handle_platform_remove] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Removing platform...")
        from db import get_platforms
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
        bot.edit_message_text(
            "Select a platform to remove:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_remove: {e}")

def handle_platform_rm(bot, call, platform_name):
    try:
        print(f"[DEBUG handle_platform_rm] data='{call.data}', user_id={call.from_user.id}, platform='{platform_name}'")
        bot.answer_callback_query(call.id, text=f"Removing {platform_name}...")
        from db import remove_platform
        response = remove_platform(platform_name)
        bot.send_message(call.message.chat.id, response)
        handle_platform_callback(bot, call)
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_rm: {e}")

def handle_platform_rename(bot, call):
    try:
        print(f"[DEBUG handle_platform_rename] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Renaming platform...")
        from db import get_platforms
        platforms = get_platforms()
        if not platforms:
            bot.answer_callback_query(call.id, "No platforms available.")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        for plat in platforms:
            plat_name = plat.get("platform_name")
            markup.add(
                types.InlineKeyboardButton(plat_name, callback_data=f"platform_rename_{plat_name}")
            )
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="platform_back"))
        bot.edit_message_text(
            "Select a platform to rename:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_rename: {e}")

def process_platform_rename(message, bot, old_name):
    from db import rename_platform
    try:
        print(f"[DEBUG process_platform_rename] text='{message.text}', user_id={message.from_user.id}, old_name='{old_name}'")
        new_name = message.text.strip()
        response = rename_platform(old_name, new_name)
        bot.send_message(message.chat.id, response)
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_platform_rename: {e}")

def handle_platform_changeprice(bot, call):
    try:
        print(f"[DEBUG handle_platform_changeprice] data='{call.data}', user_id={call.from_user.id}")
        bot.answer_callback_query(call.id, text="Changing platform price...")
        from db import get_platforms
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
        bot.edit_message_text(
            "Select a platform to change its price:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_platform_changeprice: {e}")

def process_platform_changeprice(message, bot, platform_name):
    from db import change_price
    try:
        print(f"[DEBUG process_platform_changeprice] text='{message.text}', user_id={message.from_user.id}, platform='{platform_name}'")
        new_price = message.text.strip()
        response = change_price(platform_name, new_price)
        bot.send_message(message.chat.id, response)
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_platform_changeprice: {e}")

################################
# STOCK MANAGEMENT
################################

def handle_admin_stock(bot, call):
    try:
        print(f"[DEBUG handle_admin_stock] data='{call.data}', user_id={call.from_user.id}")
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
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_admin_stock: {e}")

def handle_stock_platform_choice(bot, call, platform_name):
    try:
        print(f"[DEBUG handle_stock_platform_choice] data='{call.data}', user_id={call.from_user.id}, platform='{platform_name}'")
        bot.answer_callback_query(call.id, text="Uploading file...")
        if platform_name.startswith("Cookie: "):
            handle_cookie_stock(bot, call, platform_name)
        else:
            handle_account_stock(bot, call, platform_name)
    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
        except Exception:
            pass
        print(f"Error in handle_stock_platform_choice: {e}")

def handle_account_stock(bot, call, platform_name):
    try:
        print(f"[DEBUG handle_account_stock] data='{call.data}', user_id={call.from_user.id}, platform='{platform_name}'")
        msg = bot.send_message(
            call.message.chat.id,
            f"Platform: {platform_name}\n"
            "Send me a .txt file OR paste the accounts directly (one per line)."
        )
        bot.register_next_step_handler(msg, process_account_file_or_text, bot, platform_name)
    except Exception as e:
        print(f"Error in handle_account_stock: {e}")

def process_account_file_or_text(message, bot, platform_name):
    try:
        print(f"[DEBUG process_account_file_or_text] content_type='{message.content_type}', user_id={message.from_user.id}, platform='{platform_name}'")
        if message.content_type == 'document':
            try:
                file_id = message.document.file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                raw_text = downloaded_file.decode('utf-8', errors='ignore')
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                resp = add_stock_to_platform(platform_name, lines)
                bot.send_message(message.chat.id, f"{resp}\n\n{len(lines)} accounts added.")
                log_event(bot, "STOCK",
                          f"[STOCK] {len(lines)} accounts added to '{platform_name}'.",
                          user=message.from_user)
            except Exception as e:
                bot.send_message(message.chat.id, f"Error reading file: {e}")
        elif message.content_type == 'text':
            lines = [l.strip() for l in message.text.splitlines() if l.strip()]
            resp = add_stock_to_platform(platform_name, lines)
            bot.send_message(message.chat.id, f"{resp}\n\n{len(lines)} accounts added.")
            log_event(bot, "STOCK",
                      f"[STOCK] {len(lines)} accounts added to '{platform_name}'.",
                      user=message.from_user)
        else:
            bot.send_message(message.chat.id, "Please send a .txt file or normal text lines.")
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_account_file_or_text: {e}")

def handle_cookie_stock(bot, call, platform_name):
    try:
        print(f"[DEBUG handle_cookie_stock] data='{call.data}', user_id={call.from_user.id}, platform='{platform_name}'")
        msg = bot.send_message(
            call.message.chat.id,
            f"Platform: {platform_name}\n"
            "Send a .txt file (1 cookie) or a .zip (multiple .txt)."
        )
        bot.register_next_step_handler(msg, process_cookie_file, bot, platform_name)
    except Exception as e:
        print(f"Error in handle_cookie_stock: {e}")

def process_cookie_file(message, bot, platform_name):
    try:
        print(f"[DEBUG process_cookie_file] content_type='{message.content_type}', user_id={message.from_user.id}, platform='{platform_name}'")
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
                    with zipfile.ZipFile(tmpzip_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.lower().endswith('.txt'):
                                extracted = zip_ref.read(file).decode('utf-8', errors='ignore')
                                lines = [l.strip() for l in extracted.splitlines() if l.strip()]
                                extracted_cookies.extend(lines)
                    resp = add_stock_to_platform(platform_name, extracted_cookies)
                    bot.send_message(message.chat.id, f"{resp}\n\n{len(extracted_cookies)} cookies added.")
                    log_event(bot, "STOCK",
                              f"[STOCK] {len(extracted_cookies)} cookies added to '{platform_name}'.",
                              user=message.from_user)
                except Exception as e:
                    bot.send_message(message.chat.id, f"Error processing ZIP file: {e}")
                finally:
                    if tmpzip_path and os.path.exists(tmpzip_path):
                        os.remove(tmpzip_path)
            elif filename.lower().endswith(".txt"):
                extracted = downloaded_file.decode('utf-8', errors='ignore')
                lines = [l.strip() for l in extracted.splitlines() if l.strip()]
                resp = add_stock_to_platform(platform_name, lines)
                bot.send_message(message.chat.id, f"{resp}\n\n{len(lines)} cookies added.")
                log_event(bot, "STOCK",
                          f"[STOCK] {len(lines)} cookies added to '{platform_name}'.",
                          user=message.from_user)
            else:
                bot.send_message(message.chat.id, "Unsupported file type. Please send a .txt file or .zip archive.")
        else:
            bot.send_message(message.chat.id, "Please send a document file.")
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, message)
    except Exception as e:
        print(f"Error in process_cookie_file: {e}")
