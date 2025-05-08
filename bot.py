from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os

TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống."
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 MENU:\n1. cup   - Paper cup(1 case/10 pcs)\n2. vina  - Vinacafe(24 gói/ bịch)\n3. net   - Netcafe(18 gói/ hộp)\n4. leg   - Legend(12 gói/ hộp)\n5. g7    - G7(21 gói/ hộp)\n6. bg7   - Black G7(15 gói/ hộp)\n7. bviet - Black Cafe Việt(35 gói/ bịch)\n8. gin   - Ginger Tea\n9. lip   - Lipton ice tea\n10. blip  - Black lipton tea\n10. atis  - Atiso tea\n12. mat   - Matcha tea\n13. royal - Royal milk tea Vàng\n14. milo  - Milo(10 gói/ dây)\n15. phin  - Cà phê phin(500gr/ hộp)"
    )

async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()
