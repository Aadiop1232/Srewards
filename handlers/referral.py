import telebot
from db import get_user, add_referral, update_user_points
from telebot import types
import config

def extract_referral_code(message):
    """
    Extract referral code from the message text if it exists.
    A referral code is passed as a query parameter after the bot's username.
    """
    if message.text and message.text.startswith(f"@{config.BOT_USERNAME}"):
        parts = message.text.split()
        if len(parts) > 1:
            referral_code = parts[1].strip()
            return referral_code
    return None

def send_referral_menu(bot, message):
    """
    Send the referral menu to the user.
    Displays the referral link and the number of points they will earn for each referral.
    """
    user_id = str(message.from_user.id)
    ref_link = get_referral_link(user_id)
    text = f"<b>Your referral link:</b>\n{ref_link}\n\n"
    text += "💡 You will earn 4 points for each person who uses your referral link and registers!"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 Share your referral link", url=ref_link))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))

    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def get_referral_link(user_id):
    """
    Generate a referral link for the user.
    The referral link will direct others to the bot and include the user's Telegram ID as a query parameter.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start={user_id}"

def process_verified_referral(user_id):
    """
    Process the referral if the user is verified.
    Adds points and referral counts for the referrer.
    """
    user = get_user(user_id)
    if user and user[6]:  # Check if there is a pending referrer
        referrer_id = user[6]  # Get the pending referrer (the person who referred this user)
        add_referral(referrer_id, user_id)  # Add the referral in the database
        # Award points to the referrer (4 points for each successful referral)
        add_user_points(referrer_id, 4)  # Assuming 4 points for each referral

def add_user_points(user_id, points):
    """
    Add points to a user's account.
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET points = points + ? WHERE telegram_id=?", (points, user_id))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding points: {e}")
        
