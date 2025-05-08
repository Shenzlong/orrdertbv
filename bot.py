import telebot
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Token được lấy từ biến môi trường
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Chào bạn! Gõ /menu để xem thực đơn.")

@bot.message_handler(commands=['menu'])
def send_menu(message):
    menu = "📋 *Menu hôm nay:*\n\n🍜 Món A: Phở bò\n🍛 Món B: Cơm tấm\n🍲 Món C: Bún riêu"
    bot.send_message(message.chat.id, menu, parse_mode="Markdown")

bot.infinity_polling()  # Sử dụng infinity_polling cho ổn định khi deploy
