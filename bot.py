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

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Biến môi trường
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")
CREDENTIAL_JSON_CONTENT = os.environ.get("GOOGLE_CREDENTIAL_JSON")
GOOGLE_SHEET_NAME = "OfficeCafe"

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

user_choices = {}
user_states = {}

def update_google_sheet(user_name, drink_code):
    try:
        temp_credential_file = "/tmp/creds.json"
        with open(temp_credential_file, "w", encoding="utf-8") as f:
            f.write(CREDENTIAL_JSON_CONTENT)

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(temp_credential_file, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("Order")

        records = sheet.get_all_records()
        found = False
        for idx, row in enumerate(records, start=2):
            if row["Tên"] == user_name:
                sheet.update_cell(idx, 2, drink_code)
                found = True
                break

        if not found:
            sheet.append_row([user_name, drink_code])
    except Exception as e:
        print(f"❌ Lỗi khi ghi Google Sheet: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ: \n /menu để xem danh sách đồ uống.\n /list để xem danh sách các thành viên đã đặt món.\n /reset để xoá danh sách đã chọn món.\n /export để xuất danh sách đã chọn món ra excel.")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(text=data["name"], callback_data=f"menu_{code}")]
        for code, data in MENU_STRUCTURE.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏢 Chọn MENU:", reply_markup=reply_markup)

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
                [InlineKeyboardButton(text=f"{item['code']} - {item['name']}", callback_data=f"item_{item['code']}")]
                for item in items
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"📋 Danh sách món {MENU_STRUCTURE[menu_code]['name']}:", reply_markup=reply_markup
            )
        return

    if data.startswith("item_"):
        item_code = data.replace("item_", "")
        selected_item = None
        for menu in MENU_STRUCTURE.values():
            for item in menu["items"]:
                if item["code"] == item_code:
                    selected_item = item
                    break

        if selected_item:
            drink_text = f"{selected_item['code']} - {selected_item['name']}"
            user_choices[user_id] = {
                "name": user_name,
                "drink_code": drink_text
            }
            update_google_sheet(user_name, drink_text)

            user_states[user_id] = {
                "step": "sweetness",
                "options": selected_item.get("options", [])
            }

            if "sweetness" in selected_item.get("options", []):
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"sweetness_{opt}")] for opt in OPTIONS["sweetness_levels"]]
                await query.edit_message_text("🧁 Chọn độ ngọt:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif "tea" in selected_item.get("options", []):
                user_states[user_id]["step"] = "tea"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"tea_{opt}")] for opt in OPTIONS["tea_strengths"]]
                await query.edit_message_text("🍵 Chọn độ trà:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif "topping" in selected_item.get("options", []):
                user_states[user_id]["step"] = "topping"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"topping_{opt}")] for opt in OPTIONS["toppings"]]
                await query.edit_message_text("🍡 Chọn topping:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif "ice" in selected_item.get("options", []):
                user_states[user_id]["step"] = "ice"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"ice_{opt}")] for opt in OPTIONS["ices"]]
                await query.edit_message_text("🧊 Nóng/Đá:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text(f"✅ {user_name} đã chọn: {selected_item['code']} - {selected_item['name']}")
        return

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

async def reset_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choices.clear()
    user_states.clear()
    await update.message.reply_text("♻️ Danh sách đặt món đã được reset.")

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

async def update_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reload_data()
        await update.message.reply_text("✅ Đã tải lại menu và options từ file.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi tải: {str(e)}")

async def send_monthly_reminder(app):
    await app.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text="📣 Vui lòng chọn trà/cafe tháng này. Nhập lệnh /menu để xem chi tiết các món."
    )

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
    