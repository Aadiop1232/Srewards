# handlers/referral.py
from telebot import types
import config
from db import get_user, add_referral, clear_pending_referral

def extract_referral_code(message):
    """
    Extracts the referral code from the /start message.
    Expected format: /start ref_<referrer_id>
    Returns the referrer_id as a string or None.
    """
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(user_id):
    """
    After the user verifies, check if they have a pending referral.
    If yes, award the referrer 4 points and clear the pending referral.
    """
    user = get_user(str(user_id))
    # User tuple: (user_id, username, join_date, points, referrals, banned, pending_referrer)
    if user and user[6]:
        referrer_id = user[6]
        add_referral(referrer_id, str(user_id))
        clear_pending_referral(str(user_id))

def send_referral_menu(bot, message):
    """
    Displays the referral dashboard showing the user's details.
    If no user record is found, default values are used.
    """
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if user:
        text = (
            f"🔗 *Referral System*\n"
            f"• *Username:* {user[1]}\n"
            f"• *User ID:* {user[0]}\n"
            f"• *Total Referrals:* {user[4]}\n"
            f"• *Points Earned:* {user[3]}"
        )
    else:
        text = (
            f"🔗 *Referral System*\n"
            f"• *Username:* {message.from_user.username or message.from_user.first_name}\n"
            f"• *User ID:* {user_id}\n"
            "• *Total Referrals:* 0\n"
            "• *Points Earned:* 0"
        )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

def get_referral_link(user_id):
    """
    Returns a permanent referral link for the user.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{user_id}"
    
