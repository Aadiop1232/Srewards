# handlers/main_menu.py
from telebot import types
from handlers.admin import is_admin  # Ensure is_admin is imported

def send_main_menu(bot, update):
    """
    Sends the main menu with options.
    The admin panel button will appear if the user is an admin.
    """
    # Try to extract the chat_id and user info from different update types.
    if hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        user = update.message.from_user
    elif hasattr(update, "data"):  # For CallbackQuery objects
        chat_id = update.message.chat.id
        user = update.from_user
    else:
        chat_id = update.chat.id
        user = update.from_user

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🎉 Rewards", callback_data="menu_rewards"),
        types.InlineKeyboardButton("👥 Info", callback_data="menu_info"),
        types.InlineKeyboardButton("🤝 Referral", callback_data="menu_referral")
    )
    markup.add(
        types.InlineKeyboardButton("📠 Review", callback_data="menu_review")
    )
    # Include Admin Panel button if the user is admin.
    if is_admin(user):
        markup.add(types.InlineKeyboardButton("Admin Panel", callback_data="menu_admin"))
    bot.send_message(chat_id, "Main Menu\nPlease choose an option:", reply_markup=markup)
    
