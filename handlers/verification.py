import time
import config
from telebot import types
from handlers.main_menu import send_main_menu


def check_channel_membership(bot, user_id):
    for channel in config.REQUIRED_CHANNELS:
        try:
            chan_name = channel.rstrip('/').split("/")[-1]
            chat = bot.get_chat("@" + chan_name)

            # if the bot isn't at least a member
            bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
            if bot_member.status not in ["member", "administrator", "creator"]:
                return False

            user_member = bot.get_chat_member(chat.id, user_id)
            if user_member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Error checking membership in {channel}: {e}")
            return False
    return True

def make_progress_bar(percentage, length=10):
    filled = int(percentage * length // 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def send_verification_message(bot, message):
    verifying_msg = bot.send_message(message.chat.id, "⏳ Checking membership...")

    for step in [25, 50, 75, 100]:
        time.sleep(1)
        bar = make_progress_bar(step, length=10)
        try:
            bot.edit_message_text(
                f"⏳ Verifying channels...\n{bar}  {step}%",
                chat_id=verifying_msg.chat.id,
                message_id=verifying_msg.message_id
            )
        except Exception as e:
            print(f"Error editing verification bar: {e}")

    if check_channel_membership(bot, message.from_user.id):
        try:
            bot.edit_message_text("✅ You are verified! 🎉",
                                  chat_id=verifying_msg.chat.id,
                                  message_id=verifying_msg.message_id)
        except:
            bot.send_message(message.chat.id, "✅ You are verified! 🎉")
        send_main_menu(bot, message)
    else:
        fail_text = "🚫 You are not verified!\nPlease join the required channels first."
        try:
            bot.edit_message_text(fail_text,
                                  chat_id=verifying_msg.chat.id,
                                  message_id=verifying_msg.message_id)
        except:
            bot.send_message(message.chat.id, fail_text)

def handle_verification_callback(bot, call):
    if check_channel_membership(bot, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!")
        send_main_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "🚫 Not verified. Join channels first.")
