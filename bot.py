from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import io
import os

# Biến môi trường
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")

# Danh sách món
MENU_ITEMS = [
    ("cup", "Paper cup (1 case/10 pcs)"),
    ("vina", "Vinacafe (24 gói/ bịch)"),
    ("net", "Netcafe (18 gói/ hộp)"),
    ("leg", "Legend (12 gói/ hộp)"),
    ("g7", "G7 (21 gói/ hộp)"),
    ("bg7", "Black G7 (15 gói/ hộp)"),
    ("bviet", "Black Cafe Việt (35 gói/ bịch)"),
    ("gin", "Ginger Tea"),
    ("lip", "Lipton ice tea"),
    ("blip", "Black lipton tea"),
    ("atis", "Atiso tea"),
    ("mat", "Matcha tea"),
    ("royal", "Royal milk tea Vàng"),
    ("milo", "Milo (10 gói/ dây)"),
    ("phin", "Cà phê phin (500gr/ hộp)"),
]

user_choices = {}  # {user_id: (name, code)}

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống.")

# /menu
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"{code} - {desc}", callback_data=code)] for code, desc in MENU_ITEMS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Chọn món bạn muốn đặt:", reply_markup=reply_markup)

# Người dùng chọn món
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user_choices[user_id] = (user_name, code)
    await query.edit_message_text(f"✅ {user_name} đã chọn {code}.")

# /list
async def list_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Hiện chưa có ai chọn món.")
        return
    response = "📋 Danh sách đặt món:\n" + "\n".join(f"- {name}: {code}" for _, (name, code) in user_choices.items())
    await update.message.reply_text(response)

# /reset
async def reset_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choices.clear()
    await update.message.reply_text("♻️ Danh sách đặt món đã được reset.")

# /export
async def export_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Không có dữ liệu để xuất.")
        return
    data = [{"Tên": name, "Mã món": code} for _, (name, code) in user_choices.items()]
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Danh sách")
    buffer.seek(0)
    await update.message.reply_document(document=buffer, filename="danh_sach_chon_mon.xlsx", caption="📄 Danh sách chọn món (Excel)")

# Nhắc định kỳ
async def send_monthly_reminder(app):
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text="📣 Vui lòng chọn trà/cafe tháng này. Gõ /menu để xem món.")

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("list", list_choices_command))
    app.add_handler(CommandHandler("reset", reset_choices_command))
    app.add_handler(CommandHandler("export", export_choices_command))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, "cron", day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()
