# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends the account information for the user who triggered the update.
    Uses HTML formatting to avoid Markdown parse errors.
    Works with both Message and CallbackQuery objects.
    """
    # Determine the sender from the update
    if hasattr(update, "from_user") and update.from_user:
        telegram_id = str(update.from_user.id)
    else:
        # Fallback – should not occur normally
        telegram_id = "unknown"
    
    # If user is not registered, add them on the fly.
    user = get_user(telegram_id)
    if not user:
        add_user(
            telegram_id,
            update.from_user.username or update.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    
    # Assuming the user schema is:
    # (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    text = (
        f"<b>👤 Account Info 😁</b><br>"
        f"• <b>Username:</b> {user[2]}<br>"
        f"• <b>User ID:</b> {user[1]}<br>"
        f"• <b>Join Date:</b> {user[3]}<br>"
        f"• <b>Balance:</b> {user[4]} points<br>"
        f"• <b>Total Referrals:</b> {user[5]}"
    )
    
    # Determine the proper chat ID for sending the message.
    # For Message objects, update.chat.id works; for CallbackQuery objects, use update.message.chat.id.
    if hasattr(update, "chat") and update.chat:
        chat_id = update.chat.id
    elif hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
    else:
        # Fallback: use telegram_id if no chat id is available.
        chat_id = telegram_id

    bot.send_message(chat_id, text, parse_mode="HTML")
    
