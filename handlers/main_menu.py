import telebot
from telebot import types
from handlers.admin import is_admin

def send_main_menu(bot, message):
    """
    Send the main menu to the user with options such as Rewards, Account Info, Referrals, and Admin Panel.
    """
    user_obj = message.from_user
    markup = types.InlineKeyboardMarkup(row_width=3)

    # Main buttons for all users
    btn_rewards = types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards")
    btn_account = types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account")
    btn_referral = types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral")
    btn_review = types.InlineKeyboardButton("💬 Review", callback_data="menu_review")
    
    # Add buttons to markup
    markup.add(btn_rewards, btn_account, btn_referral, btn_review)
    
    # Add Admin button if user is admin
    if is_admin(user_obj):
        btn_admin = types.InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin")
        markup.add(btn_admin)
    
    # Send the main menu to the user
    bot.send_message(message.chat.id, "<b>📋 Main Menu 📋</b>\nPlease choose an option:", parse_mode="HTML", reply_markup=markup)
    
