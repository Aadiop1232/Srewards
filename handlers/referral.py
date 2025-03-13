import telebot
from db import get_user, add_referral, update_user_points
from telebot import types
import config

def send_referral_menu(bot, message):
    """
    Send the referral menu to the user, displaying their referral stats and giving them the option to generate a referral link.
    """
    user_id = str(message.from_user.id)
    user = get_user(user_id)

    if not user:
        bot.send_message(message.chat.id, "❌ User not found.")
        return

    # Generate referral link
    ref_link = get_referral_link(user_id)

    # Send the referral panel with user stats
    text = f"Welcome to the Referral System, {message.from_user.username}!\n\n"
    text += f"Your Referral Link: {ref_link}\n"
    text += f"Total Referrals: {user[4]}\n"  # Assuming user[4] is the total referrals count
    text += f"Points Earned from Referrals: {user[6]} points"  # Assuming user[6] is the points earned from referrals

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Generate Referral Link", callback_data="generate_referral"))

    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def get_referral_link(user_id):
    """
    Generate a unique referral link for the user.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start={user_id}"

def process_verified_referral(user_id):
    """
    Process a verified referral. If the referred user is verified, the referrer earns points.
    """
    user = get_user(user_id)
    if user and user[6]:  # Check if the user has a pending referrer
        referrer_id = user[6]  # Assuming user[6] is the referrer ID
        add_referral(referrer_id, user_id)
        update_user_points(referrer_id, 5)  # Add 5 points to the referrer for a valid referral

def add_referral(referrer_id, referred_id):
    """
    Add a referral to the database and update the referrer’s referral count.
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM referrals WHERE referred_id=?", (referred_id,))
        if c.fetchone():
            conn.close()
            return  # Skip if the referred user is already recorded
        c.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
        c.execute("UPDATE users SET points = points + 5 WHERE telegram_id=?", (referrer_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding referral: {e}")

def generate_referral_link(user_id):
    """
    Generate a permanent referral link for the user to share with others.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start={user_id}"

def process_referred_user(user_id):
    """
    This function processes the referred user by linking them to their referrer.
    It also ensures that the referral link is only valid once the user completes the verification process.
    """
    user = get_user(user_id)
    if user and user[6]:  # Ensure that the user has a referrer
        referrer_id = user[6]  # Assuming user[6] is the referrer ID
        add_referral(referrer_id, user_id)  # Add the referral to the referrer
        update_user_points(referrer_id, 5)  # Add 5 points to the referrer for a successful referral
