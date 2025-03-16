# handlers/logs.py
import config

def log_event(bot, event_type, message, user=None):
    """
    Sends a log message to the channel defined in config.LOGS_CHANNEL.
    If a user object is provided, include both their user ID and username.
    """
    if user:
        # Use username if exists, otherwise first_name.
        uname = user.username if hasattr(user, "username") and user.username else user.first_name
        user_info = f"User ID: {user.id}, Username: {uname}"
        full_message = f"[{event_type.upper()}] {user_info} - {message}"
    else:
        full_message = f"[{event_type.upper()}] {message}"
    try:
        bot.send_message(config.LOGS_CHANNEL, full_message)
    except Exception as e:
        print(f"Error sending log event: {e}")
        
