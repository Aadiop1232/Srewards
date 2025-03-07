# handlers/verification.py
import telebot
from telebot import types
import config

def check_channel_membership(bot, user_id):
    # Verify membership in all required channels
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.split("/")[-1]
            member = bot.get_chat_member(channel_username, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except Exception:
            return False
    return True

def send_verification(bot, message):
    user = message.from_user
    text = f"Hey {user.first_name or user.username}, Welcome To Shadow Rewards Bot!\nPlease verify yourself by joining the below channels."
    markup = types.InlineKeyboardMarkup(row_width=2)
    for channel in config.REQUIRED_CHANNELS:
        btn = types.InlineKeyboardButton(text=channel.split("/")[-1], url=channel)
        markup.add(btn)
    markup.add(types.InlineKeyboardButton("Verify", callback_data="verify"))
    try:
        with open("welcome.jpg", "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, text, reply_markup=markup)

def handle_verification_callback(bot, call):
    user_id = call.from_user.id
    if check_channel_membership(bot, user_id):
        bot.answer_callback_query(call.id, "Verification successful!")
        from handlers.main_menu import send_main_menu
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "Please join all required channels to verify.")
