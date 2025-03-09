# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends account info for the user who triggered the update.
    Works with both Message and CallbackQuery objects.
    """
    # Determine chat_id and telegram_id depending on the type of update.
    if hasattr(update, "chat") and update.chat:
        chat_id = update.chat.id
        telegram_id = str(update.from_user.id)
    elif hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        telegram_id = str(update.from_user.id)
    else:
        # Fallback: use from_user id for both.
        chat_id = str(update.from_user.id)
        telegram_id = str(update.from_user.id)
    
    # Ensure the user is registered.
    user = get_user(telegram_id)
    if not user:
        # If not registered, add the user (registration on the fly)
        add_user(
            telegram_id,
            update.from_user.username or update.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    
    # Assuming user schema: 
    # (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    text = (
        f"👤 *Account Info* 😁\n"
        f"• *Username:* {user[2]}\n"
        f"• *User ID:* {user[1]}\n"
        f"• *Join Date:* {user[3]}\n"
        f"• *Balance:* {user[4]} points\n"
        f"• *Total Referrals:* {user[5]}"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown")
    
