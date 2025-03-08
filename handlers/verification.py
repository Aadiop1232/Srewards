# handlers/verification.py
import telebot
from telebot import types
import config
from handlers.admin import is_admin

def check_channel_membership(bot, user_id):
    """
    Checks if the user is a member of all required channels.
    Returns True if yes; False otherwise.
    """
    for channel in config.REQUIRED_CHANNELS:
        try:
            # Extract the channel username from the URL and prepend '@'
            channel_username = channel.split("/")[-1]
            chat_id = "@" + channel_username
            member = bot.get_chat_member(chat_id, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception as e:
            print(f"❌ Error checking membership for {channel}: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """
    On every /start, automatically checks if the user is verified.
    Owners and admins are auto‑verified. Others see an attractive message with inline channel buttons and a "✅ Verify" button.
    """
    user_id = message.from_user.id

    # Auto-verify for owners/admins.
    if is_admin(user_id):
        bot.send_message(message.chat.id, "✨ Welcome, Admin/Owner! You are automatically verified! ✨")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
        return

    # Check channel membership.
    if check_channel_membership(bot, user_id):
        bot.send_message(message.chat.id, "✅ You are verified! 🎉")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
    else:
        text = "🚫 You are not verified! Please join the following channels to use this bot:"
        markup = types.InlineKeyboardMarkup(row_width=2)
        for channel in config.REQUIRED_CHANNELS:
            btn = types.InlineKeyboardButton(text=f"👉 {channel.split('/')[-1]}", url=channel)
            markup.add(btn)
        # Add a verify button.
        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        bot.send_message(message.chat.id, text, reply_markup=markup)

def handle_verification_callback(bot, call):
    """
    When the user clicks the "✅ Verify" button, re-check channel membership.
    If verified, show the main menu; otherwise, prompt them to join channels.
    """
    user_id = call.from_user.id
    if check_channel_membership(bot, user_id):
        bot.answer_callback_query(call.id, "✅ Verification successful! 🎉")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "🚫 Verification failed. Please join all channels and try again.")
        
