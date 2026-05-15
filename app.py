import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

PROFILES = {
    "Муж": {"avatar": "🧔‍♂️"},
    "Жена": {"avatar": "👩‍🦰"}
}

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

def save_data(sheet_name, df):
    conn.update(worksheet=sheet_name, data=df)

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ И КЭША БАЗЫ ДАННЫХ ---
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "main"

# Функция для принудительной загрузки данных из Гугла
def sync_database():
    with st.spinner("Синхронизация с базой..."):
        st.session_state.db = {
            "balances": get_data("balances"),
            "tasks": get_data("tasks"),
            "market": get_data("market"),
            "history": get_data("history")
        }

# Если базы в памяти еще нет — качаем её
if "db" not in st.session_state:
    try:
        sync_database()
    except Exception as e:
        st.error("Ошибка подключения к базе! Проверь листы в Гугл Таблице.")
        st.stop()

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

# --- ПОДГОТОВКА ДАННЫХ ИЗ КЭША ---
current_user = st.session_state.user
partner = "Жена" if current_user == "Муж" else "Муж"

db = st.session_state.db # Для удобства делаем короткую ссылку на кэш

муж_баланс = int(db["balances"].loc[0, "Муж"])
жена_баланс = int(db["balances"].loc[0, "Жена"])
муж_рейтинг = int(db["balances"].loc[0, "Муж_Рейтинг"])
жена_рейтинг = int(db["balances"].loc[0, "Жена_Рейтинг"])

my_balance = муж_баланс if current_user == "Муж" else жена_баланс
my_rating = муж_рейтинг if current_user == "Муж" else жена_рейтинг

# --- САЙДБАР (НАВИГАЦИЯ) ---
with st.sidebar:
    st.title(f"{PROFILES[current_user]['avatar']} {current_user}")
    
    st.metric("Кошелек", f"{my_balance} 🪙")
    st.metric("Рейтинг активности", f"{my_rating} 💖")
    
    st.markdown("---")
    if st.button("🏠 Главная", use_container_width=True):
        st.session_state.page = "main"; st.rerun()
    if st.button("👤 Личный кабинет", use_container_width=True):
        st.session_state.page = "profile"; st.rerun()
    
    st.markdown("---")
    # Кнопка для ручного обновления данных
    if st.button("🔄 Обновить данные", use_container_width=True):
        sync_database()
        st.rerun()
        
    if st.button("🚪 Сменить профиль", use_container_width=True):
        st.session_state.user = None; st.rerun()

# ==========================================
# ЭКРАН 1: ГЛАВНАЯ
# ==========================================
if st.session_state.page == "main":
    st.title("💖 Семейная Экономика")
    
    # ЗАДАЧИ
    st.header("📋 Задачи")
    for i, row in db["tasks"].iterrows():
        c1, c2 = st.columns([3, 1])
        is_my = row['assigned_to'] in [current_user, "Оба"]
        if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
            # Обновляем локально
            if current_user == "Муж": db["balances"].loc[0, "Муж"] += int(row['reward'])
            else: db["balances"].loc[0, "Жена"] += int(row['reward'])
            
            new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
            db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
            
            # Отправляем в Гугл
            save_data("balances", db["balances"])
            save_data("history", db["history"])
            st.rerun()
        c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")

    # МАРКЕТПЛЕЙС
    st.header("🛒 Маркет")
    for j, row in db["market"].iterrows():
        c1, c2 = st.columns([3, 1])
        price = int(row['price'])
        
        is_my_item = (row['seller'] == current_user)
        can_buy = (not is_my_item) and (my_balance >= price)
        btn_label = "Мой лот" if is_my_item else "Купить"
        
        if c2.button(btn_label, key=f"m_{j}", disabled=not can_buy):
            # Обновляем локально
            if current_user == "Муж":
                db["balances"].loc[0, "Муж"] -= price 
                if row['seller'] == "Жена": 
                    db["balances"].loc[0, "Жена_Рейтинг"] += price 
            else:
                db["balances"].loc[0, "Жена"] -= price 
                if row['seller'] == "Муж": 
                    db["balances"].loc[0, "Муж_Рейтинг"] += price 
            
            new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": price, "seller": row['seller'], "type": "Покупка"}])
            db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
            
            # Отправляем в Гугл
            save_data("balances", db["balances"])
            save_data("history", db["history"])
            st.balloons(); st.rerun()
            
        display_name = f"🎁 **{row['title']}** ({price} 🪙)"
        if is_my_item: display_name += " *(Ваше предложение)*"
        c1.write(display_name)

    # ФОРМЫ ДОБАВЛЕНИЯ
    with st.expander("➕ Добавить задачу/лот"):
        tab1, tab2 = st.tabs(["Задача", "Лот"])
        with tab1:
            with st.form("f1", clear_on_submit=True):
                t = st.text_input("Название"); r = st.number_input("Награда", min_value=1)
                a = st.selectbox("Кто?", ["Муж", "Жена", "Оба"])
                if st.form_submit_button("Создать"):
                    db["tasks"] = pd.concat([db["tasks"], pd.DataFrame([{"title":t, "reward":r, "assigned_to":a}])], ignore_index=True)
                    save_data("tasks", db["tasks"])
                    st.rerun()
        with tab2:
            with st.form("f2", clear_on_submit=True):
                t = st.text_input("Товар"); p = st.number_input("Цена", min_value=1)
                s = st.selectbox("Продавец", ["Муж", "Жена", "Оба"], index=0 if current_user=="Муж" else 1)
                if st.form_submit_button("Выставить"):
                    db["market"] = pd.concat([db["market"], pd.DataFrame([{"title":t, "price":p, "seller":s}])], ignore_index=True)
                    save_data("market", db["market"])
                    st.rerun()

# ==========================================
# ЭКРАН 2: ЛИЧНЫЙ КАБИНЕТ
# ==========================================
elif st.session_state.page == "profile":
    st.title("👤 Личный кабинет")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("Заработано 🪙", f"{db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Работа')]['price'].sum()}")
    col_info2.metric("Потрачено 🪙", f"{db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Покупка')]['price'].sum()}")
    col_info3.metric("Рейтинг 💖", f"{my_rating}")

    st.subheader("📦 Мои товары на витрине")
    my_lots = db["market"][db["market"]['seller'] == current_user]
    if not my_lots.empty:
        st.table(my_lots[['title', 'price']])
    else:
        st.write("Вы еще ничего не выставили на продажу.")

    st.subheader("🛍️ История покупок")
    my_buys = db["history"][(db["history"]['buyer'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_buys.empty:
        st.dataframe(my_buys[['item', 'price', 'seller']], use_container_width=True, hide_index=True)
    else:
        st.write("Вы еще ничего не купили.")
    
    st.subheader("💖 За что получен рейтинг")
    my_sales = db["history"][(db["history"]['seller'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_sales.empty:
        display_sales = my_sales[['item', 'price', 'buyer']].copy()
        display_sales = display_sales.rename(columns={'price': 'получено 💖'})
        st.dataframe(display_sales, use_container_width=True, hide_index=True)
    else:
        st.write("Ваши лоты еще не покупали.")
