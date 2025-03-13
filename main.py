import telebot
from db import init_db, get_user
from handlers.main_menu import send_main_menu
from handlers.referral import send_referral_menu
from handlers.rewards import send_rewards_menu
from handlers.account_info import send_account_info
from handlers.review import prompt_review
from handlers.verification import send_verification_message, handle_verification_callback
from handlers.admin import send_admin_menu  # Importing the correct function for admin menu
from telebot import types
import config

# Initialize the bot with the token from config.py
bot = telebot.TeleBot(config.TOKEN, parse_mode="HTML")

# Initialize the database
init_db()

# /start command: Record user info and start the verification process
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)

    if user is None:
        # Add the new user to the database
        add_user(user_id, message.from_user.username, message.date)
        send_verification_message(bot, message)
    else:
        # If the user is already in the database, just check verification status
        if user[6] == 0:  # If not verified
            send_verification_message(bot, message)
        else:
            send_main_menu(bot, message)

# Callback handler for verification (user clicks "Verify")
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def verify_user(call):
    handle_verification_callback(bot, call)

# Callback handler for main menu options
@bot.callback_query_handler(func=lambda call: call.data == 'menu_rewards')
def rewards_menu(call):
    send_rewards_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'menu_account')
def account_info(call):
    send_account_info(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'menu_referral')
def referral_menu(call):
    send_referral_menu(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'menu_review')
def review(call):
    prompt_review(bot, call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'back_main')
def back_to_main(call):
    send_main_menu(bot, call.message)

# Admin actions (for admins and owners only)
@bot.callback_query_handler(func=lambda call: call.data == 'menu_admin')
def admin_panel(call):
    send_admin_menu(bot, call.message)  # Ensure you're calling the correct function for the admin panel

# Admin Panel callbacks: Platform Management, User Management, Key Management
@bot.callback_query_handler(func=lambda call: call.data == 'admin_platform')
def admin_platform(call):
    handle_admin_platform(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_users')
def admin_users(call):
    handle_admin_users(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_keys')
def admin_keys(call):
    handle_admin_keys(bot, call)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_settings')
def admin_settings(call):
    handle_admin_settings(bot, call)

# Callback for adding platform
@bot.callback_query_handler(func=lambda call: call.data == 'add_platform')
def add_platform(call):
    handle_admin_add_platform(bot, call)

# Callback for adding stock to a platform
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_stock_'))
def add_stock(call):
    platform_name = call.data.split('_', 1)[1]
    handle_add_stock(bot, call, platform_name)

# For handling users who click on "Add Stock"
@bot.callback_query_handler(func=lambda call: call.data.startswith('reward_'))
def handle_platform_selection(call):
    platform_name = call.data.split('_', 1)[1]
    handle_platform_selection(bot, call, platform_name)

# Callback for generating referral link
@bot.callback_query_handler(func=lambda call: call.data == 'generate_referral')
def generate_referral(call):
    send_referral_menu(bot, call.message)

# Handle when users click on the "Verify" button
@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def handle_user_verification(call):
    handle_verification_callback(bot, call)

# Handler for user verification
def handle_verification_callback(bot, call):
    user_id = str(call.from_user.id)
    user = get_user(user_id)

    # Check if the user is verified, if not proceed with verification
    if user and user[6] == 1:
        send_main_menu(bot, call.message)
    else:
        send_verification_message(bot, call.message)

# Run the bot's polling function
bot.polling(none_stop=True)
