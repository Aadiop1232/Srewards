# handlers/verification.py
import telebot
from telebot import types
import config
from handlers.admin import is_admin

def check_channel_membership(bot, user_id):
    """
    Checks if the user is a member of all required channels.
    """
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.split("/")[-1]
            member = bot.get_chat_member(channel_username, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception as e:
            print(f"Error checking membership for {channel}: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """
    Checks verification on every /start.
    If the user is an admin/owner, they are automatically verified.
    Otherwise, it checks channel membership and either shows the main menu or sends a message listing required channels.
    """
    user_id = message.from_user.id
    if is_admin(user_id):
        bot.send_message(message.chat.id, "Welcome, admin/owner! You are automatically verified.")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
        return

    if check_channel_membership(bot, user_id):
        bot.send_message(message.chat.id, "Verifying user... Verified!")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, message)
    else:
        text = "You are not verified. Please join the following channels to use this bot:\n"
        for channel in config.REQUIRED_CHANNELS:
            text += f"{channel}\n"
        bot.send_message(message.chat.id, text)
        
