import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
import pandas as pd
import io

# Biến môi trường
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
MENU_JSON_FILE = 'menu.json'

# Khởi tạo MENU_STRUCTURE
MENU_STRUCTURE = {}

# Đọc menu từ file JSON
def load_menu_structure():
    global MENU_STRUCTURE
    try:
        with open(MENU_JSON_FILE, 'r', encoding='utf-8') as f:
            MENU_STRUCTURE = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Đọc menu từ file thất bại: {e}")
        MENU_STRUCTURE = {}

# Cập nhật menu từ file JSON mới
def reload_menu():
    load_menu_structure()

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ /menu để xem danh sách đồ uống."
    )

# /menu – Hiển thị menu cấp 1
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MENU_STRUCTURE:
        await update.message.reply_text("❌ Menu chưa được cập nhật.")
        return

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

# /update – Cập nhật menu từ file JSON
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        # Lấy thông tin tệp tin
        file = update.message.document
        file_name = file.file_name
        print(f"Đã nhận tệp tin: {file_name}")  # Debug để xem file nhận được

        # Tải file về
        file_path = await file.get_file()
        print(f"Tải file từ đường dẫn: {file_path.file_path}")  # Debug đường dẫn tải về
        file_path.download_to_drive(MENU_JSON_FILE)

        # Reload lại menu sau khi tải file mới
        try:
            reload_menu()  # Gọi lại reload menu ngay sau khi cập nhật file
            await update.message.reply_text(f"✅ Menu đã được cập nhật thành công từ file `{file_name}`!")
        except json.JSONDecodeError as e:
            await update.message.reply_text(f"❌ Lỗi JSON: {e}")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi cập nhật menu: {e}")
    else:
        await update.message.reply_text("❌ Vui lòng gửi một tệp tin JSON hợp lệ.")

# /list – Hiển thị danh sách người dùng đã chọn
async def list_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MENU_STRUCTURE:
        await update.message.reply_text("❌ Menu chưa được cập nhật.")
        return
    
    response = "📋 Danh sách đặt món:\n"
    # Giả sử user_choices là dictionary lưu lựa chọn của người dùng
    for user_id, (name, code) in user_choices.items():
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

# Chạy bot
if __name__ == '__main__':
    load_menu_structure()  # Đọc file menu ngay khi bắt đầu bot

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))
    app.add_handler(CommandHandler("list", list_choices_command))
    app.add_handler(CommandHandler("reset", reset_choices_command))
    app.add_handler(CommandHandler("export", export_choices_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file_upload))  # Xử lý file upload cho lệnh /update

    print("Bot đang chạy...")
    app.run_polling()
