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
if "page" not in st.session_state: st.session_state.page = "main"

if st.session_state.user is None:
    st.title("Кто сегодня молодец? 😎")
    c1, c2 = st.columns(2)
    if c1.button("Я Муж", use_container_width=True): st.session_state.user = "Муж"; st.rerun()
    if c2.button("Я Жена", use_container_width=True): st.session_state.user = "Жена"; st.rerun()
    st.stop()

db = st.session_state.db
current_user = st.session_state.user
my_balance = int(db["balances"].loc[0, current_user])
my_rating = int(db["balances"].loc[0, f"{current_user}_Рейтинг"])

# --- САЙДБАР ---
with st.sidebar:
    st.title(f"{current_user}")
    st.metric("Кошелек", f"{my_balance} 🪙")
    st.metric("Рейтинг", f"{my_rating} 💖")
    if st.button("🔄 Синхронизировать", use_container_width=True): sync_database(); st.rerun()
    if st.button("🏠 Главная"): st.session_state.page = "main"; st.rerun()
    if st.button("👤 Кабинет"): st.session_state.page = "profile"; st.rerun()

# ==========================================
# ГЛАВНАЯ СТРАНИЦА
# ==========================================
if st.session_state.page == "main":
    st.title("📋 Твои задачи")
    
    now = datetime.now()

    for i, row in db["tasks"].iterrows():
        t_type = row.get('task_type', 'Разовая')
        is_my = row['assigned_to'] in [current_user, "Оба"]
        
        c1, c2 = st.columns([3, 1])
        
        if t_type == "Интервальная":
            last_done_str = str(row.get('last_completed', ''))
            val = int(row.get('interval_value', 0))
            unit = row.get('interval_unit', 'Часы')
            
            can_do = True
            time_text = ""
            
            if last_done_str:
                last_done_dt = datetime.strptime(last_done_str, '%Y-%m-%d %H:%M:%S')
                # Считаем кулдаун в зависимости от единиц
                if unit == "Часы":
                    next_available = last_done_dt + timedelta(hours=val)
                else: # Дни
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
            
            if can_do:
                c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")
                if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
                    db["balances"].loc[0, current_user] += int(row['reward'])
                    db["tasks"].at[i, 'last_completed'] = now.strftime('%Y-%m-%d %H:%M:%S')
                    new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
                    db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                    
                    save_data("balances", db["balances"])
                    save_data("tasks", db["tasks"])
                    save_data("history", db["history"])
                    st.rerun()
            else:
                c1.write(f"~~{row['title']}~~")
                c1.caption(time_text)
                c2.button("⏳", key=f"t_{i}", disabled=True)

        else: # РАЗОВАЯ
            c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")
            if c2.button("Готово!", key=f"t_{i}", disabled=not is_my):
                db["balances"].loc[0, current_user] += int(row['reward'])
                db["tasks"] = db["tasks"].drop(i)
                new_log = pd.DataFrame([{"buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
                db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                save_data("balances", db["balances"])
                save_data("tasks", db["tasks"])
                save_data("history", db["history"])
                st.rerun()

    # --- ФОРМА СОЗДАНИЯ ---
    with st.expander("➕ Добавить задачу"):
        with st.form("new_task_form", clear_on_submit=True):
            title = st.text_input("Что сделать?")
            reward = st.number_input("Награда", min_value=1, value=10)
            assignee = st.selectbox("Кто?", ["Муж", "Жена", "Оба"])
            t_type = st.radio("Режим", ["Разовая", "Интервальная"])
            
            c_val, c_unit = st.columns(2)
            val = c_val.number_input("Интервал", min_value=1, value=12)
            unit = c_unit.selectbox("Единица", ["Часы", "Дни"])
            
            if st.form_submit_button("Создать"):
                new_data = {
                    "title": title, "reward": reward, "assigned_to": assignee,
                    "task_type": t_type, 
                    "interval_value": val if t_type == "Интервальная" else 0,
                    "interval_unit": unit if t_type == "Интервальная" else "",
                    "last_completed": ""
                }
                db["tasks"] = pd.concat([db["tasks"], pd.DataFrame([new_data])], ignore_index=True)
                save_data("tasks", db["tasks"])
                st.rerun()
