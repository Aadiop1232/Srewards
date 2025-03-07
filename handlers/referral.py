# handlers/referral.py
from db import get_user

def send_referral_menu(bot, message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if user:
        text = (f"Username: {user[1]}\n"
                f"User ID: {user[0]}\n"
                f"Total Referrals: {user[5]}\n"
                f"Points Earned: {user[4]}")
    else:
        text = "No referral data available."
    from telebot import types
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Get Referral Link", callback_data="get_ref_link"))
    markup.add(types.InlineKeyboardButton("Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

def get_referral_link(user_id):
    # Generate a referral link; adjust YourBotName accordingly.
    return f"https://t.me/YourBotName?start=ref_{user_id}"
  
