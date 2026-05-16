import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройки из переменных окружения (настроим в GitHub)
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_IDS = {
    "Муж": os.environ["MY_CHAT_ID"],
    "Жена": os.environ["WIFE_CHAT_ID"]
}

def send_tg(text, target_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": target_id, "text": text})

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.environ["G_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Читаем таблицу
sheet_url = "https://docs.google.com/spreadsheets/d/1CZA4Ugy4iuMV-KhG2X0fnhq1zaxeHPkEa5rBcHHoxUM/edit"
sheet = client.open_by_url(sheet_url).worksheet("tasks")
df = pd.DataFrame(sheet.get_all_records())

now = datetime.now()
ready_tasks = {"Муж": [], "Жена": []}
CHECK_WINDOW_HOURS = 6 # Теперь проверяем окно в 6 часов

for i, row in df.iterrows():
    if row['task_type'] == "Интервальная":
        last_val = str(row['last_completed'])
        if last_val and last_val != "" and last_val != "nan":
            last_dt = pd.to_datetime(last_val)
            val = int(row['interval_value'])
            unit = row['interval_unit']
            
            offset = timedelta(hours=val) if unit == "Часы" else timedelta(days=val)
            next_available = last_dt + offset
            
            # Считаем разницу в секундах
            time_diff = (now - next_available).total_seconds()
            
            # Если задача стала доступна в последние 6 часов (21600 секунд)
            # Добавляем небольшой буфер (5 минут / 300 сек) на случай задержки запуска
            if 0 <= time_diff < (CHECK_WINDOW_HOURS * 3600 + 300):
                target = row['assigned_to']
                if target == "Оба":
                    ready_tasks["Муж"].append(row['title'])
                    ready_tasks["Жена"].append(row['title'])
                else:
                    ready_tasks[target].append(row['title'])

# Отправляем уведомления о задачах
for user, tasks in ready_tasks.items():
    if tasks:
        msg = "🆕 Задания снова доступны:\n" + "\n".join([f"— {t}" for t in tasks])
        send_tg(msg, CHAT_IDS[user])

# Напоминалка раз в 3 дня (Пн и Чт)
# 🔥 Добавляем проверку времени (now.hour), чтобы она приходила только один раз в день (например, в 12:00)
if now.weekday() in [0, 3] and 11 <= now.hour <= 13:
    send_tg("🔔 Не забывайте заходить в приложение и отмечать успехи! 💰", CHAT_IDS["Муж"])
    send_tg("🔔 Не забывайте заходить в приложение и отмечать успехи! 💰", CHAT_IDS["Жена"])
