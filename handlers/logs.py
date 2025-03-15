# handlers/logs.py
import config

def log_event(bot, event_type, message):
    """
    Send a log message to the channel specified in config.LOGS_CHANNEL.
    
    Parameters:
      bot         : The TeleBot instance.
      event_type  : A short string identifying the event (e.g. "referral", "key_claim", "admin", etc.).
      message     : The detailed message to send.
    """
    full_message = f"[{event_type.upper()}] {message}"
    try:
        bot.send_message(config.LOGS_CHANNEL, full_message)
    except Exception as e:
        print(f"Error sending log event: {e}")
