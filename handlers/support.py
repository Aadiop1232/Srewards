def send_support_message(bot, message):
    text = "For support, contact @YourSupportUsername or join our support group at https://t.me/YourSupportGroup."
    bot.send_message(message.chat.id, text)
