# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends the account information for the user who triggered the update.
    This version displays the sender's Telegram user ID (from_user.id) as the User ID.
    Works with both Message and CallbackQuery objects.
    """
    # Retrieve the sender's Telegram ID from update.from_user
    telegram_id = str(update.from_user.id)
    
    # Determine chat_id: if update has message, use its chat id; otherwise, use telegram_id.
    chat_id = update.message.chat.id if hasattr(update, "message") and update.message else telegram_id

    # Retrieve user info from the database; if not registered, add the user on the fly.
    user = get_user(telegram_id)
    if not user:
        add_user(
            telegram_id,
            update.from_user.username or update.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    
    # Database schema for users is assumed to be:
    # (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    # We now display only the Telegram ID (user[0]) as the "User ID".
    text = (
        f"<b>👤 Account Info 😁</b>\n"
        f"• <b>Username:</b> {user[2]}\n"
        f"• <b>User ID:</b> {user[0]}\n"
        f"• <b>Join Date:</b> {user[3]}\n"
        f"• <b>Balance:</b> {user[4]} points\n"
        f"• <b>Total Referrals:</b> {user[5]}"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")
    
