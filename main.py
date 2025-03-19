import telebot
import config
import os
import threading
import time
from datetime import datetime
from db import init_db, add_user, get_user, claim_key_in_db, DATABASE, get_all_users
from handlers.verification import send_verification_message, handle_verification_callback
from handlers.main_menu import send_main_menu
from handlers.referral import extract_referral_code
from handlers.rewards import send_rewards_menu, handle_platform_selection, claim_account
from handlers.review import prompt_review, process_report, REPORT_MAPPING, handle_report_callback
from handlers.account_info import send_account_info
from handlers.admin import send_admin_menu, admin_callback_handler, is_admin, lend_points, generate_normal_key, generate_premium_key, add_key
from handlers.logs import log_event

bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")
init_db()

@bot.message_handler(commands=['recover'])
def recover_command(message):
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "Please reply to a database file (document) with /recover command.")
        return
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "You do not have permission to perform this action.")
        return
    try:
        file_id = message.reply_to_message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(DATABASE, "wb") as f:
            f.write(downloaded_file)
        bot.reply_to(message, "Database recovered successfully!")
    except Exception as e:
        bot.reply_to(message, f"Error recovering database: {e}")

def daily_backup():
    while True:
        time.sleep(86400)  # 24 hours
        try:
            with open(DATABASE, "rb") as f:
                backup_data = f.read()
            for owner in config.OWNERS:
                bot.send_document(owner, ("bot_backup.db", backup_data))
        except Exception as e:
            print(f"Error during daily backup: {e}")

threading.Thread(target=daily_backup, daemon=True).start()

@bot.message_handler(commands=["broadcast"])
def broadcast_command(message):
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /broadcast <message>")
        return
    broadcast_text = parts[1]
    users = get_all_users()
    sent = 0
    for user in users:
        try:
            bot.send_message(user.get("telegram_id"), f"[BROADCAST]\n\n{broadcast_text}")
            sent += 1
        except Exception as e:
            print(f"Error broadcasting to {user.get('telegram_id')}: {e}")
    bot.reply_to(message, f"Broadcast sent to {sent} users.")

def check_if_banned(message):
    user = get_user(str(message.from_user.id))
    if user and user.get("banned", 0):
        bot.send_message(message.chat.id, "🚫 You are banned and cannot use this bot.")
        return True
    return False

@bot.message_handler(commands=["start"])
def start_command(message):
    if check_if_banned(message):
        return
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    pending_ref = extract_referral_code(message)
    if not user:
        add_user(user_id, message.from_user.username or message.from_user.first_name,
                 datetime.now().strftime("%Y-%m-%d"), pending_referrer=pending_ref)
        user = get_user(user_id)
    if is_admin(user):
        bot.send_message(message.chat.id, "✨ Welcome, Admin/Owner! You are automatically verified! ✨")
        send_main_menu(bot, message)
        return
    bot.send_message(message.chat.id, "⏳ Verifying your channel membership, please wait...")
    send_verification_message(bot, message)

@bot.message_handler(commands=["lend"])
def lend_command(message):
    if check_if_banned(message):
        return
    if message.chat.type != "private":
        bot.send_message(message.from_user.id, "Please use the /lend command in a private chat.")
        return
    if str(message.from_user.id) not in config.ADMINS and str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 You don't have permission to use this command.")
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /lend <user_id> <points> [custom message]", parse_mode="HTML")
        return
    user_id = parts[1]
    try:
        points = int(parts[2])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    custom_message = " ".join(parts[3:]) if len(parts) > 3 else None
    result = lend_points(str(message.from_user.id), user_id, points, custom_message)
    bot.reply_to(message, result)
    log_event(bot, "LEND", f"[LEND] {message.from_user.username or message.from_user.first_name} ({message.from_user.id}) lent {points} points to user {user_id}.", user=message.from_user)

@bot.message_handler(commands=["redeem"])
def redeem_command(message):
    if check_if_banned(message):
        return
    if message.chat.type != "private":
        bot.send_message(message.from_user.id, "Please use the /redeem command in a private chat.")
        return
    user_id = str(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /redeem <key>", parse_mode="HTML")
        return
    key = parts[1].strip()
    result = claim_key_in_db(key, user_id)
    bot.reply_to(message, result)
    log_event(bot, "ACCOUNT_CLAIM", f"[ACCOUNT_CLAIM] {message.from_user.username or message.from_user.first_name} ({user_id}) redeemed key {key}. Result: {result}", user=message.from_user)

@bot.message_handler(commands=["report"])
def report_command(message):
    if check_if_banned(message):
        return
    msg = bot.send_message(message.chat.id, "📝 Please type your report message (you may attach a photo or document):")
    bot.register_next_step_handler(msg, lambda m: process_report(bot, m))

@bot.message_handler(commands=["tutorial"])
def tutorial_command(message):
    if check_if_banned(message):
        return
    text = (
        "📖 Tutorial\n"
        "1. Every new user starts with 20 points.\n"
        "2. To claim an account, go to the Rewards section.\n"
        "3. Earn more points by referrals or redeeming keys.\n"
        "4. Use the Report button to report issues.\n"
        "5. Daily check-ins and missions offer bonus points.\n"
        "Admins can generate keys with /gen, lend points with /lend, etc.\n"
        "Enjoy and good luck! 😊"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["gen"])
def gen_command(message):
    if check_if_banned(message):
        return
    if message.chat.type != "private":
        bot.send_message(message.from_user.id, "Please use the /gen command in a private chat.")
        return
    if str(message.from_user.id) not in config.ADMINS and str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 You don't have permission to generate keys.")
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /gen <normal|premium> <quantity> [points]", parse_mode="HTML")
        return
    key_type = parts[1].lower()
    try:
        qty = int(parts[2])
    except ValueError:
        bot.reply_to(message, "Quantity must be a number.")
        return
    if len(parts) >= 4:
        try:
            key_points = int(parts[3])
        except ValueError:
            bot.reply_to(message, "Key points must be a number.")
            return
    else:
        key_points = 15 if key_type == "normal" else 90
    generated = []
    if key_type == "normal":
        for _ in range(qty):
            key = generate_normal_key()
            add_key(key, "normal", key_points)
            generated.append(key)
    elif key_type == "premium":
        for _ in range(qty):
            key = generate_premium_key()
            add_key(key, "premium", key_points)
            generated.append(key)
    else:
        bot.reply_to(message, "Key type must be either 'normal' or 'premium'.")
        return
    if generated:
        text = "Redeem Generated ✅\n"
        for key in generated:
            text += f"➔ <code>{key}</code>\n"
        text += "\nYou can redeem this code using this command: /redeem KEY"
    else:
        text = "No keys generated."
    bot.reply_to(message, text, parse_mode="HTML")

# ----------------
# Callback handlers
# ----------------

@bot.callback_query_handler(func=lambda call: call.data in ["claim_report", "close_report"])
def callback_report(call):
    from handlers.review import handle_report_callback
    handle_report_callback(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def callback_back_main(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print("Error deleting message:", e)
    from handlers.main_menu import send_main_menu
    send_main_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "back_admin")
def callback_back_admin(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print("Error deleting message:", e)
    from handlers.admin import send_admin_menu
    send_admin_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify"))
def callback_verify(call):
    from handlers.verification import handle_verification_callback
    handle_verification_callback(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin"))
def callback_admin(call):
    admin_callback_handler(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def callback_menu(call):
    if call.data == "menu_rewards":
        send_rewards_menu(bot, call.message)
    elif call.data == "menu_info":
        from handlers.account_info import send_account_info
        send_account_info(bot, call)
    elif call.data == "menu_referral":
        from handlers.referral import send_referral_menu
        send_referral_menu(bot, call.message)
    elif call.data == "menu_review":
        from handlers.review import prompt_review
        prompt_review(bot, call.message)
    elif call.data == "menu_report":
        msg = bot.send_message(call.message.chat.id, "📝 Please type your report message (you may attach a photo or document):")
        bot.register_next_step_handler(msg, lambda m: process_report(bot, m))
    elif call.data == "menu_support":
        from handlers.support import send_support_message
        send_support_message(bot, call.message)
    elif call.data == "menu_admin":
        from handlers.admin import send_admin_menu
        send_admin_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown menu command.")

@bot.callback_query_handler(func=lambda call: call.data == "get_ref_link")
def callback_get_ref_link(call):
    bot.answer_callback_query(call.id, "Generating referral link...")
    from handlers.referral import get_referral_link
    referral_link = get_referral_link(str(call.from_user.id))
    bot.send_message(call.message.chat.id, f"Your referral link:\n{referral_link}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reward_"))
def callback_reward(call):
    platform_name = call.data.split("reward_")[1]
    from handlers.rewards import handle_platform_selection
    handle_platform_selection(bot, call, platform_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith("claim_"))
def callback_claim(call):
    platform_name = call.data.split("claim_")[1]
    from handlers.rewards import claim_account
    claim_account(bot, call, platform_name)

@bot.message_handler(func=lambda message: message.reply_to_message and 
                     message.reply_to_message.message_id in REPORT_MAPPING)
def relay_report_reply(message):
    original_chat = REPORT_MAPPING[message.reply_to_message.message_id]
    bot.send_message(original_chat, f"Reply from Admin: {message.text}")

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Polling error: {e}")
        try:
            bot.send_message(config.LOGS_CHANNEL, f"Polling error: {e}")
        except Exception:
            pass
        time.sleep(15)
