import telebot
import config
from db import add_review
from handlers.logs import log_event

REPORT_MAPPING = {}
CLAIMED_REPORTS = {}

def prompt_review(bot, message):
    msg = bot.send_message(message.chat.id, "💬 Please send your review or suggestion:")
    bot.register_next_step_handler(msg, lambda m: process_review(bot, m))

def process_review(bot, message):
    review_text = message.text or ""
    add_review(str(message.from_user.id), review_text)
    for owner in config.OWNERS:
        try:
            fwd = bot.send_message(
                owner,
                f"📢 Review from {message.from_user.username or message.from_user.first_name} ({message.from_user.id}):\n\n{review_text}",
                parse_mode="Markdown"
            )
            REPORT_MAPPING[fwd.message_id] = message.chat.id
        except Exception as e:
            print(f"Error sending review to {owner}: {e}")
    bot.send_message(message.chat.id, "✅ Thank you for your feedback!", parse_mode="Markdown")
    log_event(bot, "REVIEW", f"[REVIEW] {message.from_user.username or message.from_user.first_name} ({message.from_user.id}) sent a review.", user=message.from_user)

def process_report(bot, message):
    report_text = ""
    if message.content_type in ["photo", "document"]:
        report_text = message.caption or ""
    if message.content_type == "text" and message.text:
        if report_text:
            report_text += "\n" + message.text
        else:
            report_text = message.text

    user = message.from_user
    header = f"📣 Report from {user.username or user.first_name} ({user.id}):\n\n"

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("Claim Report", callback_data="claim_report"),
        telebot.types.InlineKeyboardButton("Close Report", callback_data="close_report")
    )

    for owner in config.OWNERS:
        try:
            if message.content_type == "photo":
                photo_id = message.photo[-1].file_id
                fwd = bot.send_photo(owner, photo_id,
                                     caption=header + report_text,
                                     parse_mode="HTML",
                                     reply_markup=markup)
            elif message.content_type == "document":
                fwd = bot.send_document(owner, message.document.file_id,
                                        caption=header + report_text,
                                        parse_mode="HTML",
                                        reply_markup=markup)
            else:
                fwd = bot.send_message(owner, header + report_text,
                                       parse_mode="HTML", reply_markup=markup)
            REPORT_MAPPING[fwd.message_id] = message.chat.id
        except Exception as e:
            print(f"Error sending report to {owner}: {e}")

    bot.send_message(message.chat.id, "✅ Your report has been submitted. Thank you!")

def handle_report_callback(bot, call):
    if call.data == "claim_report":
        msg_id = call.message.message_id
        if msg_id in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report already claimed.")
        else:
            admin_id = call.from_user.id
            CLAIMED_REPORTS[msg_id] = admin_id
            bot.answer_callback_query(call.id, "Report claimed.")
            user_chat = REPORT_MAPPING.get(msg_id)
            if user_chat:
                admin_name = call.from_user.username or call.from_user.first_name
                bot.send_message(user_chat, f"Your report is now being handled by {admin_name} ({admin_id}).")
    elif call.data == "close_report":
        msg_id = call.message.message_id
        if msg_id not in CLAIMED_REPORTS:
            bot.answer_callback_query(call.id, "Report not claimed yet.")
        else:
            admin_id = CLAIMED_REPORTS[msg_id]
            bot.answer_callback_query(call.id, "Report closed.")
            user_chat = REPORT_MAPPING.get(msg_id)
            if user_chat:
                admin_name = call.from_user.username or call.from_user.first_name
                bot.send_message(user_chat, f"Your report has been closed by {admin_name} ({admin_id}).")
            if msg_id in CLAIMED_REPORTS:
                del CLAIMED_REPORTS[msg_id]
            if msg_id in REPORT_MAPPING:
                del REPORT_MAPPING[msg_id]
