import telebot
from db import get_platforms, get_stock_for_platform, update_platform_stock, get_user, update_user_points
from telebot import types
import config

def send_rewards_menu(bot, message):
    """
    Send the available rewards menu to the user with buttons for each platform.
    """
    platforms = get_platforms()  # Get all platforms from the database
    if not platforms:
        bot.send_message(message.chat.id, "❌ No platforms available. Please try again later.")
        return

    markup = types.InlineKeyboardMarkup()
    for platform in platforms:
        markup.add(types.InlineKeyboardButton(f"📺 {platform[0]}", callback_data=f"reward_{platform[0]}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    
    bot.send_message(message.chat.id, "<b>🎯 Available Rewards</b>", parse_mode="HTML", reply_markup=markup)

def handle_platform_selection(bot, call, platform_name):
    """
    Handle the selection of a platform by the user.
    Displays the available stock for the platform and allows the user to buy rewards.
    """
    stock = get_stock_for_platform(platform_name)
    if not stock:
        bot.edit_message_text(f"📺 {platform_name}\n\n❌ No stock available.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    available_count = len(stock)
    text = f"📺 {platform_name}\n\nAvailable Stock: {available_count} items."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🎁 Buy {platform_name} Reward", callback_data=f"buy_{platform_name}"))

    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

def claim_account(bot, call, platform_name):
    """
    Handle the process of claiming an account from the stock, checking if the user has enough points.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    
    if user is None:
        bot.answer_callback_query(call.id, "❌ User not found.")
        return

    points = user[3]
    required_points = 3  # Cost of an account in points
    
    if points < required_points:
        bot.answer_callback_query(call.id, f"❌ Insufficient points. You need {required_points} points to buy an account.")
        return

    stock = get_stock_for_platform(platform_name)
    if not stock:
        bot.answer_callback_query(call.id, "❌ No stock available for this platform.")
        return

    account = stock.pop()  # Get the first account from the stock
    new_points = points - required_points  # Deduct points for purchasing
    update_user_points(user_id, new_points)  # Update user points in the database
    update_platform_stock(platform_name, stock)  # Update platform stock in the database
    
    bot.answer_callback_query(call.id, "🎉 You successfully claimed an account!")
    bot.send_message(call.message.chat.id, f"📺 {platform_name} Account:\n<code>{account}</code>\nRemaining Points: {new_points}", parse_mode="HTML")

def claim_cookie(bot, call, platform_name):
    """
    Handle the process of claiming a cookie from the stock, checking if the user has enough points.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    
    if user is None:
        bot.answer_callback_query(call.id, "❌ User not found.")
        return

    points = user[3]
    required_points = 2  # Cost of a cookie in points
    
    if points < required_points:
        bot.answer_callback_query(call.id, f"❌ Insufficient points. You need {required_points} points to buy a cookie.")
        return

    stock = get_stock_for_platform(platform_name)
    if not stock:
        bot.answer_callback_query(call.id, "❌ No stock available for this platform.")
        return

    cookie = stock.pop()  # Get the first cookie from the stock
    new_points = points - required_points  # Deduct points for purchasing
    update_user_points(user_id, new_points)  # Update user points in the database
    update_platform_stock(platform_name, stock)  # Update platform stock in the database
    
    bot.answer_callback_query(call.id, "🎉 You successfully claimed a cookie!")
    bot.send_message(call.message.chat.id, f"📺 {platform_name} Cookie:\n<code>{cookie}</code>\nRemaining Points: {new_points}", parse_mode="HTML")

def handle_buy_reward(bot, call, platform_name):
    """
    Handle the reward purchase by the user. It checks if it's a cookie or an account, 
    and proceeds accordingly with points validation and stock update.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    
    if user is None:
        bot.answer_callback_query(call.id, "❌ User not found.")
        return
    
    # Assuming the user has enough points (check if enough points are available)
    points = user[3]
    
    # Different rewards have different costs (3 points for accounts, 2 points for cookies)
    # You can add more logic here for different types of rewards if needed
    if points >= 3:
        claim_account(bot, call, platform_name)  # Handle claiming account
    elif points >= 2:
        claim_cookie(bot, call, platform_name)  # Handle claiming cookie
    else:
        bot.answer_callback_query(call.id, "❌ You don't have enough points to claim this reward.")

def update_platform_stock(platform_name, stock):
    """
    Update the stock for a specific platform after a user claims a reward (account/cookie).
    """
    try:
        conn = sqlite3.connect(config.DATABASE)
        c = conn.cursor()
        c.execute("UPDATE platforms SET stock=? WHERE platform_name=?", (json.dumps(stock), platform_name))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error updating platform stock: {e}")
    
