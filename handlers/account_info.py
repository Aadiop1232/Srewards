# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    """
    Primary Account Info Format:
    Shows detailed user information:
      - Username, Internal User ID (8-digit), Join Date, Balance, and Total Referrals.
    This function assumes that the user is already registered.
    """
    telegram_id = str(message.from_user.id)
    user = get_user(telegram_id)
    # No fallback is provided – it must return valid user info.
    text = (
        f"👤 *Account Info*\n"
        f"• *Username:* {user[2]}\n"
        f"• *User ID:* {user[1]}\n"  # internal_id (an 8-digit number)
        f"• *Join Date:* {user[3]}\n"
        f"• *Balance:* {user[4]} points\n"
        f"• *Total Referrals:* {user[5]}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

def send_account_info_alt(bot, message):
    """
    Alternative Account Info Format:
    A concise display of user information.
    """
    telegram_id = str(message.from_user.id)
    user = get_user(telegram_id)
    text = (
        f"👤 *User:* {user[2]}\n"
        f"ID: {user[1]}\n"
        f"Balance: {user[4]} pts | Referrals: {user[5]}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
