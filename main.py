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
init_db()  # For Mongo, this ensures connection setup if needed

# --- Command Handlers ---

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    # Block banned users
    if user and user.get("banned", False):
        bot.send_message(message.chat.id, "🚫 You are banned and cannot use this bot.")
        return
    pending_ref = extract_referral_code(message)
    if not user:
        add_user(user_id,
                 message.from_user.username or message.from_user.first_name,
                 datetime.now().strftime("%Y-%m-%d"),
                 pending_referrer=pending_ref)
    send_verification_message(bot, message)

@bot.message_handler(commands=["gen"])
def gen_command(message):
    # Only admins/owners can generate keys
    if str(message.from_user.id) not in config.ADMINS and str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 You do not have permission to generate keys.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /gen <normal|premium> <quantity>")
        return
    key_type = parts[1].lower()
    try:
        qty = int(parts[2])
    except ValueError:
        bot.reply_to(message, "Quantity must be a number.")
        return
    generated = []
    if key_type == "normal":
        # generate_normal_key and add_key are imported within admin module
        from handlers.admin import generate_normal_key
        for _ in range(qty):
            key = generate_normal_key()
            from handlers.admin import add_key
            add_key(key, "normal", 15)
            generated.append(key)
    elif key_type == "premium":
        from handlers.admin import generate_premium_key
        for _ in range(qty):
            key = generate_premium_key()
            from handlers.admin import add_key
            add_key(key, "premium", 35)
            generated.append(key)
    else:
        bot.reply_to(message, "Key type must be either 'normal' or 'premium'.")
        return
    if generated:
        text = f"Redeem Generated ✅➔ `<code>{generated[0]}</code>`\n"
        for key in generated[1:]:
            text += f"➔ `<code>{key}</code>`\n"
        text += "\nYou can redeem these codes using: /redeem <Key>"
    else:
        text = "No keys generated."
    bot.reply_to(message, text, parse_mode="Markdown")
    log_event(bot, "key_generation", f"Admin {message.from_user.id} generated {qty} {key_type} keys.")

@bot.message_handler(commands=["redeem"])
def redeem_command(message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /redeem <key>")
        return
    key = parts[1].strip()
    result = claim_key_in_db(key, user_id)
    bot.reply_to(message, result)
    log_event(bot, "key_claim", f"User {user_id} redeemed key {key}. Result: {result}")

@bot.message_handler(commands=["tutorial"])
def tutorial_command(message):
    text = (
        "📖 Tutorial\n"
        "1. Every new user starts with 20 points (each account claim costs dynamic points).\n"
        "2. To claim an account, go to the Rewards section.\n"
        "3. Earn more points by referrals or redeeming keys.\n"
        "4. Use /report to report issues.\n"
        "5. Daily check-ins and missions offer bonus points.\n"
        "Admins can generate keys with /gen, lend points with /lend, and adjust pricing with /Uprice and /Rpoints.\n"
        "Enjoy and good luck! 😊"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["lend"])
def lend_command(message):
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 You don't have permission to use this command.")
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /lend <user_id> <points>")
        return
    user_id = parts[1]
    try:
        points = int(parts[2])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    result = lend_points(message.from_user.id, user_id, points)
    bot.reply_to(message, result)
    log_event(bot, "lend", f"Admin {message.from_user.id} lent {points} pts to user {user_id}.")

@bot.message_handler(commands=["Uprice"])
def uprice_command(message):
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 Access denied.")
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /Uprice <points>")
        return
    try:
        price = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    update_account_claim_cost(price)
    bot.reply_to(message, f"Account claim cost updated to {price} points.")
    log_event(bot, "config", f"Owner {message.from_user.id} updated account claim cost to {price} pts.")

@bot.message_handler(commands=["Rpoints"])
def rpoints_command(message):
    if str(message.from_user.id) not in config.OWNERS:
        bot.reply_to(message, "🚫 Access denied.")
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /Rpoints <points>")
        return
    try:
        bonus = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Points must be a number.")
        return
    update_referral_bonus(bonus)
    bot.reply_to(message, f"Referral bonus updated to {bonus} points.")
    log_event(bot, "config", f"Owner {message.from_user.id} updated referral bonus to {bonus} pts.")

@bot.message_handler(commands=["report"])
def report_command(message):
    msg = bot.send_message(message.chat.id, "📝 Please type your report message (text and optional screenshot together):")
    bot.register_next_step_handler(msg, process_report)

def process_report(message):
    report_text = message.text
    for owner in config.OWNERS:
        try:
            bot.send_message(owner, f"🚨 Report from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{report_text}")
        except Exception as e:
            print(f"Error forwarding report to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")
    log_event(bot, "report", f"User {message.from_user.id} submitted a report.")

# --- Callback Query Handlers ---

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def callback_back_main(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print("Error deleting message:", e)
    from handlers.main_menu import send_main_menu
    send_main_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_rewards")
def callback_menu_rewards(call):
    send_rewards_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reward_"))
def callback_reward(call):
    platform_name = call.data.split("reward_")[1]
    handle_platform_selection(bot, call, platform_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith("claim_"))
def callback_claim(call):
    platform_name = call.data.split("claim_")[1]
    claim_account(bot, call, platform_name)

@bot.callback_query_handler(func=lambda call: call.data == "menu_account")
def callback_menu_account(call):
    from handlers.account_info import send_account_info
    send_account_info(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == "menu_referral")
def callback_menu_referral(call):
    send_referral_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "get_ref_link")
def callback_get_ref_link(call):
    ref_link = get_referral_link(call.from_user.id)
    bot.answer_callback_query(call.id, "Referral link generated!")
    bot.send_message(call.message.chat.id, f"Your referral link:\n{ref_link}", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "menu_review")
def callback_menu_review(call):
    prompt_review(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == "menu_report")
def callback_menu_report(call):
    msg = bot.send_message(call.message.chat.id, "📝 Please type your report message (text and optional screenshot):")
    bot.register_next_step_handler(msg, process_report)

@bot.callback_query_handler(func=lambda call: call.data == "menu_admin")
def callback_menu_admin(call):
    send_admin_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify"))
def callback_verify(call):
    handle_verification_callback(bot, call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin"))
def callback_admin(call):
    admin_callback_handler(bot, call)

bot.polling(none_stop=True)
