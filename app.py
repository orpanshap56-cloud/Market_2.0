import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Семейная Экономика", page_icon="💰", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name): return conn.read(worksheet=sheet_name, ttl=0)
def save_data(sheet_name, df): conn.update(worksheet=sheet_name, data=df)

def sync_database():
    st.session_state.db = {
        "balances": get_data("balances"),
        "tasks": get_data("tasks"),
        "market": get_data("market"),
        "history": get_data("history")
    }

if "db" not in st.session_state: sync_database()
if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "tasks"

# --- ПОДГОТОВКА ДАННЫХ ИЗ КЭША ---
if "db" not in st.session_state: sync_database()
db = st.session_state.db 

# Аккуратно читаем ники (чтобы код не упал, если колонок вдруг нет)
h_name = db["balances"].loc[0, "Муж_Имя"] if "Муж_Имя" in db["balances"].columns else "Муж"
w_name = db["balances"].loc[0, "Жена_Имя"] if "Жена_Имя" in db["balances"].columns else "Жена"

# Словарь для перевода системной роли в красивый ник
DISPLAY = {"Муж": h_name, "Жена": w_name, "Оба": "Оба"}

# --- ЭКРАН ВЫБОРА ПРОФИЛЯ ---
if "user" not in st.session_state: st.session_state.user = None
if st.session_state.user is None:
    st.title("Кто сегодня молодец? 😎")
    c1, c2 = st.columns(2)
    if c1.button(f"Я {DISPLAY['Муж']}", use_container_width=True): st.session_state.user = "Муж"; st.rerun()
    if c2.button(f"Я {DISPLAY['Жена']}", use_container_width=True): st.session_state.user = "Жена"; st.rerun()
    st.stop()

current_user = st.session_state.user
partner = "Жена" if current_user == "Муж" else "Муж"

db = st.session_state.db
current_user = st.session_state.user
my_balance = int(db["balances"].loc[0, current_user])
my_rating = int(db["balances"].loc[0, f"{current_user}_Рейтинг"])

# --- САЙДБАР ---
with st.sidebar:
    st.title(f"{DISPLAY[current_user]}")
    st.metric("Кошелек", f"{my_balance} 🪙")
    st.metric("Рейтинг", f"{my_rating} 💖")
    
    st.markdown("---")
    if st.button("🔄 Синхронизировать", use_container_width=True): sync_database(); st.rerun()
    
    # НОВЫЕ КНОПКИ НАВИГАЦИИ
    if st.button("📋 Список задач", use_container_width=True):
        st.session_state.page = "tasks"; st.rerun()
    if st.button("🛒 Маркетплейс", use_container_width=True):
        st.session_state.page = "market"; st.rerun()
    if st.button("👤 Личный кабинет", use_container_width=True):
        st.session_state.page = "profile"; st.rerun()
        
    st.markdown("---")
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.user = None; st.rerun()


# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ЗАДАЧИ)
# ==========================================
if st.session_state.page == "tasks":
    st.header("📋 Твои задачи")
    now = datetime.now()

    # --- ФОРМА СОЗДАНИЯ ---
    with st.expander("➕ Добавить задачу"):
        title = st.text_input("Что сделать?")
        reward = st.number_input("Награда", min_value=1, value=10)
        assignee = st.selectbox("Кто?", ["Муж", "Жена", "Оба"], format_func=lambda x: DISPLAY.get(x, x))
        t_type = st.radio("Режим", ["Разовая", "Интервальная"])
        
        val, unit = 0, ""
        
        if t_type == "Интервальная":
            c_val, c_unit = st.columns(2)
            val = c_val.number_input("Интервал", min_value=1, value=12)
            unit = c_unit.selectbox("Единица", ["Часы", "Дни"])
            
        if st.button("Создать"):
            if not title:
                st.warning("Напиши название задачи!")
            else:
                new_task = {
                    "title": title, 
                    "reward": reward, 
                    "assigned_to": assignee, 
                    "task_type": t_type, 
                    "interval_value": val, 
                    "interval_unit": unit, 
                    "last_completed": "",
                    "created_by": current_user
                }
                db["tasks"] = pd.concat([db["tasks"], pd.DataFrame([new_task])], ignore_index=True)
                save_data("tasks", db["tasks"])
                st.success("Задача добавлена!")
                st.rerun()
                
   # --- ВЫВОД ЗАДАЧ ---
    db["tasks"] = db["tasks"].reset_index(drop=True) 
    
    for i, row in db["tasks"].iterrows():
        t_type = row.get('task_type', 'Разовая')
        is_my = row['assigned_to'] in [current_user, "Оба"]
        
        raw_creator = row.get('created_by')
        creator = raw_creator if pd.notna(raw_creator) and raw_creator != "" else "Система"
        
        assignee_label = DISPLAY.get(row['assigned_to'], row['assigned_to'])
        creator_label = DISPLAY.get(creator, creator)
        
        c1, c2, c3 = st.columns([3, 1, 0.5])
        
        if c3.button("🗑️", key=f"del_t_{i}", help="Удалить задачу"):
            db["tasks"] = db["tasks"].drop(i)
            save_data("tasks", db["tasks"])
            st.rerun()

        if t_type == "Интервальная":
            raw_last_done = row.get('last_completed')
            val = int(row.get('interval_value', 0))
            unit = row.get('interval_unit', 'Часы')
            
            can_do = True
            time_text = ""
            
            if pd.notna(raw_last_done) and str(raw_last_done).strip() != "" and str(raw_last_done) != "nan":
                try:
                    last_done_dt = pd.to_datetime(str(raw_last_done))
                    if last_done_dt.tzinfo is not None:
                        last_done_dt = last_done_dt.tz_localize(None)
                        
                    if unit == "Часы":
                        next_available = last_done_dt + timedelta(hours=val)
                    else:
                        next_available = last_done_dt + timedelta(days=val)
                    
                    if now < next_available:
                        can_do = False
                        diff = next_available - now
                        if diff.days > 0:
                            time_text = f"⏳ Доступно через {diff.days}д {diff.seconds // 3600}ч"
                        else:
                            hours, remainder = divmod(diff.seconds, 3600)
                            minutes, _ = divmod(remainder, 60)
                            time_text = f"⏳ Доступно через {hours}ч {minutes}м"
                except Exception as e:
                    can_do = False
                    time_text = f"⚠️ Ошибка даты"
            
            if can_do:
              c1.write(f"**{str(row['title']).strip()}** (+{row['reward']} 🪙)")
            c1.caption(f"✍️ От: {creator_label} | 🎯 Для: {assignee_label}")
                
            if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
                    db["balances"].loc[0, current_user] += int(row['reward'])
                    db["tasks"]['last_completed'] = db["tasks"]['last_completed'].astype(str)
                    db["tasks"].at[i, 'last_completed'] = now.strftime('%Y-%m-%d %H:%M:%S')
                    
                    new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
                    db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                    save_data("balances", db["balances"]); save_data("tasks", db["tasks"]); save_data("history", db["history"])
                    st.rerun()
            else:
                c1.write(f"~~{str(row['title']).strip()}~~")
                c1.caption(f"{time_text} | 🎯 Для: {assignee_label}")
                c2.button("⏳", key=f"t_{i}", disabled=True)

        else: # РАЗОВАЯ
           c1.write(f"**{str(row['title']).strip()}** (+{row['reward']} 🪙)")
        c1.caption(f"✍️ От: {creator_label} | 🎯 Для: {assignee_label}")
            
        if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
             db["balances"].loc[0, current_user] += int(row['reward'])
             db["tasks"] = db["tasks"].drop(i)
             new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
            db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
             save_data("balances", db["balances"]); save_data("tasks", db["tasks"]); save_data("history", db["history"])
             st.rerun()
                
# ==========================================
# ЭКРАН: МАРКЕТПЛЕЙС
# ==========================================
elif st.session_state.page == "market":
    st.title("🛒 Маркетплейс")
    
    for j, row in db["market"].iterrows():
        # Те же три колонки: описание, кнопка покупки и корзина
        c1, c2, c3 = st.columns([3, 1, 0.5])
        price = int(row['price'])
        is_my_item = (row['seller'] == current_user)
        can_buy = (not is_my_item) and (my_balance >= price)
        btn_label = "Мой лот" if is_my_item else "Купить"
        
        # Кнопка удаления лота (🗑️)
        if c3.button("🗑️", key=f"del_m_{j}", help="Удалить лот с витрины"):
            db["market"] = db["market"].drop(j)
            save_data("market", db["market"])
            st.rerun()
        
        if c2.button(btn_label, key=f"m_{j}", disabled=not can_buy):
            # Снимаем 🪙, начисляем 💖 партнеру
            db["balances"].loc[0, current_user] -= price
            if row['seller'] != "Оба":
                partner_key = f"{row['seller']}_Рейтинг"
                db["balances"].loc[0, partner_key] += price
            
            new_log = pd.DataFrame([{
                "buyer": current_user, 
                "item": row['title'], 
                "price": price, 
                "seller": row['seller'], 
                "type": "Покупка"
            }])
            db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
            save_data("balances", db["balances"])
            save_data("history", db["history"])
            st.balloons()
            st.rerun()
            
        display_name = f"🎁 **{row['title']}** ({price} 🪙)"
        if is_my_item: 
            display_name += " *(Ваше)*"
        c1.write(display_name)
    
  # --- ДОБАВЛЕНИЕ ЛОТА ---
    with st.expander("🏷️ Выставить лот на продажу"):
        with st.form("new_market_form", clear_on_submit=True):
            m_title = st.text_input("Что продаем?")
            m_price = st.number_input("Цена (🪙)", min_value=1, value=50)
            m_seller = st.selectbox("Продавец", [current_user, "Оба"], format_func=lambda x: DISPLAY.get(x, x))
            
            if st.form_submit_button("Выставить на маркет"):
                if m_title:
                    new_item = {"title": m_title, "price": m_price, "seller": m_seller}
                    db["market"] = pd.concat([db["market"], pd.DataFrame([new_item])], ignore_index=True)
                    save_data("market", db["market"])
                    st.success("Лот добавлен на витрину!")
                    st.rerun()
                else:
                    st.warning("Введи название лота!")
    

# ==========================================
# ЭКРАН 2: ЛИЧНЫЙ КАБИНЕТ
# ==========================================
elif st.session_state.page == "profile":
    st.title("👤 Личный кабинет")
    
    # --- НАСТРОЙКИ ПРОФИЛЯ (СМЕНА НИКА) ---
    with st.expander("⚙️ Настройки профиля"):
        new_name = st.text_input("Мой никнейм", value=DISPLAY[current_user])
        if st.button("Сохранить"):
            col_name = f"{current_user}_Имя"
            
            # Принудительно создаем колонку как текстовую, если её нет
            if col_name not in db["balances"].columns:
                db["balances"][col_name] = ""
            
            # Лечим ошибку Pandas: приводим к строковому типу
            db["balances"][col_name] = db["balances"][col_name].astype(str)
            db["balances"].loc[0, col_name] = new_name
            
            save_data("balances", db["balances"])
            st.success("Ник обновлен! Синхронизирую...")
            sync_database() 
            st.rerun()

    st.markdown("---")

    # --- ОБЩАЯ СТАТИСТИКА ---
    col_info1, col_info2, col_info3 = st.columns(3)
    
    # Считаем доходы от задач
    earned = db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Работа')]['price'].sum()
    # Считаем траты в магазине
    spent = db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Покупка')]['price'].sum()
    
    col_info1.metric("Заработано 🪙", f"{earned}")
    col_info2.metric("Потрачено 🪙", f"{spent}")
    col_info3.metric("Рейтинг 💖", f"{my_rating}")

    st.markdown("---")

    # --- МОИ ЛОТЫ НА ВИТРИНЕ ---
    st.subheader("📦 Мои товары в продаже")
    my_lots = db["market"][db["market"]['seller'] == current_user]
    if not my_lots.empty:
        st.dataframe(my_lots[['title', 'price']], use_container_width=True, hide_index=True)
    else:
        st.write("Вы еще ничего не выставили на продажу.")

    # --- ИСТОРИЯ ПОКУПОК ---
    st.subheader("🛍️ История моих покупок")
    my_buys = db["history"][(db["history"]['buyer'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_buys.empty:
        st.dataframe(my_buys[['item', 'price', 'seller']], use_container_width=True, hide_index=True)
    else:
        st.write("Вы еще ничего не купили.")
    
    # --- МОИ ПРОДАЖИ (РЕЙТИНГ) ---
    st.subheader("💖 За что получен рейтинг")
    my_sales = db["history"][(db["history"]['seller'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_sales.empty:
        display_sales = my_sales[['item', 'price', 'buyer']].copy()
        display_sales = display_sales.rename(columns={'price': 'получено 💖'})
        st.dataframe(display_sales, use_container_width=True, hide_index=True)
    else:
        st.write("Ваши лоты еще не покупали.")
