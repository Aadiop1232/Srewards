import telebot
import config
from db import get_user, clear_pending_referral, add_referral

def extract_referral_code(message):
    if message.text and "ref_" in message.text:
        for part in message.text.split():
            if part.startswith("ref_"):
                return part[len("ref_"):]
    return None

def process_verified_referral(telegram_id, bot_instance):
    referred = get_user(str(telegram_id))
    if referred and referred[6]:
        referrer_id = referred[6]
        add_referral(referrer_id, referred[0])
        clear_pending_referral(str(telegram_id))
        try:
            bot_instance.send_message(referrer_id, "<b>🎉 Referral completed!</b> You earned 4 points.", parse_mode="HTML")
        except Exception as e:
            print(f"Error notifying referrer: {e}")

def send_referral_menu(bot, message):
    telegram_id = str(message.from_user.id)
    text = "🔗 <b>Referral System 😁</b>\nYour referral link is below."
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌟 Get Referral Link", callback_data="get_ref_link"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def get_referral_link(telegram_id):
    return f"https://t.me/{config.BOT_USERNAME}?start=ref_{telegram_id}"
    
