import telebot
import config
from db import get_user, clear_pending_referral, add_referral, update_user_verified
from handlers.logs import log_event
from handlers.verification import check_channel_membership

def extract_referral_code(message):
    """
    If the message text contains a referral code in the format "ref_XXXX",
    this function returns the code (i.e. XXXX); otherwise, it returns None.
    """
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(telegram_id, bot_instance):
    """
    Processes the referral bonus for a newly verified user.
    This function first checks whether the user has joined all required channels.
    Only if the check passes, the user is marked as verified, the referral is added,
    and the pending referral is cleared.
    """
    user = get_user(str(telegram_id))
    if user and user.get("pending_referrer"):
        # Check channel membership (convert telegram_id to int if needed)
        if check_channel_membership(bot_instance, int(telegram_id)):
            update_user_verified(str(telegram_id))
            add_referral(user.get("pending_referrer"), user.get("telegram_id"))
            clear_pending_referral(str(telegram_id))
            try:
                bot_instance.send_message(
                    int(user.get("pending_referrer")),
                    "🎉 Referral completed! You earned 10 points!",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error notifying referrer: {e}")
            log_event(bot_instance, "referral", 
                      f"User {user.get('pending_referrer')} referred user {user.get('telegram_id')}.")
        else:
            # The referral bonus is not awarded if the user hasn't joined all required channels.
            print("User has not joined the required channels. Referral bonus not awarded.")

def send_referral_menu(bot, message):
    """
    Sends the referral menu to the user with their referral link.
    """
    telegram_id = str(message.from_user.id)
    text = """🔗 REFERRAL SYSTEM 🔗
══════ ⌁ ══════
💡 Your referral link is below!
🎁 Earn 10 Points per referral!
══════ ⌁ ══════
"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

def get_referral_link(telegram_id):
    """
    Generates and returns a referral link for the given Telegram user ID.
    """
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{telegram_id}"
