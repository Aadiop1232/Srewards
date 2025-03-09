import telebot
from telebot import types
from handlers.admin import is_admin

def send_main_menu(bot, message, edit=False):
    user_obj = message.from_user
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Create buttons
    buttons = [
        types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards"),
        types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account"),
        types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral"),
        types.InlineKeyboardButton("💬 Review", callback_data="menu_review")
    ]
    
    # Add admin button if applicable
    if is_admin(user_obj):
        buttons.append(types.InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin"))
    
    # Add buttons in rows
    markup.add(*buttons[:2])
    markup.add(*buttons[2:4])
    if len(buttons) > 4:
        markup.add(buttons[4])
    
    # Add back button
    markup.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="back_main"))
    
    # Edit or send new message
    if edit:
        try:
            bot.edit_message_text(
                "<b>📋 Main Menu 📋</b>\nChoose an option:",
                chat_id=message.chat.id,
                message_id=message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Menu edit error: {e}")
            bot.send_message(
                message.chat.id,
                "<b>📋 Main Menu 📋</b>\nChoose an option:",
                parse_mode="HTML",
                reply_markup=markup
            )
    else:
        bot.send_message(
            message.chat.id,
            "<b>📋 Main Menu 📋</b>\nChoose an option:",
            parse_mode="HTML",
            reply_markup=markup
        )
