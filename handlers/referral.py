import telebot
import config
from db import get_user, clear_pending_referral, add_referral, update_user_verified
from handlers.logs import log_event

def extract_referral_code(message):
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(telegram_id, bot_instance):
    user = get_user(str(telegram_id))
    if user and user.get("pending_referrer") and not user.get("verified"):
        referrer_id = user.get("pending_referrer")
        update_user_verified(str(telegram_id))
        add_referral(referrer_id, user.get("telegram_id"))
        clear_pending_referral(str(telegram_id))
        try:
            bot_instance.send_message(
                int(referrer_id),
                "🎉 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱! 🎉\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "You earned 10 points!\n"
                "━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error notifying referrer: {e}")
        log_event(bot_instance, "referral", f"User {referrer_id} referred user {user.get('telegram_id')}.")

def send_referral_menu(bot, message):
    telegram_id = str(message.from_user.id)
    text = """🔗 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗦𝘆𝘀𝘁𝗲𝗺 🔗
══════ ⌁ ══════
💡 Your referral link is below!
🎁 Earn 🎯 10 Points per referral!
══════ ⌁ ══════
"""
    # Create the markup
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))

    # Send the referral message
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")

def get_referral_link(telegram_id):
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{telegram_id}"
