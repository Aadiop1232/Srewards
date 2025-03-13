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
        bot.send_message(message.chat.id, "✅ You are already verified!")
        send_main_menu(bot, message)
        return
    
    if is_admin_or_owner(message.from_user):  # Check if the user is an admin/owner
        bot.send_message(message.chat.id, "⚡️ You are an admin/owner, so verification is bypassed.")
        send_main_menu(bot, message)
        return

    # Send instructions for verification
    text = (
        "🛑 Before you can start using the bot, please verify that you have joined the required channels.\n\n"
        "👉 Please click the button below to verify. You must join the following channels to continue using the bot."
    )
    markup = types.InlineKeyboardMarkup()

    # Show the required channels for the user to join
    for channel in config.REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=channel))

    # Verify button to proceed with the verification
    markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))

    bot.send_message(message.chat.id, text, reply_markup=markup)

def handle_verification_callback(bot, call):
    """
    Handle the verification process by checking if the user has joined the required channels.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    
    if user and user[6]:  # Check if the user is already verified
        bot.answer_callback_query(call.id, "You are already verified!")
        return
    
    # Verify the channels the user has joined
    try:
        for channel in config.REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ["member", "administrator"]:
                bot.answer_callback_query(call.id, f"You need to join the channel: {channel}")
                return
        
        # Mark the user as verified
        update_user_verified(user_id)
        bot.answer_callback_query(call.id, "You are now verified! 🎉")

        # Send the main menu after successful verification
        send_main_menu(bot, call.message)

    except Exception as e:
        print(f"❌ Error verifying user {user_id}: {e}")
        bot.answer_callback_query(call.id, "An error occurred while verifying. Please try again later.")

def update_user_verified(user_id):
    """
    Mark the user as verified by setting their 'verified' status.
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE users SET pending_referrer=NULL WHERE telegram_id=?", (user_id,))
        c.execute("UPDATE users SET verified=1 WHERE telegram_id=?", (user_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error updating verification status: {e}")

def send_main_menu(bot, message):
    """
    Send the main menu to the user after successful verification or bypass.
    """
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_rewards = types.InlineKeyboardButton("💳 Rewards", callback_data="menu_rewards")
    btn_account = types.InlineKeyboardButton("👤 Account Info", callback_data="menu_account")
    btn_referral = types.InlineKeyboardButton("🔗 Referral System", callback_data="menu_referral")
    btn_review = types.InlineKeyboardButton("💬 Review", callback_data="menu_review")

    markup.add(btn_rewards, btn_account, btn_referral, btn_review)
    
    bot.send_message(message.chat.id, "<b>📋 Main Menu 📋</b>\nPlease choose an option:", parse_mode="HTML", reply_markup=markup)

def is_admin_or_owner(user_obj):
    """
    Check if the user is an admin or owner.
    Admins and owners can bypass verification.
    """
    user_id = str(user_obj.id)
    return user_id in config.ADMINS or user_id in config.OWNERS
    
