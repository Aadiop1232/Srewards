# main.py
import telebot
import config
from datetime import datetime
from db import add_user, get_user, claim_key_in_db
from handlers.verification import send_verification_message, handle_verification_callback
from handlers.main_menu import send_main_menu
from handlers.referral import extract_referral_code, process_verified_referral, send_referral_menu, get_referral_link
from handlers.rewards import send_rewards_menu, handle_platform_selection, claim_account
from handlers.review import prompt_review
from handlers.admin import send_admin_menu, admin_callback_handler, lend_points, update_account_claim_cost, update_referral_bonus
from handlers.logs import log_event

bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start_command(message):
    print(f"[DEBUG] Received /start command from user: {message.from_user.id}")
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    
    # Block banned users
    if user and user.get("banned", False):
        bot.send_message(message.chat.id, "🚫 You are banned and cannot use this bot.")
        print(f"[DEBUG] User {user_id} is banned.")
        return

    pending_ref = extract_referral_code(message)
    
    if not user:
        print(f"[DEBUG] Creating new user with ID: {user_id}")
        add_user(
            user_id,
            message.from_user.username or message.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d"),
            pending_referrer=pending_ref
        )
        user = get_user(user_id)
    
    print(f"[DEBUG] User {user_id} record exists. Proceeding to verification.")
    # Send immediate feedback so the user sees something while verification is performed
    bot.send_message(message.chat.id, "⏳ Verifying your channel membership, please wait...")
    send_verification_message(bot, message)

# (Other command handlers remain as before)
@bot.message_handler(commands=["gen"])
def gen_command(message):
    # Implementation for /gen command (key generation) goes here.
    pass

@bot.message_handler(commands=["redeem"])
def redeem_command(message):
    # Implementation for /redeem command goes here.
    pass

@bot.message_handler(commands=["tutorial"])
def tutorial_command(message):
    # Implementation for /tutorial command goes here.
    pass

@bot.message_handler(commands=["lend"])
def lend_command(message):
    # Implementation for /lend command goes here.
    pass

@bot.message_handler(commands=["Uprice"])
def uprice_command(message):
    # Implementation for /Uprice command goes here.
    pass

@bot.message_handler(commands=["Rpoints"])
def rpoints_command(message):
    # Implementation for /Rpoints command goes here.
    pass

@bot.message_handler(commands=["report"])
def report_command(message):
    # Implementation for /report command goes here.
    pass

# Callback query handlers
@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def callback_back_main(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print("[DEBUG] Error deleting message:", e)
    from handlers.main_menu import send_main_menu
    send_main_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify"))
def callback_verify(call):
    handle_verification_callback(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin"))
def callback_admin(call):
    admin_callback_handler(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def callback_menu(call):
    # Example: routes for rewards, account info, referral, review, report, admin panel
    if call.data == "menu_rewards":
        send_rewards_menu(bot, call.message)
    elif call.data == "menu_account":
        from handlers.account_info import send_account_info
        send_account_info(bot, call)
    elif call.data == "menu_referral":
        from handlers.referral import send_referral_menu
        send_referral_menu(bot, call.message)
    elif call.data == "menu_review":
        prompt_review(bot, call.message)
    elif call.data == "menu_report":
        msg = bot.send_message(call.message.chat.id, "📝 Please type your report message:")
        bot.register_next_step_handler(msg, lambda m: print("[DEBUG] Report received"))  # Replace with actual report processing
    elif call.data == "menu_admin":
        send_admin_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Unknown menu command.")

bot.polling(none_stop=True)
