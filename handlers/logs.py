# handlers/logs.py
import config

def log_event(bot, event_type, message):
    """
    Send a log message to the channel defined in config.LOGS_CHANNEL.
    """
    full_message = f"[{event_type.upper()}] {message}"
    try:
        bot.send_message(config.LOGS_CHANNEL, full_message)
    except Exception as e:
        print(f"Error sending log event: {e}")
