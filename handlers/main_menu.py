import telebot
from telebot import types
from handlers.admin import is_admin

def send_main_menu(bot, update):
    if hasattr(update, "message"):
        chat_id = update.message.chat.id
        user_obj = update.from_user
    elif hasattr(update, "data"):  # Callback query
        chat_id = update.message.chat.id
        user_obj = update.from_user
    elif hasattr(update, "chat"):
        chat_id = update.chat.id
        user_obj = update.from_user
    else:
        chat_id = update.message.chat.id
        user_obj = update.from_user

    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_rewards = types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards")
    btn_account = types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account")
    btn_referral = types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral")
    btn_review = types.InlineKeyboardButton("💬 Review", callback_data="menu_review")
    markup.add(btn_rewards, btn_account, btn_referral, btn_review)
    if is_admin(user_obj):
        btn_admin = types.InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin")
        markup.add(btn_admin)
    bot.send_message(chat_id, "<b>📋 Main Menu 📋</b>\nPlease choose an option:", parse_mode="HTML", reply_markup=markup)
