import telebot
from db import add_review
import config

def prompt_review(bot, message):
    msg = bot.send_message(message.chat.id, "💬 *Please send your review or suggestion:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_review)

def process_review(message):
    review_text = message.text
    add_review(str(message.from_user.id), review_text)
    bot = telebot.TeleBot(config.TOKEN)
    for owner in config.OWNERS:
        try:
            bot.send_message(owner,
                             f"📢 *Review from {message.from_user.username or message.from_user.first_name}:*\n\n{review_text}",
                             parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Error sending review to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ *Thank you for your feedback!*", parse_mode="Markdown")
    
