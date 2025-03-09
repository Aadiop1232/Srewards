from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    # Handle both Message and CallbackQuery
    if hasattr(update, 'message'):
        message = update.message
        chat_id = message.chat.id
    else:  # CallbackQuery case
        message = update
        chat_id = message.message.chat.id

    telegram_id = str(message.from_user.id)
    
    # Retrieve or create user
    user = get_user(telegram_id)
    if not user:
        add_user(
            telegram_id,
            message.from_user.username or message.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    
    # Build info text
    text = (
        f"<b>👤 Account Info 😁</b>\n"
        f"• <b>Username:</b> {user[2]}\n"
        f"• <b>User ID:</b> {user[0]}\n"
        f"• <b>Join Date:</b> {user[3]}\n"
        f"• <b>Balance:</b> {user[4]} points\n"
        f"• <b>Total Referrals:</b> {user[5]}"
    )
    
    try:
        if hasattr(update, 'callback_query'):
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=update.callback_query.message.message_id,
                parse_mode="HTML"
            )
        else:
            bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Account info error: {e}")
        bot.send_message(chat_id, "❌ Could not display account information.", parse_mode="HTML")
