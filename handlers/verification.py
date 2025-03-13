import telebot
from db import get_user, update_user_points
from telebot import types
import config

def send_verification_message(bot, message):
    """
    Send a verification message to the user and check if they have joined the required channels.
    """
    user_id = str(message.from_user.id)
    user = get_user(user_id)

    # Check if the user is already verified or is an admin/owner
    if user and user[6]:  # Checking if the user has already passed verification
        bot.send_message(message.chat.id, f"✅ Welcome back {message.from_user.username}, you're already verified!")
        send_main_menu(bot, message)
        return
    
    if is_admin_or_owner(message.from_user):  # Bypass for Admins and Owners
        bot.send_message(message.chat.id, f"⚡️ Hello {message.from_user.username}, as an admin/owner, verification is bypassed.")
        send_main_menu(bot, message)
        return

    # Send instructions for verification
    text = f"Hey {message.from_user.username}, Welcome to {config.BOT_USERNAME}!\n\n"
    text += "Please verify yourself by joining the channels below:\n"

    markup = types.InlineKeyboardMarkup()
    for channel in config.REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=channel))
    
    markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))

    bot.send_message(message.chat.id, text, reply_markup=markup)

def handle_verification_callback(bot, call):
    user_id = str(call.from_user.id)
    user = get_user(user_id)

    if user and user[6]:  # If already verified
        bot.answer_callback_query(call.id, "You're already verified!")
        return

    try:
        for channel in config.REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ["member", "administrator"]:
                bot.answer_callback_query(call.id, f"You need to join the channel: {channel}")
                return
        
        # Update the user as verified in the database
        update_user_verified(user_id)
        bot.answer_callback_query(call.id, "You're now verified! 🎉")
        send_main_menu(bot, call.message)
    
    except Exception as e:
        print(f"Error verifying user {user_id}: {e}")
        bot.answer_callback_query(call.id, "Verification failed. Please try again.")

def update_user_verified(user_id):
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET verified=1 WHERE telegram_id=?", (user_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error updating verification status for {user_id}: {e}")

def send_main_menu(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_rewards = types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards")
    btn_account = types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account")
    btn_referral = types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral")
    btn_review = types.InlineKeyboardButton("💬 Review", callback_data="menu_review")
    
    markup.add(btn_rewards, btn_account, btn_referral, btn_review)
    
    # Admin button visible only to admins/owners
    if is_admin_or_owner(message.from_user):
        btn_admin = types.InlineKeyboardButton("🛠 Admin Panel", callback_data="menu_admin")
        markup.add(btn_admin)

    bot.send_message(message.chat.id, "<b>📋 Main Menu</b>\nPlease choose an option:", parse_mode="HTML", reply_markup=markup)

def is_admin_or_owner(user_obj):
    """
    Check if the user is an admin or owner.
    Admins and owners can see the Admin Panel in the main menu.
    """
    user_id = str(user_obj.id)
    return user_id in config.ADMINS or user_id in config.OWNERS
        
