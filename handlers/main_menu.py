from telebot import types
from handlers.admin import is_admin

def send_main_menu(bot, update):
    # Try to extract chat_id and user from the update.
    if hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        user = update.message.from_user
    elif hasattr(update, "from_user") and update.from_user:
        # For CallbackQuery objects, use update.from_user.
        chat_id = update.message.chat.id if hasattr(update, "message") and update.message else update.chat.id
        user = update.from_user
    else:
        chat_id = update.chat.id
        user = update.from_user

    # Optionally, you may also retrieve the user record from your database:
    # from db import get_user
    # user_record = get_user(user.id)
    # and then check admin status using is_admin(user_record)
    # For now, we check directly with the user object.
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🎉 Rewards", callback_data="menu_rewards"),
        types.InlineKeyboardButton("👥 Info", callback_data="menu_info"),
        types.InlineKeyboardButton("🤝 Referral", callback_data="menu_referral")
    )
    markup.add(
        types.InlineKeyboardButton("📠 Review", callback_data="menu_review"),
        types.InlineKeyboardButton("📣 Report", callback_data="menu_report")
    )
    if is_admin(user):
        markup.add(types.InlineKeyboardButton("🔨 Admin Panel", callback_data="menu_admin"))
    bot.send_message(chat_id, "Main Menu\nPlease choose an option:", reply_markup=markup)
