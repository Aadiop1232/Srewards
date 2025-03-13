from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    try:
        telegram_id = str(update.from_user.id)
        chat_id = update.message.chat.id if hasattr(update, "message") and update.message else telegram_id
        user = get_user(telegram_id)
        
        if not user:
            add_user(
                telegram_id,
                update.from_user.username or update.from_user.first_name,
                datetime.now().strftime("%Y-%m-%d")
            )
            user = get_user(telegram_id)

        # Ensure user data is valid
        if user:
            text = (
                f"<b>👤 Account Info 😁</b>\n"
                f"• <b>Username:</b> {user[2]}\n"
                f"• <b>User ID:</b> {user[0]}\n"
                f"• <b>Join Date:</b> {user[3]}\n"
                f"• <b>Balance:</b> {user[4]} points\n"
                f"• <b>Total Referrals:</b> {user[5]}"
            )
            bot.send_message(chat_id, text, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "❌ Error: User data is missing or corrupted.", parse_mode="HTML")
    except Exception as e:
        bot.send_message(chat_id, f"❌ An error occurred: {e}", parse_mode="HTML")
        
