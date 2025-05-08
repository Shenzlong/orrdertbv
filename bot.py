from flask import Flask
import threading
import asyncio
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# Tạo Flask app giả để giữ cho Render không dừng web service
app_flask = Flask(__name__)

# Lệnh /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống."
    )

# Lệnh /menu
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 MENU:\n"
        "1. cup   - Paper cup (1 case/10 pcs)\n"
        "2. vina  - Vinacafe (24 gói/ bịch)\n"
        "3. net   - Netcafe (18 gói/ hộp)\n"
        "4. leg   - Legend (12 gói/ hộp)\n"
        "5. g7    - G7 (21 gói/ hộp)\n"
        "6. bg7   - Black G7 (15 gói/ hộp)\n"
        "7. bviet - Black Cafe Việt (35 gói/ bịch)\n"
        "8. gin   - Ginger Tea\n"
        "9. lip   - Lipton ice tea\n"
        "10. blip  - Black lipton tea\n"
        "11. atis  - Atiso tea\n"
        "12. mat   - Matcha tea\n"
        "13. royal - Royal milk tea Vàng\n"
        "14. milo  - Milo (10 gói/ dây)\n"
        "15. phin  - Cà phê phin (500gr/ hộp)"
    )

# Tin nhắn định kỳ mỗi tháng
async def send_monthly_reminder(app):
    chat_id = os.environ.get("TARGET_CHAT_ID")
    await app.bot.send_message(
        chat_id=chat_id,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

# Chạy bot trong luồng riêng
def run_bot():
    TOKEN = os.environ.get("BOT_TOKEN")
    bot_app = ApplicationBuilder().token(TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("menu", menu_command))

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[bot_app])
    scheduler.start()

    # Fix lỗi asyncio trong thread phụ
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_app.run_polling())

# Flask route mặc định
@app_flask.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))