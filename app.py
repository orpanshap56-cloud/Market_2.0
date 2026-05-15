import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

PROFILES = {
    "Муж": {"avatar": "🧔‍♂️"},
    "Жена": {"avatar": "👩‍🦰"}
}

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "main" # По умолчанию главная

# --- ЭКРАН ВЫБОРА ПРОФИЛЯ ---
if st.session_state.user is None:
    st.title("Привет! Кто сегодня молодец? 😎")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"{PROFILES['Муж']['avatar']} Я Муж", use_container_width=True):
            st.session_state.user = "Муж"; st.rerun()
    with col2:
        if st.button(f"{PROFILES['Жена']['avatar']} Я Жена", use_container_width=True):
            st.session_state.user = "Жена"; st.rerun()
    st.stop() 

# --- ПОДКЛЮЧЕНИЕ И ДАННЫЕ ---
current_user = st.session_state.user
partner = "Жена" if current_user == "Муж" else "Муж"
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

def save_data(sheet_name, df):
    conn.update(worksheet=sheet_name, data=df)

try:
    df_balances = get_data("balances")
    df_tasks = get_data("tasks")
    df_market = get_data("market")
    df_history = get_data("history") # Лист с историей
    муж_баланс = int(df_balances.loc[0, "Муж"])
    жена_баланс = int(df_balances.loc[0, "Жена"])
except:
    st.error("Ошибка базы! Проверь листы: balances, tasks, market, history.")
    st.stop()

my_balance = муж_баланс if current_user == "Муж" else жена_баланс

# --- САЙДБАР (НАВИГАЦИЯ) ---
with st.sidebar:
    st.title(f"{PROFILES[current_user]['avatar']} {current_user}")
    st.metric("Мой баланс", f"{my_balance} 🪙")
    
    st.markdown("---")
    if st.button("🏠 Главная", use_container_width=True):
        st.session_state.page = "main"; st.rerun()
    if st.button("👤 Личный кабинет", use_container_width=True):
        st.session_state.page = "profile"; st.rerun()
    
    st.markdown("---")
    if st.button("🔄 Сменить профиль", use_container_width=True):
        st.session_state.user = None; st.rerun()

# ==========================================
# ЭКРАН 1: ГЛАВНАЯ
# ==========================================
if st.session_state.page == "main":
    st.title("💖 Семейная Экономика")
    
    # ЗАДАЧИ
    st.header("📋 Задачи")
    for i, row in df_tasks.iterrows():
        c1, c2 = st.columns([3, 1])
        is_my = row['assigned_to'] in [current_user, "Оба"]
        if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
            if current_user == "Муж": df_balances.loc[0, "Муж"] += int(row['reward'])
            else: df_balances.loc[0, "Жена"] += int(row['reward'])
            
            # Пишем в историю
            new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
            save_data("history", pd.concat([df_history, new_log]))
            save_data("balances", df_balances)
            st.rerun()
        c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")

    # МАРКЕТПЛЕЙС
    st.header("🛒 Маркет")
    for j, row in df_market.iterrows():
        if row['seller'] != current_user:
            c1, c2 = st.columns([3, 1])
            price = int(row['price'])
            if c2.button("Купить", key=f"m_{j}", disabled=my_balance < price):
                if current_user == "Муж":
                    df_balances.loc[0, "Муж"] -= price
                    if row['seller'] == "Жена": df_balances.loc[0, "Жена"] += price
                else:
                    df_balances.loc[0, "Жена"] -= price
                    if row['seller'] == "Муж": df_balances.loc[0, "Муж"] += price
                
                # Пишем в историю
                new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": price, "seller": row['seller'], "type": "Покупка"}])
                save_data("history", pd.concat([df_history, new_log]))
                save_data("balances", df_balances)
                st.balloons(); st.rerun()
            c1.write(f"🎁 **{row['title']}** ({price} 🪙)")

    # ФОРМЫ ДОБАВЛЕНИЯ (в экспандерах)
    with st.expander("➕ Добавить задачу/лот"):
        tab1, tab2 = st.tabs(["Задача", "Лот"])
        with tab1:
            with st.form("f1", clear_on_submit=True):
                t = st.text_input("Название"); r = st.number_input("Награда", min_value=1)
                a = st.selectbox("Кто?", ["Муж", "Жена", "Оба"])
                if st.form_submit_button("Создать"):
                    save_data("tasks", pd.concat([df_tasks, pd.DataFrame([{"title":t, "reward":r, "assigned_to":a}])]))
                    st.rerun()
        with tab2:
            with st.form("f2", clear_on_submit=True):
                t = st.text_input("Товар"); p = st.number_input("Цена", min_value=1)
                s = st.selectbox("Продавец", ["Муж", "Жена", "Оба"], index=0 if current_user=="Муж" else 1)
                if st.form_submit_button("Выставить"):
                    save_data("market", pd.concat([df_market, pd.DataFrame([{"title":t, "price":p, "seller":s}])]))
                    st.rerun()

# ==========================================
# ЭКРАН 2: ЛИЧНЫЙ КАБИНЕТ
# ==========================================
elif st.session_state.page == "profile":
    st.title("👤 Личный кабинет")
    
    col_info1, col_info2 = st.columns(2)
    col_info1.metric("Заработано всего", f"{df_history[(df_history['buyer'] == current_user) & (df_history['type'] == 'Работа')]['price'].sum()} 🪙")
    col_info2.metric("Потрачено всего", f"{df_history[(df_history['buyer'] == current_user) & (df_history['type'] == 'Покупка')]['price'].sum()} 🪙")

    st.subheader("📦 Мои товары на витрине")
    my_lots = df_market[df_market['seller'] == current_user]
    if not my_lots.empty:
        st.table(my_lots[['title', 'price']])
    else:
        st.write("Вы еще ничего не выставили на продажу.")

    st.subheader("🛍️ История покупок")
    my_buys = df_history[(df_history['buyer'] == current_user) & (df_history['type'] == 'Покупка')]
    if not my_buys.empty:
        st.dataframe(my_buys[['item', 'price', 'seller']], use_container_width=True, hide_index=True)
    else:
        st.write("Вы еще ничего не купили.")
    
    st.subheader("💰 Мои продажи (выручка)")
    my_sales = df_history[(df_history['seller'] == current_user) & (df_history['type'] == 'Покупка')]
    if not my_sales.empty:
        st.dataframe(my_sales[['item', 'price', 'buyer']], use_container_width=True, hide_index=True)
    else:
        st.write("У вас еще ничего не купили.")
