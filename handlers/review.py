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



@bot.message_handler(func=lambda message: message.reply_to and message.reply_to.text == "⚖️ Your report has been responded to by an admin.")
def forward_user_reply_to_admin(message):
    admin_id = message.reply_to.message.from_user.id
    bot.forward_message(admin_id, message.chat.id, message.message_id)
    bot.send_message(admin_id, "⚖️ The user has replied to your message.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("close_report"))
def close_report(call):
    user_id = call.data.split("_")[2]
    close_report_in_db(user_id, call.from_user.id)  # Update the report status in your DB to closed
    bot.answer_callback_query(call.id, "✅ This report is now closed.")

    # Notify the user
    bot.send_message(user_id, "🚫 Your report has been closed. Hope you found a solution!")

    # Notify the admin
    bot.send_message(call.from_user.id, "⚖️ You have closed this report. No further actions can be taken.")
    
    # Prevent further claiming
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

# Handler for reports in the main menu if needed
def send_report_menu(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📝 Submit a Report", callback_data="submit_report"))
    bot.send_message(message.chat.id, "If you want to report any issue, use the button below:", reply_markup=markup)
