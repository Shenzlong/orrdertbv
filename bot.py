from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
import os
import pandas as pd

TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
MENU_FILE = "menu_data.json"

def load_menu():
    try:
        with open(MENU_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "Highland": [], "Bapun": [],
            "E-coffee": [], "Meways": [], "Mai Teas": []
        }

def save_menu():
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(menu_data, f, ensure_ascii=False, indent=2)

menu_data = load_menu()
user_choices = {}

SELECT_MENU, ENTER_ITEMS = range(2)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào mừng! Gõ /menu để bắt đầu chọn món.")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=f"menu|{name}")] for name in menu_data.keys()]
    await update.message.reply_text("📋 Chọn menu thương hiệu:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, menu_name = query.data.split("|")
    items = menu_data.get(menu_name, [])
    if not items:
        await query.edit_message_text(f"🚫 Menu '{menu_name}' chưa có món.")
        return
    keyboard = [[InlineKeyboardButton(f"{code} - {desc}", callback_data=f"item|{code}")] for code, desc in items]
    await query.edit_message_text(f"📂 Món trong menu '{menu_name}':", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_item_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, code = query.data.split("|")
    user_name = query.from_user.first_name
    user_choices[query.from_user.id] = (user_name, code)
    await query.edit_message_text(f"✅ {user_name} đã chọn {code}.")

async def update_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(name, callback_data=f"update|{name}")] for name in menu_data.keys()]
    await update.message.reply_text("🛠 Chọn menu bạn muốn cập nhật:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_MENU

async def select_menu_to_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, menu_name = query.data.split("|")
    context.user_data["updating_menu"] = menu_name
    await query.edit_message_text("✏️ Nhập từng món theo mẫu: mã - mô tả. Nhập 'xong' để hoàn tất.")
    return ENTER_ITEMS

async def receive_menu_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    menu_name = context.user_data["updating_menu"]
    if text.lower() == "xong":
        save_menu()
        await update.message.reply_text(f"✅ Đã cập nhật menu '{menu_name}'.")
        return ConversationHandler.END
    if " - " not in text:
        await update.message.reply_text("⚠️ Sai định dạng. Nhập theo mẫu: mã - mô tả")
        return ENTER_ITEMS
    code, desc = text.split(" - ", 1)
    menu_data[menu_name].append((code.strip(), desc.strip()))
    await update.message.reply_text(f"✔️ Đã thêm: {code.strip()} - {desc.strip()}")
    return ENTER_ITEMS

async def list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📋 Danh sách toàn bộ menu:\n"
    for brand, items in menu_data.items():
        msg += f"\n🔸 *{brand}*\n"
        for code, desc in items:
            msg += f"  - {code}: {desc}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rows = []
        for brand, items in menu_data.items():
            for code, desc in items:
                rows.append({"Menu": brand, "Mã": code, "Mô tả": desc})
        df = pd.DataFrame(rows)
        file_path = "menu_export.xlsx"
        df.to_excel(file_path, index=False)
        with open(file_path, "rb") as f:
            await update.message.reply_document(f, filename=file_path)
    except:
        await update.message.reply_text("❌ Không thể xuất dữ liệu.")

async def clear_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for k in menu_data:
        menu_data[k] = []
    save_menu()
    await update.message.reply_text("⚠️ Đã xóa toàn bộ món trong menu.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy cập nhật.")
    return ConversationHandler.END

async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Nhắc nhở: Vui lòng chọn trà/cafe tháng này. Dùng lệnh /menu."
    )

# ==== Upload JSON ====
async def handle_json_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Vui lòng gửi file .json")
        return
    file = await document.get_file()
    path = "uploaded_menu.json"
    await file.download_to_drive(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in data:
            if isinstance(data[k], list):
                menu_data[k] = data[k]
        save_menu()
        await update.message.reply_text("✅ Đã cập nhật menu từ file JSON.")
    except Exception as e:
        await update.message.reply_text("❌ Lỗi khi đọc file JSON.")

# ==== Khởi động ====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_menu_selection, pattern="^menu\\|"))
    app.add_handler(CallbackQueryHandler(handle_item_selection, pattern="^item\\|"))

    app.add_handler(CommandHandler("list", list_menu))
    app.add_handler(CommandHandler("export", export_menu))
    app.add_handler(CommandHandler("clear", clear_menu))

    update_conv = ConversationHandler(
        entry_points=[CommandHandler("update", update_menu_command)],
        states={
            SELECT_MENU: [CallbackQueryHandler(select_menu_to_update, pattern="^update\\|")],
            ENTER_ITEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_menu_item)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(update_conv)

    # Nhận file json để cập nhật
    app.add_handler(MessageHandler(filters.Document.MIME_TYPE("application/json"), handle_json_upload))

    # Nhắc định kỳ
    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, "cron", day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()