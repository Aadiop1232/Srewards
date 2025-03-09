import telebot
import config
from datetime import datetime
from db import init_db, add_user, get_user, claim_key_in_db
from handlers.verification import send_verification_message, handle_verification_callback
from handlers.main_menu import send_main_menu
from handlers.referral import extract_referral_code, process_verified_referral
from handlers.rewards import send_rewards_menu, handle_platform_selection, claim_account
from handlers.account_info import send_account_info
from handlers.review import prompt_review
from handlers.admin import send_admin_menu, admin_callback_handler, is_admin, generate_normal_key, generate_premium_key, add_key

bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")
init_db()

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = str(message.from_user.id)
    pending_ref = extract_referral_code(message)
    
    # Add user if not exists
    if not get_user(user_id):
        add_user(
            user_id,
            message.from_user.username or message.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d"),
            pending_ref
        )
    
    # Handle verification and menu
    try:
        send_verification_message(bot, message)
    except Exception as e:
        print(f"Start command error: {e}")
        bot.send_message(message.chat.id, "🚫 Error initializing bot. Please try again.")

@bot.message_handler(commands=["gen"])
def gen_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "🚫 Permission denied.")
        return
    
    try:
        _, key_type, qty = message.text.split()
        qty = int(qty)
    except:
        bot.reply_to(message, "❌ Usage: /gen <normal|premium> <quantity>")
        return

    generated = []
    key_func = generate_premium_key if key_type.lower() == "premium" else generate_normal_key
    points = 35 if key_type.lower() == "premium" else 15
    
    for _ in range(qty):
        key = key_func()
        add_key(key, key_type.lower(), points)
        generated.append(key)
    
    bot.reply_to(message, f"🔑 Generated {qty} {key_type} keys:\n" + "\n".join(generated))

@bot.message_handler(commands=["redeem"])
def redeem_command(message):
    try:
        key = message.text.split()[1]
        result = claim_key_in_db(key, str(message.from_user.id))
        bot.reply_to(message, result)
    except IndexError:
        bot.reply_to(message, "❌ Usage: /redeem <key>")
    except Exception as e:
        print(f"Redeem error: {e}")
        bot.reply_to(message, "❌ Error processing key.")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    try:
        if call.data == "back_main":
            send_main_menu(bot, call.message, edit=True)
        elif call.data.startswith("reward_"):
            handle_platform_selection(bot, call, call.data.split("_")[1])
        elif call.data.startswith("claim_"):
            claim_account(bot, call, call.data.split("_")[1])
        elif call.data == "menu_account":
            send_account_info(bot, call)
        elif call.data == "menu_referral":
            from handlers.referral import send_referral_menu
            send_referral_menu(bot, call.message)
        elif call.data == "menu_review":
            prompt_review(bot, call.message)
        elif call.data == "menu_admin":
            send_admin_menu(bot, call.message)
        elif call.data == "verify":
            handle_verification_callback(bot, call)
            process_verified_referral(call.from_user.id)
        elif call.data.startswith("admin"):
            admin_callback_handler(bot, call)
        else:
            bot.answer_callback_query(call.id, "❌ Unknown command")
    except Exception as e:
        print(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing request")

if __name__ == "__main__":
    print("Bot started...")
    bot.polling(none_stop=True)
