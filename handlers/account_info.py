# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends the account information for the user who triggered the update.
    This function works with both Message and CallbackQuery objects and
    uses HTML formatting.
    """
    # Determine chat_id and telegram_id from the update.
    # For messages:
    if hasattr(update, "message") and update.message:
        chat_id = update.message.chat.id
        telegram_id = str(update.message.from_user.id)
    # For callback queries:
    elif hasattr(update, "from_user") and hasattr(update, "message"):
        chat_id = update.message.chat.id
        telegram_id = str(update.from_user.id)
    else:
        # Fallback if nothing is available (should not happen)
        chat_id = update.from_user.id
        telegram_id = str(update.from_user.id)
    
    # Ensure the user is registered. If not, register on the fly.
    user = get_user(telegram_id)
    if not user:
        add_user(
            telegram_id,
            update.from_user.username or update.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    
    # Expected user schema:
    # (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    text = (
        f"<b>👤 Account Info 😁</b>\n"
        f"• <b>Username:</b> {user[2]}\n"
        f"• <b>User ID:</b> {user[1]}\n"
        f"• <b>Join Date:</b> {user[3]}\n"
        f"• <b>Balance:</b> {user[4]} points\n"
        f"• <b>Total Referrals:</b> {user[5]}"
    )
    
    bot.send_message(chat_id, text, parse_mode="HTML")
    
