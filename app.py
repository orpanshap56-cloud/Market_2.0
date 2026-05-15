import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. НАСТРОЙКИ СТРАНИЦЫ (всегда на самом верху)
st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

# 2. ПРОФИЛИ И СЕССИЯ
PROFILES = {
    "Муж": {"avatar": "🧔‍♂️", "color": "blue"},
    "Жена": {"avatar": "👩‍🦰", "color": "pink"}
}

if "user" not in st.session_state:
    st.session_state.user = None

# 3. ЭКРАН ВЫБОРА ПРОФИЛЯ
if st.session_state.user is None:
    st.title("Привет! Кто сегодня молодец? 😎")
    st.write("Выбери свой профиль:")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{PROFILES['Муж']['avatar']} Я Муж", use_container_width=True):
            st.session_state.user = "Муж"
            st.rerun()
    with col2:
        if st.button(f"{PROFILES['Жена']['avatar']} Я Жена", use_container_width=True):
            st.session_state.user = "Жена"
            st.rerun()
            
    st.stop() # Дальше код не идет, пока профиль не выбран

# ==========================================
# 4. ОСНОВНОЙ ИНТЕРФЕЙС (ПРОФИЛЬ ВЫБРАН)
# ==========================================
current_user = st.session_state.user
partner = "Жена" if current_user == "Муж" else "Муж"

# Коннект к базе Гугла
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

def save_data(sheet_name, df):
    conn.update(worksheet=sheet_name, data=df)

# Читаем данные из обеих вкладок
try:
    df_balances = get_data("balances")
    df_tasks = get_data("tasks")
    муж_баланс = int(df_balances.loc[0, "Муж"])
    жена_баланс = int(df_balances.loc[0, "Жена"])
except Exception as e:
    st.error("Ошибка загрузки данных! Проверь листы 'balances' и 'tasks' в Гугл Таблице.")
    st.stop()

# Определяем, где чей баланс
my_balance = муж_баланс if current_user == "Муж" else жена_баланс
partner_balance = жена_баланс if current_user == "Муж" else муж_баланс

# --- БОКОВАЯ ПАНЕЛЬ (ЛИЧНЫЙ КАБИНЕТ) ---
with st.sidebar:
    st.title(f"{PROFILES[current_user]['avatar']} Мой профиль")
    st.metric(label="Мой капитал", value=f"{my_balance} 🪙")
    
    st.markdown("🏆 **Достижения:**")
    st.caption("Пока пусто, но скоро будут!")
    
    st.markdown("---")
    if st.button("🔄 Сменить профиль", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- ЦЕНТРАЛЬНАЯ ЧАСТЬ ---
st.title("💖 Семейная Экономика")
st.info(f"Баланс партнера ({partner}): **{partner_balance} 🪙**")
st.markdown("---")

# --- БЛОК ДОМАШНИХ ДЕЛ ---
st.header("📋 Задачи на сегодня")

for i, row in df_tasks.iterrows():
    col_task, col_btn = st.columns([3, 1])
    with col_task:
        st.write(f"**{row['title']}** — {row['reward']} 🪙 (Кому: {row['assigned_to']})")
    with col_btn:
        # Проверяем, может ли текущий профиль выполнить задачу
        is_my_task = (row['assigned_to'] in [current_user, "Оба"])
        if st.button("Готово!", key=f"task_{i}", disabled=not is_my_task):
            if current_user == "Муж":
                df_balances.loc[0, "Муж"] = муж_баланс + int(row['reward'])
            else:
                df_balances.loc[0, "Жена"] = жена_баланс + int(row['reward'])
            
            save_data("balances", df_balances)
            st.success("Монетки начислены!")
            st.rerun()

st.markdown("---")

# --- БЛОК СОЗДАНИЯ НОВЫХ ЗАДАЧ ---
with st.expander("➕ Добавить новую задачу"):
    with st.form("new_task_form", clear_on_submit=True):
        new_title = st.text_input("Что нужно сделать?")
        new_reward = st.number_input("Награда (🪙)", min_value=1, value=10)
        new_assignee = st.selectbox("Кто выполняет?", ["Муж", "Жена", "Оба"])
        submit_task = st.form_submit_button("Создать задачу")
        
        if submit_task and new_title:
            new_row = pd.DataFrame([{"title": new_title, "reward": new_reward, "assigned_to": new_assignee}])
            df_tasks = pd.concat([df_tasks, new_row], ignore_index=True)
            save_data("tasks", df_tasks)
            st.success("Задача добавлена в базу!")
            st.rerun()

st.markdown("---")

# --- МАРКЕТПЛЕЙС (пока зашит в код) ---
MARKET = [
    {"title": "Массаж спины", "price": 50, "seller": "Жена"},
    {"title": "Приготовление ужина на заказ", "price": 40, "seller": "Муж"},
    {"title": "Выходной от дел", "price": 100, "seller": "Оба"}
]

st.header("🛒 Маркетплейс")

for j, item in enumerate(MARKET):
    # Не показываем свои же товары для покупки (или показываем, если "Оба")
    if item['seller'] != current_user:
        col_item, col_buy = st.columns([3, 1])
        with col_item:
            st.write(f"🎁 **{item['title']}** — Цена: {item['price']} 🪙 (Продавец: {item['seller']})")
        with col_buy:
            can_afford = my_balance >= item['price']
            
            if st.button("Купить", key=f"market_{j}", disabled=not can_afford):
                if current_user == "Муж":
                    df_balances.loc[0, "Муж"] = муж_баланс - item['price']
                    if item['seller'] == "Жена":
                        df_balances.loc[0, "Жена"] = жена_баланс + item['price']
                else:
                    df_balances.loc[0, "Жена"] = жена_баланс - item['price']
                    if item['seller'] == "Муж":
                        df_balances.loc[0, "Муж"] = муж_баланс + item['price']
                
                save_data("balances", df_balances)
                st.balloons()
                st.success("Куплено!")
                st.rerun()
