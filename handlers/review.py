# handlers/review.py
import telebot
from db import add_review
import config

def prompt_review(bot, message):
    msg = bot.send_message(message.chat.id, "Please send your review or suggestion:")
    bot.register_next_step_handler(msg, process_review)

def process_review(message):
    review_text = message.text
    add_review(str(message.from_user.id), review_text)
    # Forward review to owner
    import telebot
    bot = telebot.TeleBot(config.TOKEN)
    bot.send_message(config.OWNER_ID,
                     f"Review from {message.from_user.username or message.from_user.first_name}:\n{review_text}")
    bot.send_message(message.chat.id, "Thank you for your feedback!")
  
