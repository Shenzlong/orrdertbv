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

# Cấu trúc menu cấp 1 và danh sách món tương ứng
MENU_STRUCTURE = {
    "scm": {
        "name": "SCM Office",
        "items": [
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
    },
    "hr": {
        "name": "HR Office",
        "items": [
            ("coca", "Coca Cola"),
            ("pepsi", "Pepsi Light"),
            ("sprite", "Sprite"),
        ]
    }
}

# Lưu lựa chọn người dùng: {user_id: (tên, mã món)}
user_choices = {}

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống."
    )

# /menu – Hiển thị menu cấp 1
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(text=data["name"], callback_data=f"menu_{code}")]
        for code, data in MENU_STRUCTURE.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏢 Chọn khu vực đặt món:", reply_markup=reply_markup)

# Xử lý lựa chọn menu cấp 1 hoặc món
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if data.startswith("menu_"):
        menu_code = data.replace("menu_", "")
        if menu_code in MENU_STRUCTURE:
            items = MENU_STRUCTURE[menu_code]["items"]
            keyboard = [
                [InlineKeyboardButton(text=f"{code} - {desc}", callback_data=code)]
                for code, desc in items
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"📋 Danh sách món {MENU_STRUCTURE[menu_code]['name']}:", reply_markup=reply_markup
            )
        return

    # Lưu lựa chọn món
    user_choices[user_id] = (user_name, data)
    await query.edit_message_text(text=f"✅ {user_name} đã chọn {data}.")

# /list – Hiển thị danh sách người dùng đã chọn
async def list_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Hiện chưa có ai chọn món.")
        return

    response = "📋 Danh sách đặt món:\n"
    for _, (name, code) in user_choices.items():
        response += f"- {name}: {code}\n"

    await update.message.reply_text(response)

# /reset – Xoá danh sách lựa chọn
async def reset_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choices.clear()
    await update.message.reply_text("♻️ Danh sách đặt món đã được reset.")

# /export – Xuất Excel danh sách món
async def export_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Không có dữ liệu để xuất.")
        return

    data = [{"Tên": name, "Mã món": code} for _, (name, code) in user_choices.items()]
    df = pd.DataFrame(data)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Danh sách')

    excel_buffer.seek(0)

    await update.message.reply_document(
        document=excel_buffer,
        filename="danh_sach_chon_mon.xlsx",
        caption="📄 Danh sách chọn món (Excel)"
    )

# Gửi nhắc nhở định kỳ
async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

# Chạy bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))
    app.add_handler(CommandHandler("list", list_choices_command))
    app.add_handler(CommandHandler("reset", reset_choices_command))
    app.add_handler(CommandHandler("export", export_choices_command))

    # Scheduler
    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()
