import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Семейная Монетизация", page_icon="💰")

st.title("💖 Семейная Экономика: Задачи и Плюшки")

# Создаем подключение к Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Читаем данные (укажи имя своего листа, например 'balances')
# Мы храним там только баланс, а задачи оставим в коде, так как они статичны
try:
    df = conn.read(worksheet="balances", ttl=0) # ttl=0 значит обновлять данные сразу, без кэша
    муж_баланс = int(df.iloc[0]["Муж"])
    жена_баланс = int(df.iloc[0]["Жена"])
except Exception as e:
    st.error("База данных еще не настроена в Secrets. Инструкция ниже!")
    муж_баланс, женат_баланс = 0, 0

# Дефолтные списки (чтобы не усложнять таблицу, пусть дела живут в коде)
TASKS = [
    {"title": "Помыть посуду", "reward": 10, "assigned_to": "Муж"},
    {"title": "Приготовить обед", "reward": 15, "assigned_to": "Жена"},
    {"title": "Постирать вещи", "reward": 10, "assigned_to": "Муж"}
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
for i, task in enumerate(TASKS):
    col_task, col_btn = st.columns([3, 1])
    with col_task:
        st.write(f"**{task['title']}** —  {task['reward']} 🪙 ({task['assigned_to']})")
    with col_btn:
        if st.button(f"Выполнено!", key=f"task_{i}"):
            if task['assigned_to'] == "Муж":
                df.iloc[0]["Муж"] = муж_баланс + task['reward']
            else:
                df.iloc[0]["Жена"] = жена_баланс + task['reward']
            
            # Сохраняем в Google Таблицу
            conn.update(worksheet="balances", data=df)
            st.success("Монетки улетели на баланс!")
            st.rerun()

st.markdown("---")

# --- БЛОК 3: МАРКЕТПЛЕЙС ---
st.header("🛒 Маркетплейс")
current_user = st.selectbox("Кто у экрана?", ["Муж", "Жена"])

for j, item in enumerate(MARKET):
    if item['seller'] != current_user:
        col_item, col_buy = st.columns([3, 1])
        with col_item:
            st.write(f"🎁 **{item['title']}** — Цена: {item['price']} 🪙")
        with col_buy:
            user_balance = муж_баланс if current_user == "Муж" else женат_баланс
            can_afford = user_balance >= item['price']
            if st.button(f"Купить", key=f"market_{j}", disabled=not can_afford):
                if current_user == "Муж":
                    df.iloc[0]["Муж"] = муж_баланс - item['price']
                    if item['seller'] == "Жена":
                        df.iloc[0]["Жена"] = жена_баланс + item['price']
                else:
                    df.iloc[0]["Жена"] = женат_баланс - item['price']
                    if item['seller'] == "Муж":
                        df.iloc[0]["Муж"] = муж_баланс + item['price']
                
                conn.update(worksheet="balances", data=df)
                st.balloons()
                st.rerun()
