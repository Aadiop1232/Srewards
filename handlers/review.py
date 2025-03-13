import telebot
from db import add_review
import config

def prompt_review(bot, message):
    """
    Prompt the user to send a review or suggestion.
    """
    msg = bot.send_message(message.chat.id, "💬 *Please send your review or suggestion:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_review)

def process_review(message):
    """
    Process the review submitted by the user and send it to the admins.
    """
    review_text = message.text
    user_id = message.from_user.id

    # Add the review to the database
    add_review(str(user_id), review_text)
    
    # Notify the admins about the new review
    bot = telebot.TeleBot(config.TOKEN)
    for owner in config.OWNERS:
        try:
            bot.send_message(owner,
                             f"📢 *Review from {message.from_user.username or message.from_user.first_name}:*\n\n{review_text}",
                             parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Error sending review to owner {owner}: {e}")
    
    # Thank the user for their review
    bot.send_message(message.chat.id, "✅ *Thank you for your feedback!*", parse_mode="Markdown")
    
