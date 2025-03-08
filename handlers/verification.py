# handlers/verification.py
import telebot
from telebot import types
import config
from handlers.admin import is_admin

def check_channel_membership(bot, user_id):
    """
    Checks if the user is a member of all required channels.
    Returns True if yes, False otherwise.
    """
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.split("/")[-1]
            member = bot.get_chat_member(channel_username, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception as e:
            print(f"❌ Error checking membership for {channel}: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """
    On every /start, checks if the user is verified.
    Owners and admins are automatically verified.
    If verified, shows the main menu; if not, instructs the user to join channels.
    """
    user_id = message.from_user.id

    # Automatically verify owners/admins
    if is_admin(user_id):
        bot.send_message(message.chat.id, "✨ Welcome, Admin/Owner! You are automatically verified. ✨")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
        return

    # Otherwise, check channel membership
    if check_channel_membership(bot, user_id):
        bot.send_message(message.chat.id, "✅ Verifying user... Verified! 🎉")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
    else:
        text = "🚫 You are not verified! Please join the following channels to use this bot:\n"
        for channel in config.REQUIRED_CHANNELS:
            text += f"👉 {channel}\n"
        bot.send_message(message.chat.id, text)
        
