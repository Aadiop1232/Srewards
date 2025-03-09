# handlers/referral.py
import telebot
import config
from db import get_user, clear_pending_referral, add_referral

def extract_referral_code(message):
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(telegram_id):
    referred = get_user(str(telegram_id))
    if referred and referred[7]:  # pending_referrer is at index 7 now
        referrer_internal_id = referred[7]
        # Add referral using internal IDs:
        add_referral(referrer_internal_id, referred[1])
        clear_pending_referral(str(telegram_id))
        notification = (
            f"🎉 *Referral Completed!*\n"
            f"You have successfully referred {referred[2]} (Internal ID: {referred[1]}).\n"
            f"You earned 4 points!"
        )
        bot = telebot.TeleBot(config.TOKEN)
        try:
            bot.send_message(referrer_internal_id, notification, parse_mode="Markdown")
        except Exception as e:
            print(f"Error notifying referrer: {e}")

def send_referral_menu(bot, message):
    telegram_id = str(message.from_user.id)
    text = f"🔗 *Referral System*\nYour referral link is available below."
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

def get_referral_link(telegram_id):
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{telegram_id}"
    
