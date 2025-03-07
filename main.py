
# main.py
import telebot
from telebot import types
import config
from datetime import datetime
from db import init_db, add_user, get_user
from handlers.verification import send_verification, handle_verification_callback
from handlers.main_menu import send_main_menu
from handlers.referral import extract_referral_code, process_verified_referral, send_referral_menu

bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")
init_db()

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = str(message.from_user.id)
    from handlers.referral import extract_referral_code
    pending_ref = extract_referral_code(message)
    
    user = get_user(user_id)
    if not user:
        add_user(user_id,
                 message.from_user.username or message.from_user.first_name,
                 datetime.now().strftime("%Y-%m-%d"),
                 pending_referrer=pending_ref)
    send_verification(bot, message)

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def callback_verify(call):
    from handlers.verification import handle_verification_callback
    handle_verification_callback(bot, call)
    from handlers.referral import process_verified_referral
    process_verified_referral(call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def callback_back_main(call):
    send_main_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "get_ref_link")
def callback_get_ref_link(call):
    from handlers.referral import get_referral_link
    ref_link = get_referral_link(call.from_user.id)
    bot.answer_callback_query(call.id, f"Your referral link: {ref_link}")
    bot.send_message(call.message.chat.id, f"Your referral link: {ref_link}")

# Additional handlers for rewards, account info, review, and admin panel should be added here.

bot.polling(none_stop=True)
  
