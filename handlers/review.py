import telebot
import config
from db import add_review
from handlers.logs import log_event

# Global mappings for reports
REPORT_MAPPING = {}    # maps forwarded report message id -> original reporter's chat id
CLAIMED_REPORTS = {}   # maps forwarded report message id -> admin id who claimed it

def prompt_review(bot, message):
    msg = bot.send_message(message.chat.id, "💬 Please send your review or suggestion:")
    bot.register_next_step_handler(msg, process_review, bot)

def process_review(bot, message):
    review_text = message.text
    add_review(str(message.from_user.id), review_text)
    for owner in config.OWNERS:
        try:
            forwarded = bot.send_message(
                owner,
                f"📢 Review from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{review_text}",
                parse_mode="Markdown"
            )
            # Optionally, you could map forwarded reviews if you want to allow live replies.
            REPORT_MAPPING[forwarded.message_id] = message.chat.id
        except Exception as e:
            print(f"Error sending review to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Thank you for your feedback!", parse_mode="Markdown")
    log_event(bot, "REVIEW", f"[REVIEW] {message.from_user.username or message.from_user.first_name} ({message.from_user.id}) sent a review.", user=message.from_user)

def process_report(bot, message):
    # Combine text if there is a caption (for media) and text
    report_text = ""
    if message.content_type in ["photo", "document"]:
        report_text = message.caption or ""
    if hasattr(message, "text") and message.text:
        if report_text:
            report_text = f"{report_text}\n{message.text}"
        else:
            report_text = message.text

    user = message.from_user
    username = user.username if user.username else user.first_name
    report_header = f"📣 Report from {username} ({user.id}):\n\n"

    # Build inline keyboard with Claim and Close buttons.
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("Claim Report", callback_data="claim_report"),
        telebot.types.InlineKeyboardButton("Close Report", callback_data="close_report")
    )

    # Forward the report to each owner with the inline keyboard.
    for owner in config.OWNERS:
        try:
            if message.content_type == "photo":
                photo_id = message.photo[-1].file_id
                forwarded = bot.send_photo(owner, photo_id, caption=report_header + report_text, parse_mode="HTML", reply_markup=markup)
            elif message.content_type == "document":
                forwarded = bot.send_document(owner, message.document.file_id, caption=report_header + report_text, parse_mode="HTML", reply_markup=markup)
            else:
                forwarded = bot.send_message(owner, report_header + report_text, parse_mode="HTML", reply_markup=markup)
            # Save mapping for this forwarded report.
            REPORT_MAPPING[forwarded.message_id] = message.chat.id
        except Exception as e:
            print(f"Error sending report to owner {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")

def update_report_claim_status(report_msg_id, admin_id):
    if report_msg_id in CLAIMED_REPORTS:
        return False  # Already claimed
    CLAIMED_REPORTS[report_msg_id] = admin_id
    return True

def close_report(report_msg_id):
    if report_msg_id in CLAIMED_REPORTS:
        del CLAIMED_REPORTS[report_msg_id]
    if report_msg_id in REPORT_MAPPING:
        del REPORT_MAPPING[report_msg_id]

def handle_report_callback(bot, call):
    """
    Handles callback queries for reports.
    Expects callback data to be either "claim_report" or "close_report".
    """
    if call.data == "claim_report":
        report_msg_id = call.message.message_id
        if report_msg_id in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report already claimed.")
        else:
            admin_id = call.from_user.id
            success = update_report_claim_status(report_msg_id, admin_id)
            if success:
                bot.answer_callback_query(call.id, "Report claimed.")
                reporter_chat = REPORT_MAPPING.get(report_msg_id)
                if reporter_chat:
                    admin_name = call.from_user.username or call.from_user.first_name
                    bot.send_message(reporter_chat, f"Your report is now being handled by {admin_name} ({admin_id}).")
            else:
                bot.answer_callback_query(call.id, "Failed to claim report.")
    elif call.data == "close_report":
        report_msg_id = call.message.message_id
        if report_msg_id not in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report not claimed yet.")
        else:
            admin_id = CLAIMED_REPORTS[report_msg_id]
            bot.answer_callback_query(call.id, "Report closed.")
            reporter_chat = REPORT_MAPPING.get(report_msg_id)
            if reporter_chat:
                admin_name = call.from_user.username or call.from_user.first_name
                bot.send_message(reporter_chat, f"Your report has been closed by {admin_name} ({admin_id}).")
            close_report(report_msg_id)
