def send_support_message(bot, message):
    text = "For support, contact @MrLazyOp or join our support group at https://t.me/ShadowBotSupportChat ."
    bot.send_message(message.chat.id, text)
