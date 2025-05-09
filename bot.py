import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import io

# Biến môi trường
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
MENU_JSON_FILE = "menu.json"  # Đường dẫn tới file menu.json

# Cấu trúc menu cấp 1 và danh sách món tương ứng (ban đầu sẽ load từ file JSON)
MENU_STRUCTURE = {}

# Lưu lựa chọn người dùng: {user_id: (tên, mã món)}
user_choices = {}

# Đọc và tải cấu trúc menu từ file JSON
def load_menu_structure():
    global MENU_STRUCTURE
    try:
        with open(MENU_JSON_FILE, "r", encoding="utf-8") as f:
            MENU_STRUCTURE = json.load(f)
        print("Menu đã được tải thành công.")
    except json.JSONDecodeError as e:
        print(f"Lỗi JSON khi tải menu: {e}")
    except Exception as e:
        print(f"Lỗi khi tải menu: {e}")

# Reload lại cấu trúc menu
def reload_menu():
    load_menu_structure()
    print("Menu đã được cập nhật:", MENU_STRUCTURE)  # In ra cấu trúc menu để kiểm tra

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

# /update – Cập nhật menu từ file JSON
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        # Tải file về
        file = update.message.document
        file_path = await file.get_file()
        file_path.download_to_drive(MENU_JSON_FILE)

        # Reload lại menu sau khi tải file mới
        try:
            reload_menu()  # Gọi lại reload menu ngay sau khi cập nhật file
            await update.message.reply_text("✅ Menu đã được cập nhật thành công từ file `menu.json`!")
        except json.JSONDecodeError as e:
            await update.message.reply_text(f"❌ Lỗi JSON: {e}")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi cập nhật menu: {e}")

# Gửi nhắc nhở định kỳ
async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

# Chạy bot
if __name__ == '__main__':
    load_menu_structure()  # Lấy cấu trúc menu khi bot khởi động

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))
    app.add_handler(CommandHandler("list", list_choices_command))
    app.add_handler(CommandHandler("reset", reset_choices_command))
    app.add_handler(CommandHandler("export", export_choices_command))
    app.add_handler(CommandHandler("update", handle_file_upload))  # Thêm lệnh /update để upload file

    # Scheduler
    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()
