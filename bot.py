from flask import Flask
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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

# Gửi nhắc nhở định kỳ
async def send_monthly_reminder(app):
    chat_id = os.environ.get("TARGET_CHAT_ID")
    await app.bot.send_message(
        chat_id=chat_id,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

# Route Flask cơ bản
@app_flask.route('/')
def index():
    return "Bot is running!"

# Chạy Flask bằng asyncio
async def run_flask():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', '10000')}"]
    await serve(app_flask, config)

# Chạy bot Telegram
async def run_bot():
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))

    scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    await app.run_polling()

# Chạy cả Flask và Bot song song
async def main():
    await asyncio.gather(
        run_flask(),
        run_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())