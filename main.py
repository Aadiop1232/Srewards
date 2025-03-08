# main.py
import telebot
from telebot import types
import config
from datetime import datetime
from db import init_db, add_user, get_user
from handlers.verification import send_verification_message
from handlers.main_menu import send_main_menu
from handlers.referral import extract_referral_code, process_verified_referral, send_referral_menu, get_referral_link
from handlers.rewards import send_rewards_menu, handle_platform_selection, claim_account
from handlers.account_info import send_account_info
from handlers.review import prompt_review
from handlers.admin import send_admin_menu, admin_callback_handler

bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")
init_db()

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = str(message.from_user.id)
    # Extract referral code from /start command if present
    from handlers.referral import extract_referral_code
    pending_ref = extract_referral_code(message)
    # If the user is not in DB, add them with the pending referral (can be None)
    user = get_user(user_id)
    if not user:
        add_user(user_id,
                 message.from_user.username or message.from_user.first_name,
                 datetime.now().strftime("%Y-%m-%d"),
                 pending_referrer=pending_ref)
    # Automatically check verification each time /start is invoked
    from handlers.verification import send_verification_message
    send_verification_message(bot, message)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def callback_back_main(call):
    send_main_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "get_ref_link")
def callback_get_ref_link(call):
    ref_link = get_referral_link(call.from_user.id)
    bot.answer_callback_query(call.id, f"🔗 Your referral link: {ref_link}")
    bot.send_message(call.message.chat.id, f"🔗 *Your referral link:*\n{ref_link}", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "menu_rewards")
def callback_menu_rewards(call):
    send_rewards_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reward_"))
def callback_reward(call):
    platform = call.data.split("reward_")[1]
    handle_platform_selection(bot, call, platform)

@bot.callback_query_handler(func=lambda call: call.data.startswith("claim_"))
def callback_claim(call):
    platform = call.data.split("claim_")[1]
    claim_account(bot, call, platform)

@bot.callback_query_handler(func=lambda call: call.data == "menu_account")
def callback_menu_account(call):
    send_account_info(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_referral")
def callback_menu_referral(call):
    send_referral_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_review")
def callback_menu_review(call):
    prompt_review(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_admin")
def callback_menu_admin(call):
    send_admin_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin"))
def callback_admin(call):
    admin_callback_handler(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == "menu_main")
def callback_menu_main(call):
    send_main_menu(bot, call.message)

bot.polling(none_stop=True)
                       
