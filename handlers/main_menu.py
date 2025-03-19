# main_menu.py

import telebot
from telebot import types
from db import get_user
from handlers.admin import is_admin

GIF_URL = "https://i.imgur.com/AcmLDc1.gif"  # The GIF you want to show

def send_main_menu(bot, update):
    """
    Sends a single message with an animation (the GIF) + caption + inline keyboard
    in one go. That way, when we call bot.delete_message on it, the entire
    animation + menu gets deleted together.
    """
    print("[DEBUG send_main_menu] Called send_main_menu.")

    # Figure out which chat_id to send to
    if hasattr(update, "from_user"):
        user = get_user(str(update.from_user.id))
        chat_id = update.chat.id if hasattr(update, "chat") else update.message.chat.id
    else:
        user = get_user(str(update.message.from_user.id))
        chat_id = update.message.chat.id

    # Build the inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🎉 Rewards", callback_data="menu_rewards"),
        types.InlineKeyboardButton("👥 Info", callback_data="menu_info"),
        types.InlineKeyboardButton("🤝 Referral", callback_data="menu_referral")
    )
    markup.add(
        types.InlineKeyboardButton("📠 Review", callback_data="menu_review"),
        types.InlineKeyboardButton("📣 Report", callback_data="menu_report"),
        types.InlineKeyboardButton("💬 Support", callback_data="menu_support")
    )

    # If user is admin, show Admin Panel button
    if is_admin(user):
        markup.add(types.InlineKeyboardButton("🔨 Admin Panel", callback_data="menu_admin"))

    # Send the GIF, caption, and inline keyboard in one message
    try:
        bot.send_animation(
            chat_id,
            GIF_URL,
            caption="Main Menu\nPlease choose an option:",
            parse_mode="HTML",
            reply_markup=markup
        )
        print("[DEBUG send_main_menu] Successfully sent animation + menu in one message.")
    except Exception as e:
        print(f"[ERROR] send_main_menu failed to send animation: {e}")
        # Fallback: if animation with inline keyboard fails on some clients,
        # you can do two separate messages (GIF, then text + keyboard).
        # But then you'd have to store both message IDs to delete both, etc.
        # For now, we try to keep it simple with one message.
