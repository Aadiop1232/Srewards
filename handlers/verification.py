# handlers/verification.py
import telebot
from telebot import types
import config
from handlers.admin import is_admin

def check_channel_membership(bot, user_id):
    """
    Checks if the user is a member of all required channels.
    If an error is raised stating "member list is inaccessible," we skip that channel's check.
    """
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.rstrip('/').split("/")[-1]
            # Call get_chat_member directly using "@" + username.
            member = bot.get_chat_member("@" + channel_username, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception as e:
            err = str(e).lower()
            if "inaccessible" in err:
                # If the error indicates that the member list is inaccessible, assume verification passes.
                continue
            print(f"❌ Error checking membership for {channel}: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """
    Auto‑verifies owners/admins; otherwise, sends channel join buttons with a Verify button.
    """
    user_id = message.from_user.id

    if is_admin(user_id):
        bot.send_message(message.chat.id, "✨ Welcome, Admin/Owner! You are automatically verified! ✨")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
        return

    if check_channel_membership(bot, user_id):
        bot.send_message(message.chat.id, "✅ You are verified! 🎉")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
    else:
        text = "🚫 You are not verified! Please join the following channels to use this bot:"
        markup = types.InlineKeyboardMarkup(row_width=2)
        for channel in config.REQUIRED_CHANNELS:
            channel_username = channel.rstrip('/').split("/")[-1]
            btn = types.InlineKeyboardButton(text=f"👉 {channel_username}", url=channel)
            markup.add(btn)
        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        bot.send_message(message.chat.id, text, reply_markup=markup)

def handle_verification_callback(bot, call):
    """
    Re-checks channel membership on Verify button click.
    """
    user_id = call.from_user.id
    if check_channel_membership(bot, user_id):
        bot.answer_callback_query(call.id, "✅ Verification successful! 🎉")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "🚫 Verification failed. Please join all channels and try again.")
        
