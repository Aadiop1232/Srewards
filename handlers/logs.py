# logs.py

import telebot
import config
from db import log_admin_action

def log_event(bot, action, message, user=None):
    """
    Logs an event both to the console and to the admin_logs table in the database.
    Shows username + user ID if 'user' is provided.
    """

    if user:
        # If we have a user object, include their username and user ID
        username = user.username or user.first_name
        user_id_str = str(user.id)
        full_message = f"{message} [User: {username} ({user_id_str})]"
        admin_id = user_id_str
    else:
        # If no user is provided, we just log the raw message
        full_message = message
        admin_id = "N/A"

    # Print to console
    print(f"[{action}] {full_message}")

    # Save to admin_logs table via db.py
    # 'log_admin_action' typically looks like:
    #   def log_admin_action(admin_id, action): ...
    # Make sure your db.py has that function, or rename as needed.
    log_admin_action(admin_id, full_message)
