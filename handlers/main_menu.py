# handlers/main_menu.py
import telebot
from telebot import types

def send_main_menu(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_rewards = types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards")
    btn_account = types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account")
    btn_referral = types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral")
    btn_review = types.InlineKeyboardButton("💬 Review", callback_data="menu_review")
    btn_admin = types.InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin")
    markup.add(btn_rewards, btn_account, btn_referral, btn_review, btn_admin)
    bot.send_message(message.chat.id, "📋 *Main Menu* 📋\nPlease choose an option:", parse_mode="Markdown", reply_markup=markup)
    
