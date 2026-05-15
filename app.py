import streamlit as st
import json
import os

# Настройки страницы
st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

DATA_FILE = "family_data.json"

# Дефолтные данные, если файла еще нет
DEFAULT_DATA = {
    "balances": {"Муж": 0, "Жена": 0},
    "tasks": [
        {"title": "Помыть посуду", "reward": 10, "assigned_to": "Муж"},
        {"title": "Приготовить обед", "reward": 15, "assigned_to": "Жена"},
        {"title": "Постирать вещи", "reward": 10, "assigned_to": "Муж"}
    ],
    "market": [
        {"title": "Массаж спины", "price": 50, "seller": "Жена"},
        {"title": "Приготовление ужина на заказ", "price": 40, "seller": "Муж"},
        {"title": "Вечер без домашних дел (выходной)", "price": 100, "seller": "Оба"}
    ]
}

# Функция для загрузки данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA

# Функция для сохранения данных
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализация данных в сессии Streamlit
if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

st.title("💖 Семейная Экономика: Задачи и Плюшки")

# --- БЛОК 1: БАЛАНС ---
st.header("💰 Текущий баланс")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Баланс Мужа", value=f"{data['balances']['Муж']} 🪙")
with col2:
    st.metric(label="Баланс Жены", value=f"{data['balances']['Жена']} 🪙")

st.markdown("---")

# --- БЛОК 2: ДОМАШНИЕ ДЕЛА ---
st.header("📋 Выполнение домашних дел")
st.subheader("Выбери, кто выполнил задачу, чтобы получить монетки:")

for i, task in enumerate(data["tasks"]):
    col_task, col_btn = st.columns([3, 1])
    with col_task:
        st.write(f"**{task['title']}** — 給 {task['reward']} 🪙 (Исполнитель: {task['assigned_to']})")
    with col_btn:
        if st.button(f"Выполнено!##{i}", key=f"task_{i}"):
            # Начисляем монеты тому, кто был назначен
            user = task['assigned_to']
            data["balances"][user] += task['reward']
            save_data(data)
            st.success(f"{user} получил(а) {task['reward']} 🪙!")
            st.rerun()

st.markdown("---")

# --- БЛОК 3: МАРКЕТПЛЕЙС ---
st.header("🛒 Маркетплейс плюшек")
st.subheader("Потрать свои монетки на награду от партнера:")

# Определим, кто зашел (для простоты добавим переключатель пользователя в самом низу или тут)
current_user = st.selectbox("Кто сейчас у экрана?", ["Муж", "Жена"])

for j, item in enumerate(data["market"]):
    # Покупать можно только то, что продает ПАРТНЕР (не ты сам)
    if item['seller'] != current_user:
        col_item, col_buy = st.columns([3, 1])
        with col_item:
            st.write(f"🎁 **{item['title']}** — Цена: {item['price']} 🪙 (Продавец: {item['seller']})")
        with col_buy:
            # Проверяем, хватает ли денег
            can_afford = data["balances"][current_user] >= item['price']
            if st.button(f"Купить##{j}", key=f"market_{j}", disabled=not can_afford):
                # Списываем у покупателя
                data["balances"][current_user] -= item['price']
                # Начисляем продавцу (если продавец не "Оба")
                if item['seller'] in data["balances"]:
                    data["balances"][item['seller']] += item['price']
                
                save_data(data)
                st.balloons()
                st.success(f"Ура! {current_user} купил '{item['title']}' за {item['price']} 🪙!")
                st.rerun()

st.markdown("---")

# --- БЛОК 4: УПРАВЛЕНИЕ (ДОБАВЛЕНИЕ НОВОГО) ---
st.sidebar.header("⚙️ Конструктор")
with st.sidebar.expander("➕ Добавить новую задачу"):
    new_task_title = st.text_input("Название дела")
    new_task_reward = st.number_input("Награда (монет)", min_value=1, value=10)
    new_task_user = st.selectbox("Кому назначить?", ["Муж", "Жена"])
    if st.button("Добавить задачу"):
        if new_task_title:
            data["tasks"].append({"title": new_task_title, "reward": int(new_task_reward), "assigned_to": new_task_user})
            save_data(data)
            st.success("Задача добавлена!")
            st.rerun()

with st.sidebar.expander("➕ Добавить товар в маркет"):
    new_item_title = st.text_input("Название ништяка")
    new_item_price = st.number_input("Цена (монет)", min_value=1, value=20)
    new_item_seller = st.selectbox("Кто предоставляет?", ["Муж", "Жена", "Оба"])
    if st.button("Добавить в магазин"):
        if new_item_title:
            data["market"].append({"title": new_item_title, "price": int(new_item_price), "seller": new_item_seller})
            save_data(data)
            st.success("Товар добавлен!")
            st.rerun()
