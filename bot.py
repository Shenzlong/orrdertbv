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
from collections import defaultdict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Ghi credentials từ biến môi trường thành file
GOOGLE_CREDS = os.environ.get("CREDENTIAL_JSON_CONTENT")
with open("credentials.json", "w", encoding="utf-8") as f:
    f.write(GOOGLE_CREDS)

# Kết nối Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet_bot = gc.open_by_url("https://docs.google.com/spreadsheets/d/1FP-6syh0tBAf4Bdx4wzM9w9ENP9iSukMI_8Cwll2nLE/edit").worksheet("Bot")

# Biến môi trường bot
TOKEN = os.environ.get("BOT_TOKEN")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID")

# Tải menu và options
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
reload_data()

user_choices = {}
user_states = {}

# ... (start_command, menu_command, v.v. giữ nguyên như cũ)

# 🧠 CHỈ THAY ĐỔI HÀM handle_menu_choice (phần cuối)
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    # (Giữ nguyên xử lý menu_ và item_...)

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
            elif category == "topping" and "ice" in current_options:
                next_step = "ice"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"ice_{opt}")] for opt in OPTIONS["ices"]]
                await query.edit_message_text("🧊 Nóng/Đá:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text(f"✅ {user_choices[user_id]['name']} đã hoàn tất đặt món.")
                # Ghi vào Google Sheet
                try:
                    data = user_choices[user_id]
                    row = [
                        data.get("name", ""),
                        data.get("drink_code", ""),
                        data.get("sweetness", ""),
                        data.get("tea", ""),
                        data.get("topping", ""),
                        data.get("ice", ""),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    sheet_bot.append_row(row)
                except Exception as e:
                    print(f"[❌] Ghi Google Sheet lỗi: {str(e)}")
                user_states.pop(user_id, None)

            if next_step:
                user_states[user_id]["step"] = next_step

# ... (giữ nguyên các hàm còn lại)

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
