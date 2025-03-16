import telebot
import config
from db import get_user, clear_pending_referral, add_referral
from handlers.logs import log_event

def extract_referral_code(message):
    """
    Extract a referral code from the message text.
    Expected format: ref_<referrer_id>
    """
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(telegram_id, bot_instance):
    """
    If the user has a pending referrer, add the referral,
    clear the pending referrer, notify the referrer, and log the event.
    """
    user = get_user(str(telegram_id))
    if user and user.get("pending_referrer"):
        referrer_id = user.get("pending_referrer")
        add_referral(referrer_id, user.get("telegram_id"))
        clear_pending_referral(str(telegram_id))
        try:
            bot_instance.send_message(referrer_id, "🎉 Referral completed! You earned bonus points!", parse_mode="HTML")
        except Exception as e:
            print(f"Error notifying referrer: {e}")
        log_event(bot_instance, "referral", f"User {referrer_id} referred user {user.get('telegram_id')}.")
