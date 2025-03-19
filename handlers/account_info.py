# account_info.py

from db import get_user
from handlers.admin import is_admin

def send_account_info(bot, call):
    """
    Sends the user's account info in your fancy ASCII style.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if not user:
        bot.send_message(call.message.chat.id, "User not found. Please /start the bot first.")
        return

    username = user.get("username", "N/A")
    join_date = user.get("join_date", "N/A")
    balance = user.get("points", 0)
    referrals = user.get("referrals", 0)

    text = (
        "╭━━━✦❘༻👤 ACCOUNT INFO ༺❘✦━━━╮\n"
        "┃\n"
        f"┃ ✧ Username: {username}\n"
        f"┃ ✧ User ID: {user_id}\n"
        f"┃ ✧ Join Date: {join_date}\n"
        f"┃ ✧ Balance: {balance}\n"
        f"┃ ✧ Total Referrals: {referrals}\n"
        "┃\n"
        "╰━━━━━━━✦✧✦━━━━━━━╯"
    )

    # If this came from a callback, we can either edit or send a new message
    # For simplicity, let's just send a new message
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")
