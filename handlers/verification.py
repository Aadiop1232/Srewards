# handlers/verification.py
import telebot
from telebot import types
import config
from handlers.admin import is_admin
from handlers.main_menu import send_main_menu

def check_channel_membership(bot, user_id):
    """
    Check if a user is a member of all required channels.
    """
    for channel in config.REQUIRED_CHANNELS:
        try:
            # Extract the channel username from the URL.
            channel_username = channel.rstrip('/').split("/")[-1]
            chat = bot.get_chat("@" + channel_username)
            # Ensure the bot is an admin in the channel (needed for reliable membership checking).
            bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
            if bot_member.status not in ["administrator", "creator"]:
                print(f"Bot is not admin in {channel}")
                return False
            # Check the user's membership status.
            user_member = bot.get_chat_member(chat.id, user_id)
            if user_member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception as e:
            print(f"Error checking membership for {channel}: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """
    Sends a verification message to the user.
    Admins bypass verification.
    If the user is verified (i.e. a member of all required channels), the main menu is shown.
    Otherwise, the user is prompted to join the required channels.
    """
    if is_admin(message.from_user):
        bot.send_message(message.chat.id, "✨ Welcome, Admin/Owner! You are automatically verified! ✨")
        send_main_menu(bot, message)
        return
    if check_channel_membership(bot, message.from_user.id):
        bot.send_message(message.chat.id, "✅ You are verified! 🎉")
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
    Handles the callback from the verification button.
    Rechecks channel membership and shows the main menu if verified.
    """
    if check_channel_membership(bot, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verification successful! 🎉")
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "🚫 Verification failed. Please join all channels and try again.")
