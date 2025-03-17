# handlers/review.py
import telebot
import config
from db import add_review
from handlers.logs import log_event

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
    Process a report from the user and forward it to the owners.
    This function supports text reports as well as media (photo or document) with captions.
    """
    # Combine caption and text if available.
    report_text = ""
    if message.content_type in ["photo", "document"]:
        report_text = message.caption or ""
    if hasattr(message, "text") and message.text:
        # If there's a caption, append the text; otherwise, use it.
        if report_text:
            report_text = f"{report_text}\n{message.text}"
        else:
            report_text = message.text

    user = message.from_user
    username = user.username if user.username else user.first_name
    report_header = f"Report from {username} ({user.id}):\n\n"

    for owner in config.OWNERS:
        try:
            if message.content_type == "photo":
                # Use highest-resolution photo.
                photo_id = message.photo[-1].file_id
                bot.send_photo(owner, photo_id, caption=report_header + report_text, parse_mode="HTML")
            elif message.content_type == "document":
                bot.send_document(owner, message.document.file_id, caption=report_header + report_text, parse_mode="HTML")
            else:
                bot.send_message(owner, report_header + report_text, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending report to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")
    
