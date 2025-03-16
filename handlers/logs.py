# handlers/logs.py
import config

def log_event(bot, event_type, message, user=None):
    """
    Send a log message to the channel defined in config.LOGS_CHANNEL.
    Optionally include user details if provided.
    """
    if user:
        # Use both user ID and username (if available)
        user_info = f"User ID: {user.id}, Username: {user.username or 'N/A'}"
        full_message = f"[{event_type.upper()}] {user_info} - {message}"
    else:
        full_message = f"[{event_type.upper()}] {message}"
    
    try:
        bot.send_message(config.LOGS_CHANNEL, full_message)
    except Exception as e:
        print(f"Error sending log event: {e}")
        
