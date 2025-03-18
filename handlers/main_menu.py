from telebot import types
from db import get_user
from handlers.admin import is_admin

def send_main_menu(bot, update):
    if hasattr(update, "from_user"):
        user = get_user(str(update.from_user.id))
        chat_id = update.chat.id if hasattr(update, "chat") else update.message.chat.id
    else:
        user = get_user(str(update.message.from_user.id))
        chat_id = update.message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🎉 Rewards", callback_data="menu_rewards"),
        types.InlineKeyboardButton("👥 Info", callback_data="menu_info"),
        types.InlineKeyboardButton("🤝 Referral", callback_data="menu_referral")
    )
    markup.add(
        types.InlineKeyboardButton("📠 Review", callback_data="menu_review"),
        types.InlineKeyboardButton("📣 Report", callback_data="menu_report"),
        types.InlineKeyboardButton("💬 Support", callback_data="menu_support")
    )
    if is_admin(user):
        markup.add(types.InlineKeyboardButton("🔨 Admin Panel", callback_data="menu_admin"))
    bot.send_message(chat_id, "Main Menu\nPlease choose an option:", reply_markup=markup)
