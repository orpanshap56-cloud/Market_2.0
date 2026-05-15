import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

st.title("💖 Семейная Экономика: Задачи и Плюшки")

# Создаем подключение к Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Читаем данные
try:
    df = conn.read(worksheet="balances", ttl=0) # ttl=0 обновляет данные сразу
    муж_баланс = int(df.iloc[0]["Муж"])
    жена_баланс = int(df.iloc[0]["Жена"])
except Exception as e:
    st.error("База данных еще не настроена в Secrets или таблица заполнена неверно!")
    st.info("Убедись, что в Secrets добавлен URL, а в таблице на листе 'balances' в первой строке написано Муж и Жена, а во второй — числа.")
    муж_баланс, жена_баланс = 0, 0

# Список дел (если нужно изменить или добавить — правим прямо тут)
TASKS = [
    {"title": "Помыть посуду", "reward": 10, "assigned_to": "Муж"},
    {"title": "Приготовить обед", "reward": 15, "assigned_to": "Жена"},
    {"title": "Постирать вещи", "reward": 10, "assigned_to": "Муж"},
    {"title": "Убраться в комнате", "reward": 20, "assigned_to": "Оба"}
]

MARKET = [
    {"title": "Массаж спины", "price": 50, "seller": "Жена"},
    {"title": "Приготовление ужина на заказ", "price": 40, "seller": "Муж"},
    {"title": "Выходной от дел", "price": 100, "seller": "Оба"}
]

# --- БЛОК 1: БАЛАНС ---
st.header("💰 Текущий баланс")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Баланс Мужа", value=f"{муж_баланс} 🪙")
with col2:
    st.metric(label="Баланс Жены", value=f"{жена_баланс} 🪙")

st.markdown("---")

# --- БЛОК 2: ДОМАШНИЕ ДЕЛА ---
st.header("📋 Выполнение домашних дел")
current_user = st.selectbox("Кто сейчас у экрана?", ["Муж", "Жена"], key="user_select_tasks")

for i, task in enumerate(TASKS):
    col_task, col_btn = st.columns([3, 1])
    with col_task:
        st.write(f"**{task['title']}** — {task['reward']} 🪙 (Кому: {task['assigned_to']})")
    with col_btn:
        # Кнопка активна, если задача для всех ("Оба") или конкретно для того, кто у экрана
        is_my_task = (task['assigned_to'] == current_user or task['assigned_to'] == "Оба")
        if st.button(f"Выполнено!", key=f"task_{i}", disabled=not is_my_task):
            if current_user == "Муж":
                df.iloc[0]["Муж"] = муж_баланс + task['reward']
            else:
                df.iloc[0]["Жена"] = жена_баланс + task['reward']
            
            # Сохраняем в Google Таблицу
            conn.update(worksheet="balances", data=df)
            st.success(f"{current_user} получил(а) {task['reward']} 🪙!")
            st.rerun()

st.markdown("---")

# --- БЛОК 3: МАРКЕТПЛЕЙС ---
st.header("🛒 Маркетплейс")

for j, item in enumerate(MARKET):
    # Покупать можно только то, что продает партнер (или статус "Оба")
    if item['seller'] != current_user:
        col_item, col_buy = st.columns([3, 1])
        with col_item:
            st.write(f"🎁 **{item['title']}** — Цена: {item['price']} 🪙 (Продавец: {item['seller']})")
        with col_buy:
            active_balance = муж_баланс if current_user == "Муж" else_баланс = жена_баланс
            can_afford = active_balance >= item['price']
            
            if st.button(f"Купить", key=f"market_{j}", disabled=not can_afford):
                if current_user == "Муж":
                    df.iloc[0]["Муж"] = муж_баланс - item['price']
                    if item['seller'] == "Жена":
                        df.iloc[0]["Жена"] = жена_баланс + item['price']
                else:
                    df.iloc[0]["Жена"] = жена_баланс - item['price']
                    if item['seller'] == "Муж":
                        df.iloc[0]["Муж"] = муж_баланс + item['price']
                
                conn.update(worksheet="balances", data=df)
                st.balloons()
                st.success(f"Куплено!")
                st.rerun()
