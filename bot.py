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
from collections import defaultdict

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

reload_data()

user_choices = {}  # {user_id: {name, drink_code, sweetness, tea, topping, size}}
user_states = {}   # {user_id: {step, options}}

# Lưu vào Google Sheets
def save_to_google_sheets(data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.environ.get("CREDENTIAL_JSON_CONTENT"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet_url = "https://docs.google.com/spreadsheets/d/1FP-6syh0tBAf4Bdx4wzM9w9ENP9iSukMI_8Cwll2nLE"
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("Bot")

        name = data.get("name", "").strip()
        all_records = worksheet.get_all_records()

        found = False
        for idx, record in enumerate(all_records, start=2):  # start=2 vì dòng 1 là tiêu đề
            if record.get("Tên", "").strip() == name:
                worksheet.update(f'A{idx}:H{idx}', [[
                    data.get("name", ""),
                    data.get("drink_code", ""),
                    data.get("sweetness", ""),
                    data.get("tea", ""),
                    data.get("topping", ""),
                    data.get("ice", ""),
                    data.get("size", ""),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]])
                found = True
                break

        if not found:
            worksheet.append_row([
                data.get("name", ""),
                data.get("drink_code", ""),
                data.get("sweetness", ""),
                data.get("tea", ""),
                data.get("topping", ""),
                data.get("ice", ""),
                data.get("size", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

        print("✅ Đã ghi dữ liệu vào Google Sheets.")
    except Exception as e:
        print("❌ Lỗi khi ghi Google Sheets:", e)


# Lệnh khởi động
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Chào mừng bạn với bot đặt trà/cafe!\nGõ: \n /menu để xem danh sách đồ uống.\n /list để xem danh sách các thành viên đã đặt món.\n /reset để xoá danh sách đã chọn món.\n /export để xuất danh sách đã chọn món ra excel.")

# Lệnh hiển thị menu
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(text=data["name"], callback_data=f"menu_{code}")]
        for code, data in MENU_STRUCTURE.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏢 Chọn MENU:", reply_markup=reply_markup)

# Xử lý chọn menu và món
async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if data == "ignore":
        return

    if data.startswith("menu_"):
        menu_code = data.replace("menu_", "")
        if menu_code in MENU_STRUCTURE:
            items = MENU_STRUCTURE[menu_code]["items"]
            grouped_items = defaultdict(list)
            for item in items:
                group = item.get("group", "Khác")
                grouped_items[group].append(item)

            keyboard = []
            for group_name, group_items in grouped_items.items():
                keyboard.append([InlineKeyboardButton(text=f"📂 {group_name}", callback_data="ignore")])
                for item in group_items:
                    keyboard.append([
                        InlineKeyboardButton(text=f"{item['code']} - {item['name']}", callback_data=f"item_{item['code']}")
                    ])

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
            user_choices[user_id] = {
                "name": user_name,
                "drink_code": f"{selected_item['code']} - {selected_item['name']}"
            }
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
            elif "size" in selected_item.get("options", []):
                user_states[user_id]["step"] = "size"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"size_{opt}")] for opt in OPTIONS["sizes"]]
                await query.edit_message_text("👝 Size:", reply_markup=InlineKeyboardMarkup(keyboard))
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
            elif category == "topping" and "ice" in current_options:
                next_step = "ice"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"ice_{opt}")] for opt in OPTIONS["ices"]]
                await query.edit_message_text("🧊 Nóng/Đá:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif category == "ice" and "size" in current_options:
                next_step = "size"
                keyboard = [[InlineKeyboardButton(text=opt, callback_data=f"size_{opt}")] for opt in OPTIONS["sizes"]]
                await query.edit_message_text("👝 Size:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text(f"✅ {user_choices[user_id]['name']} đã hoàn tất đặt món.")
                save_to_google_sheets(user_choices[user_id])
                user_states.pop(user_id, None)

            if next_step:
                user_states[user_id]["step"] = next_step

# Lệnh /list
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
        if "ice" in data:
            detail += f" | Nóng/Đá: {data['ice']}"
        if "size" in data:
            detail += f" | Size: {data['size']}"
        response += f"- {data['name']}: {detail}\n"

    await update.message.reply_text(response)

# Lệnh /reset
# Lệnh /reset
async def reset_choices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choices.clear()
    user_states.clear()

    try:
        # Kết nối Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(os.environ.get("CREDENTIAL_JSON_CONTENT"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet_url = "https://docs.google.com/spreadsheets/d/1FP-6syh0tBAf4Bdx4wzM9w9ENP9iSukMI_8Cwll2nLE"
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet("Bot")

        # Lấy tất cả giá trị
        data = worksheet.get_all_values()
        if len(data) <= 1:
            await update.message.reply_text("♻️ Danh sách trên Google Sheets đã trống hoặc chỉ có tiêu đề.")
            return

        # Xoá nội dung từ dòng 2 trở đi, trừ cột "Tên"
        for row_index in range(2, len(data)+1):
            worksheet.batch_update([{
                "range": f"B{row_index}:H{row_index}",  # Xoá từ cột B đến H (giữ cột A là "Tên")
                "values": [[""] * (len(data[0]) - 1)]
            }])

        await update.message.reply_text("♻️ Danh sách đã được xoá.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi xoá dữ liệu Google Sheets: {str(e)}")


# Lệnh /export
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
            "Topping": d.get("topping", ""),
            "Nóng/Đá": d.get("ice", ""),
            "Size": d.get("size", "")
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

# Lệnh /update
async def update_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reload_data()
        await update.message.reply_text("✅ Đã tải lại menu và options từ file.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi tải: {str(e)}")

# Gửi nhắc định kỳ
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
