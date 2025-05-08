from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 MENU:\n1. 📰 Tin tức\n2. 📅 Lịch trình\n3. ❓ Trợ giúp"
    )

if __name__ == '__main__':
    import os
    TOKEN = os.environ.get("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("menu", menu_command))

    print("Bot đang chạy...")
    app.run_polling()

