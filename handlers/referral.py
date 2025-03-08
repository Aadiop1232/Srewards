# handlers/referral.py
import telebot
import config

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
    Process a verified referral for a user.
    (Placeholder function: implement your database logic here to award referral points.)
    """
    # Example (pseudo-code):
    # user = get_user_from_db(user_id)
    # if user and user.pending_referrer:
    #     award_points_to_referrer(user.pending_referrer)
    #     clear_pending_referral(user_id)
    pass

def send_referral_menu(bot, message):
    """
    Displays the referral system dashboard to the user.
    """
    user_id = str(message.from_user.id)
    text = f"🔗 *Referral System*\nYour referral link is available below."
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

def get_referral_link(user_id):
    """
    Returns the referral link for the given user.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{user_id}"
    
