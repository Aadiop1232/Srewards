import telebot
from db import get_user
from telebot import types

def send_account_info(bot, message):
    """
    Send the account information for the user, including username, points, and referrals.
    """
    user_id = str(message.from_user.id)
    user = get_user(user_id)

    if user:
        # Get user data from the database
        username = user[1] if user[1] else "No username"
        join_date = user[2] if user[2] else "N/A"
        points = user[3] if user[3] else 0
        referrals = user[4] if user[4] else 0
        status = "Banned" if user[5] == 1 else "Active"
        
        # Build the account info message
        text = f"<b>Account Info:</b>\n"
        text += f"Username: {username}\n"
        text += f"Join Date: {join_date}\n"
        text += f"Points: {points}\n"
        text += f"Referrals: {referrals}\n"
        text += f"Status: {status}\n"
        
        # Send the account info
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Error: User not found.")
        
