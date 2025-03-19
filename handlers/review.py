# review.py

import telebot
import config
from db import add_review
from handlers.logs import log_event

# Global mappings to track forwarded reports
REPORT_MAPPING = {}    # Maps forwarded report message ID to the original reporter's chat ID
CLAIMED_REPORTS = {}   # Maps forwarded report message ID to the admin ID who claimed it

def prompt_review(bot, message):
    """
    Asks the user to send a review or suggestion, and sets up process_review to handle their next message.
    """
    msg = bot.send_message(message.chat.id, "💬 Please send your review or suggestion:")
    # When the user replies, it calls process_review(message, bot)
    bot.register_next_step_handler(msg, process_review, bot)

def process_review(message, bot):
    """
    Saves the user's review in the database, forwards it to owners,
    and sends a confirmation back to the user.
    """
    review_text = message.text or ""
    from_user_id = str(message.from_user.id)

    # Save to DB
    add_review(from_user_id, review_text)

    # Forward the review to owners
    for owner in config.OWNERS:
        try:
            forwarded = bot.send_message(
                owner,
                f"📢 Review from {message.from_user.username or message.from_user.first_name} ({from_user_id}):\n\n{review_text}",
                parse_mode="HTML"
            )
            # Track who originally sent this, if you want to support live chat replies
            REPORT_MAPPING[forwarded.message_id] = message.chat.id
        except Exception as e:
            print(f"Error sending review to owner {owner}: {e}")

    # Acknowledge success
    bot.send_message(message.chat.id, "✅ Thank you for your feedback!", parse_mode="Markdown")

    # Log the event
    log_event(bot, "REVIEW",
              f"[REVIEW] {message.from_user.username or message.from_user.first_name} ({from_user_id}) sent a review.",
              user=message.from_user)

def process_report(message, bot):
    """
    Processes a user-submitted report (text, photo, or document),
    forwards it to all owners with inline buttons for admins to claim or close it.
    """
    report_text = ""
    # If the user attached a photo or document, set 'report_text' to message.caption
    if message.content_type in ["photo", "document"]:
        report_text = message.caption or ""

    # If the user typed text, combine it with the above (or just set it)
    if hasattr(message, "text") and message.text:
        if report_text:
            report_text += f"\n{message.text}"
        else:
            report_text = message.text

    user = message.from_user
    username = user.username if user.username else user.first_name

    report_header = f"📣 Report from {username} ({user.id}):\n\n"

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("Claim Report", callback_data="claim_report"),
        telebot.types.InlineKeyboardButton("Close Report", callback_data="close_report")
    )

    # Forward to owners
    for owner in config.OWNERS:
        try:
            if message.content_type == "photo":
                photo_id = message.photo[-1].file_id
                forwarded = bot.send_photo(
                    owner,
                    photo_id,
                    caption=report_header + report_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            elif message.content_type == "document":
                forwarded = bot.send_document(
                    owner,
                    message.document.file_id,
                    caption=report_header + report_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                forwarded = bot.send_message(
                    owner,
                    report_header + report_text,
                    parse_mode="HTML",
                    reply_markup=markup
                )

            # Remember who originally sent the report
            REPORT_MAPPING[forwarded.message_id] = message.chat.id

        except Exception as e:
            print(f"Error sending report to owner {owner}: {e}")

    # Confirm to the user
    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")

def handle_report_callback(bot, call):
    """
    Handles the 'Claim Report' and 'Close Report' buttons that owners use on forwarded reports.
    """
    if call.data == "claim_report":
        report_msg_id = call.message.message_id
        if report_msg_id in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report already claimed.")
        else:
            admin_id = call.from_user.id
            CLAIMED_REPORTS[report_msg_id] = admin_id
            bot.answer_callback_query(call.id, "Report claimed.")

            # Notify the original reporter
            reporter_chat = REPORT_MAPPING.get(report_msg_id)
            if reporter_chat:
                admin_name = call.from_user.username or call.from_user.first_name
                bot.send_message(reporter_chat, f"Your report is now being handled by {admin_name} ({admin_id}).")

    elif call.data == "close_report":
        report_msg_id = call.message.message_id
        if report_msg_id not in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report not claimed yet.")
        else:
            admin_id = CLAIMED_REPORTS[report_msg_id]
            bot.answer_callback_query(call.id, "Report closed.")

            # Notify the original reporter
            reporter_chat = REPORT_MAPPING.get(report_msg_id)
            if reporter_chat:
                admin_name = call.from_user.username or call.from_user.first_name
                bot.send_message(reporter_chat, f"Your report has been closed by {admin_name} ({admin_id}).")

            # Clean up references
            if report_msg_id in CLAIMED_REPORTS:
                del CLAIMED_REPORTS[report_msg_id]
            if report_msg_id in REPORT_MAPPING:
                del REPORT_MAPPING[report_msg_id]
