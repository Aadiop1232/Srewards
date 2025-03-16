# handlers/review.py
import telebot
from db import add_review
import config
from handlers.logs import log_event

def prompt_review(bot, message):
    """Prompt the user to submit a review or suggestion."""
    msg = bot.send_message(message.chat.id, "💬 Please send your review or suggestion:")
    bot.register_next_step_handler(msg, process_review)

def process_review(message):
    """Process the review and notify owners."""
    review_text = message.text
    add_review(str(message.from_user.id), review_text)
    # Create a new bot instance for sending to owners
    bot_instance = telebot.TeleBot(config.TOKEN)
    for owner in config.OWNERS:
        try:
            bot_instance.send_message(
                owner,
                f"📢 Review from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{review_text}",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error sending review to owner {owner}: {e}")
    bot_instance.send_message(message.chat.id, "✅ Thank you for your feedback!", parse_mode="Markdown")
    log_event(bot_instance, "review", f"Review received from user {message.from_user.id}.")