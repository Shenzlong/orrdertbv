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
import json

# Biến môi trường
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")

# Tải menu từ file
MENU_STRUCTURE = {}
OPTIONS = {}
def load_menu_structure():
    with open("menu.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_options():
    with open("options.json", "r", encoding="utf-8") as f:
        return json.load(f)

def reload_data():
    global MENU_STRUCTURE, OPTIONS
    MENU_STRUCTURE = load_menu_structure()
    OPTIONS = load_options()

# Gọi khi khởi động
reload_data()

# Lưu lựa chọn người dùng: {user_id: {"name": ..., "drink_code": ..., "sweetness": ..., "tea": ..., "topping": ...}}
user_choices = {}
user_states = {}

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
    await update.message.reply_text("🏢 Chọn MENU:", reply_markup=reply_markup)

# Xử lý callback
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
                [InlineKeyboardButton(text=f"{code} - {desc}", callback_data=f"item_{code}")]
                for code, desc in items
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"📋 Danh sách món {MENU_STRUCTURE[menu_code]['name']}:", reply_markup=reply_markup
            )
        return

    # Xử lý chọn món
    if data.startswith("item_"):
        item_code = data.replace("item_", "")
        # Tìm menu chứa item_code
        selected_item = None
        for menu in MENU_STRUCTURE.values():
            for code, name in menu["items"]:
                if code == item_code:
                    selected_item = {
                        "code": code,
                        "name": name,
                        "options": menu.get("options", {})
                    }
                    break

        if selected_item:
            user_choices[user_id] = {"name": user_name, "drink_code": f"{selected_item['code']} - {selected_item['name']}"}
            user_states[user_id] = {"step": "sweetness", "options": selected_item["options"]}

            if "sweetness" in selected_item["options"]:
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"sweetness_{opt}")] for opt in OPTIONS["sweetness_levels"]]
                await query.edit_message_text("🧁 Chọn độ ngọt:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif "tea" in selected_item["options"]:
                user_states[user_id]["step"] = "tea"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"tea_{opt}")] for opt in OPTIONS["tea_strengths"]]
                await query.edit_message_text("🍵 Chọn độ trà:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif "topping" in selected_item["options"]:
                user_states[user_id]["step"] = "topping"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"topping_{opt}")] for opt in OPTIONS["toppings"]]
                await query.edit_message_text("🍡 Chọn topping:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text(f"✅ {user_name} đã chọn: {selected_item['code']} - {selected_item['name']}")
        return

    # Xử lý các bước chọn option
    if "_" in data:
        category, value = data.split("_", 1)
        if user_id in user_choices and user_id in user_states:
            user_choices[user_id][category] = value
            next_step = None
            current_options = user_states[user_id]["options"]
            if category == "sweetness" and "tea" in current_options:
                next_step = "tea"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"tea_{opt}")] for opt in OPTIONS["tea_strengths"]]
                await query.edit_message_text("🍵 Chọn độ trà:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif category == "tea" and "topping" in current_options:
                next_step = "topping"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"topping_{opt}")] for opt in OPTIONS["toppings"]]
                await query.edit_message_text("🍡 Chọn topping:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text(f"✅ {user_choices[user_id]['name']} đã hoàn tất đặt món.")
                user_states.pop(user_id, None)

            if next_step:
                user_states[user_id]["step"] = next_step

# /list – Hiển thị danh sách
async def list_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Hiện chưa có ai chọn món.")
        return

    response = "📋 Danh sách đặt món:\n"
    for data in user_choices.values():
        detail = data["drink_code"]
        if "sweetness" in data:
            detail += f" | Ngọt: {data['sweetness']}"
        if "tea" in data:
            detail += f" | Trà: {data['tea']}"
        if "topping" in data:
            detail += f" | Topping: {data['topping']}"
        response += f"- {data['name']}: {detail}\n"

    await update.message.reply_text(response)

# /reset – Xoá tất cả
async def reset_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choices.clear()
    user_states.clear()
    await update.message.reply_text("♻️ Danh sách đặt món đã được reset.")

# /export – Xuất Excel
async def export_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_choices:
        await update.message.reply_text("📭 Không có dữ liệu để xuất.")
        return

    data = []
    for d in user_choices.values():
        entry = {
            "Tên": d["name"],
            "Món": d["drink_code"],
            "Độ ngọt": d.get("sweetness", ""),
            "Độ trà": d.get("tea", ""),
            "Topping": d.get("topping", "")
        }
        data.append(entry)

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

# /update – Reload menu và options
async def update_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reload_data()
        await update.message.reply_text("✅ Đã tải lại menu và options từ file.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi tải: {str(e)}")

# Gửi nhắc nhở định kỳ
async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

# Khởi động bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))
    app.add_handler(CommandHandler("list", list_choices_command))
    app.add_handler(CommandHandler("reset", reset_choices_command))
    app.add_handler(CommandHandler("export", export_choices_command))
    app.add_handler(CommandHandler("update", update_menu_command))

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(send_monthly_reminder, 'cron', day=6, hour=8, minute=0, args=[app])
    scheduler.start()

    print("Bot đang chạy...")
    app.run_polling()
