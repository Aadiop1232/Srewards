import telebot
from telebot import types
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
    username = message.from_user.username if message.from_user.username else "Unknown"
    
    # Add the review to the database (optional, if needed)
    add_review(user_id, review_text)

    # Notify admins about the new review
    bot = telebot.TeleBot(config.TOKEN)
    for owner in config.OWNERS:
        try:
            bot.send_message(owner,
                             f"📢 *Review from {username} (User ID: {user_id}):*\n\n{review_text}",
                             parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Error sending review to owner {owner}: {e}")
    
    # Acknowledge the user
    bot.send_message(message.chat.id, "✅ *Thank you for your feedback!*")

def add_review(user_id, review_text):
    """
    Adds the review or suggestion from the user to the database.
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO reviews (user_id, review) VALUES (?, ?)", (user_id, review_text))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error adding review: {e}")
        
