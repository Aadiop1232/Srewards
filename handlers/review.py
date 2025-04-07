# handlers/review.py
import telebot
import config
from db import add_review, add_report, claim_report_in_db, close_report_in_db, check_if_report_claimed, get_user
from handlers.logs import log_event
from telebot import types

def prompt_review(bot, message):
    """
    Prompt the user to send a review or suggestion.
    """
    msg = bot.send_message(message.chat.id, "💬 Please send your review or suggestion:")
    bot.register_next_step_handler(msg, process_review, bot)

def process_review(bot, message):
    """
    Process a review or suggestion from the user.
    """
    review_text = message.text
    add_review(str(message.from_user.id), review_text)
    for owner in config.OWNERS:
        try:
            bot.send_message(owner,
                             f"📢 Review from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{review_text}",
                             parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending review to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Thank you for your feedback!", parse_mode="Markdown")
    log_event(bot, "review", f"Review received from user {message.from_user.id}.", user=message.from_user)

def process_report(bot, message):
    """
    Process the report sent by a user and notify the admins.
    """
    report_text = message.text
    # Create buttons for claiming or closing the report
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Claim Report", callback_data=f"claim_report_{message.from_user.id}"),
        types.InlineKeyboardButton("Close Report", callback_data=f"close_report_{message.from_user.id}")
    )

    for owner in config.OWNERS:
        try:
            bot.send_message(owner, f"📢 Report from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{report_text}", reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending report to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")
    # Save the report to the database as open
    add_report(str(message.from_user.id), report_text)



