import telebot
from telebot import types
import config
from handlers.admin import is_admin
from handlers.main_menu import send_main_menu

def check_channel_membership(bot, user_id):
    """Verify bot is admin and user is member in all channels"""
    for channel in config.REQUIRED_CHANNELS:
        try:
            channel_username = channel.split("/")[-1]
            chat = bot.get_chat(f"@{channel_username}")
            
            # Check bot admin status
            bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
            if bot_member.status not in ["administrator", "creator"]:
                print(f"Bot not admin in {channel}")
                return False
            
            # Check user membership
            user_member = bot.get_chat_member(chat.id, user_id)
            if user_member.status not in ["member", "administrator", "creator"]:
                return False
                
        except Exception as e:
            print(f"Verification error: {e}")
            return False
    return True

def send_verification_message(bot, message):
    """Handle verification flow with proper message editing"""
    user_id = message.from_user.id
    
    if is_admin(user_id):
        try:
            # Edit existing message if possible
            bot.edit_message_text(
                "✨ Admin/Owner Access Granted!",
                message.chat.id,
                message.message_id
            )
        except:
            # Send new message if edit fails
            bot.send_message(message.chat.id, "✨ Welcome back, Admin!")
        
        send_main_menu(bot, message)
        return

    if check_channel_membership(bot, user_id):
        try:
            bot.edit_message_text(
                "✅ Verification Successful!",
                message.chat.id,
                message.message_id
            )
        except:
            bot.send_message(message.chat.id, "✅ Verified!")
        send_main_menu(bot, message)
    else:
        markup = types.InlineKeyboardMarkup()
        for channel in config.REQUIRED_CHANNELS:
            channel_username = channel.split("/")[-1]
            markup.add(types.InlineKeyboardButton(
                f"Join {channel_username}",
                url=channel
            ))
        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
        
        try:
            bot.edit_message_text(
                "🔒 Please join these channels to continue:",
                message.chat.id,
                message.message_id,
                reply_markup=markup
            )
        except:
            bot.send_message(
                message.chat.id,
                "🔒 Please join these channels to continue:",
                reply_markup=markup
            )

def handle_verification_callback(bot, call):
    """Handle verification button press"""
    if check_channel_membership(bot, call.from_user.id):
        try:
            bot.edit_message_text(
                "✅ Verification Successful!",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            bot.answer_callback_query(call.id, "✅ Verified!")
        send_main_menu(bot, call.message)
        process_verified_referral(call.from_user.id)
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Join all channels first!",
            show_alert=True
        )
