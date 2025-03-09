# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Sends the account information for the user who triggered the update.
    Always uses update.from_user.id as the unique Telegram ID.
    Uses HTML formatting with newline characters.
    """
    # Use update.from_user.id (this should be unique for every user)
    telegram_id = str(update.from_user.id)
    # For the chat id, if update.message exists, use its chat id; otherwise, fallback to telegram_id.
    chat_id = update.message.chat.id if hasattr(update, "message") and update.message else telegram_id

    # Debug print to check which Telegram ID is being used.
    print("DEBUG: Account info requested by telegram_id:", telegram_id)

    # Retrieve user data. If user is not found, register them.
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
    
