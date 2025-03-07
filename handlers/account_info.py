# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if user:
        # Assuming the user tuple is (user_id, username, join_date, language, points, referrals)
        text = (f"Username: {user[1]}\n"
                f"User ID: {user[0]}\n"
                f"Join Date: {user[2]}\n"
                f"Language: {user[3]}\n"
                f"Points: {user[4]}\n"
                f"Total Referrals: {user[5]}")
    else:
        text = "No account info found."
    bot.send_message(message.chat.id, text)
  
