import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Семейная Монетизация", page_icon="💰", layout="centered")

st.title("💖 Семейная Экономика")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def get_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl=0)

def save_data(sheet_name, df):
    conn.update(worksheet=sheet_name, data=df)

# Читаем данные
try:
    df_balances = get_data("balances")
    df_tasks = get_data("tasks")
    муж_баланс = int(df_balances.loc[0, "Муж"])
    жена_баланс = int(df_balances.loc[0, "Жена"])
except Exception as e:
    st.error("Ошибка загрузки данных! Проверь листы 'balances' и 'tasks'.")
    st.stop()

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
current_user = st.selectbox("Кто у экрана?", ["Муж", "Жена"], key="user_active")

# Вывод списка задач из таблицы
for i, row in df_tasks.iterrows():
    col_task, col_btn = st.columns([3, 1])
    with col_task:
        st.write(f"**{row['title']}** — {row['reward']} 🪙 (Кому: {row['assigned_to']})")
    with col_btn:
        is_my_task = (row['assigned_to'] in [current_user, "Оба"])
        if st.button("Готово!", key=f"task_{i}", disabled=not is_my_task):
            # Обновляем баланс
            if current_user == "Муж":
                df_balances.loc[0, "Муж"] = муж_баланс + int(row['reward'])
            else:
                df_balances.loc[0, "Жена"] = жена_баланс + int(row['reward'])
            
            save_data("balances", df_balances)
            st.success("Монетки начислены!")
            st.rerun()

st.markdown("---")

# --- БЛОК 3: ДОБАВЛЕНИЕ НОВОЙ ЗАДАЧИ ---
with st.expander("➕ Добавить новую задачу"):
    with st.form("new_task_form", clear_on_submit=True):
        new_title = st.text_input("Что нужно сделать?")
        new_reward = st.number_input("Награда (🪙)", min_value=1, value=10)
        new_assignee = st.selectbox("Кто выполняет?", ["Муж", "Жена", "Оба"])
        submit_task = st.form_submit_button("Создать задачу")
        
        if submit_task and new_title:
            # Создаем новую строчку
            new_row = pd.DataFrame([{
                "title": new_title, 
                "reward": new_reward, 
                "assigned_to": new_assignee
            }])
            # Добавляем к текущему списку и сохраняем
            df_tasks = pd.concat([df_tasks, new_row], ignore_index=True)
            save_data("tasks", df_tasks)
            st.success("Задача добавлена в базу!")
            st.rerun()

# Маркетплейс пока оставим как был, или его тоже можно перенести в таблицу по той же логике
