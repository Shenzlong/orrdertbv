from flask import Flask, request
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "mysecretpath")

app = Flask(__name__)

# Lệnh /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống.")

# Lệnh /menu
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 MENU:\n1. cup   - Paper cup(1 case/10 pcs)..."
    )

# Khởi tạo bot app
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("menu", menu_command))

# Webhook endpoint
@app.post(f"/{WEBHOOK_SECRET}")
async def webhook() -> str:
    update = Update.de_json(request.json, bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

@app.route('/')
def index():
    return "Bot is live with webhook!"

# Đặt webhook khi khởi động
async def set_webhook():
    url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{WEBHOOK_SECRET}"
    await bot_app.bot.set_webhook(url)

if __name__ == "__main__":
    import asyncio
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))