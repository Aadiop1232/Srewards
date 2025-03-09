# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends the account info for the user who triggered the update.
    This function works with both Message and CallbackQuery objects.
    """
    # For both messages and callback queries, use the from_user field.
    user_obj = update.from_user  
    if not user_obj:
        # Fallback if from_user is missing (should not happen for commands)
        bot.send_message(update.message.chat.id, "Unable to retrieve your user information.")
        return

    telegram_id = str(user_obj.id)
    user = get_user(telegram_id)
    if not user:
        # If the user is not registered, register them on the fly.
        add_user(
            telegram_id,
            user_obj.username or user_obj.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    # Assuming user schema: (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    text = (
        f"👤 *Account Info*\n"
        f"• *Username:* {user[2]}\n"
        f"• *User ID:* {user[1]}\n"  # internal_id shown as User ID
        f"• *Join Date:* {user[3]}\n"
        f"• *Balance:* {user[4]} points\n"
        f"• *Total Referrals:* {user[5]}"
    )
    # Determine chat_id – if update is a callback, update.message.chat.id works.
    chat_id = update.message.chat.id if hasattr(update, 'message') else update.message.chat.id
    bot.send_message(chat_id, text, parse_mode="Markdown")
    
