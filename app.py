import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

def send_telegram(text, target="Оба"):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        # Используем те же ключи, что в selectbox
        ids = {
            "Муж": [st.secrets["MY_CHAT_ID"]],
            "Жена": [st.secrets["WIFE_CHAT_ID"]],
            "Оба": [st.secrets["MY_CHAT_ID"], st.secrets["WIFE_CHAT_ID"]]
        }
        
        target_ids = ids.get(target, [])
        for chat_id in target_ids:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {"chat_id": chat_id, "text": text}
            response = requests.get(url, params=params)
            
            if not response.ok:
                st.error(f"❌ Ошибка ТГ для ID {chat_id}: {response.text}")
            else:
                st.toast(f"✅ Уведомление отправлено на ID {chat_id}")
                
    except Exception as e:
        st.error(f"💥 Критическая ошибка функции: {e}")
#-----Уровни--------
def get_level_data(xp):
    level = 1
    next_level_step = 100 # Сколько нужно опыта для перехода с 1 на 2
    total_needed = 100    # Порог для достижения 2 уровня
    
    while xp >= total_needed:
        level += 1
        next_level_step = int(next_level_step * 1.3)
        total_needed += next_level_step
    
    # Расчет прогресса внутри уровня
    current_level_start = total_needed - next_level_step
    xp_in_level = xp - current_level_start
    return level, xp_in_level, next_level_step

# Словарь для будущих статусов (пока просто заглушка)
LEVEL_TITLES = {
    1: "Даня",
    2: "Рифеншталь",
    3: "Алинка",
    4: "Стажер клининга",
    5: "Дед",
    6: "Легендарный уборщик",
    7: "Зачетный колдун-клинер",
    8: "Бог дома",
    9: "Домашний властелин",
    10: "Домовой",
    15: "Генерал домашних войск",
    17: "Магистр Клининг",
    20: "Злая Алинка"
}
# ---  НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Семейная Экономика", page_icon="💰", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name): return conn.read(worksheet=sheet_name, ttl=0)
def save_data(sheet_name, df): conn.update(worksheet=sheet_name, data=df)

def sync_database():
    st.session_state.db = {
        "balances": get_data("balances"),
        "tasks": get_data("tasks"),
        "market": get_data("market"),
        "history": get_data("history"),
        "templates": get_data("templates"),
        "reports": get_data("reports"),
        "achievements": get_data("achievements")
    }

if "db" not in st.session_state: sync_database()
if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "tasks"

# --- ПОДГОТОВКА ДАННЫХ ИЗ КЭША ---
db = st.session_state.db 

h_name = db["balances"].loc[0, "Муж_Имя"] if "Муж_Имя" in db["balances"].columns else "Муж"
w_name = db["balances"].loc[0, "Жена_Имя"] if "Жена_Имя" in db["balances"].columns else "Жена"

DISPLAY = {"Муж": h_name, "Жена": w_name, "Оба": "Оба"}

# --- ЭКРАН ВЫБОРА ПРОФИЛЯ ---
if st.session_state.user is None:
    st.title("Кто сегодня молодец? 😎")
    c1, c2 = st.columns(2)
    if c1.button(f"Я {DISPLAY['Муж']}", use_container_width=True): 
        st.session_state.user = "Муж"
        st.rerun()
    if c2.button(f"Я {DISPLAY['Жена']}", use_container_width=True): 
        st.session_state.user = "Жена"
        st.rerun()
    st.stop()

current_user = st.session_state.user
my_balance = int(db["balances"].loc[0, current_user])
my_rating = int(db["balances"].loc[0, f"{current_user}_Рейтинг"])
now = datetime.now()

# --- СТАНДАРТНЫЙ САЙДБАР ---
with st.sidebar:
    st.title(f"{DISPLAY[current_user]}")
    st.metric("Кошелек", f"{my_balance} 🪙")
    
    # 🔥 СИСТЕМА УРОВНЕЙ
    lvl, xp_current, xp_needed = get_level_data(my_rating)
    title = LEVEL_TITLES.get(lvl, "Герой")
    
    st.markdown(f"### Уровень {lvl}: **{title}**")
    # Прогресс-бар
    progress = xp_current / xp_needed
    st.progress(progress)
    st.caption(f"Опыт: {xp_current} / {xp_needed} (Всего: {my_rating} 💖)")
    
    st.markdown("---")
    
    # Навигация
    if st.button("📋 Список задач", use_container_width=True):
        st.session_state.page = "tasks"
        st.rerun()
            
    if st.button("🛒 Маркетплейс", use_container_width=True):
        st.session_state.page = "market"
        st.rerun()
            
    if st.button("👤 Личный кабинет", use_container_width=True):
        st.session_state.page = "profile"
        st.rerun()
        
    st.markdown("---")
    if st.button("🔄 Синхронизировать", use_container_width=True): 
        sync_database()
        st.rerun()
        
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.user = None
        st.rerun()
        
# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ЗАДАЧИ)
# ==========================================
if st.session_state.page == "tasks":
    st.title("✅ Задачи")

    # --- БЛОК ДОБАВЛЕНИЯ ЗАДАЧИ ---
    with st.expander("➕ Добавить новую задачу"):
        template_df = db.get("templates", pd.DataFrame(columns=["title", "reward"]))
        template_options = ["Без шаблона (Свой вариант)"]
        if not template_df.empty:
            for idx, t_row in template_df.iterrows():
                template_options.append(f"{t_row['title']} ({t_row['reward']} 🪙)")
                
        selected_template = st.selectbox("Выбрать из готовых шаблонов", template_options)
        
        default_title = ""
        default_reward = 10
        if selected_template != "Без шаблона (Свой вариант)":
            sel_idx = template_options.index(selected_template) - 1
            default_title = str(template_df.iloc[sel_idx]['title'])
            default_reward = int(template_df.iloc[sel_idx]['reward'])
            
        title = st.text_input("Что сделать?", value=default_title, key=f"title_input_{selected_template}")
        reward = st.number_input("Награда (🪙)", min_value=1, value=default_reward)
        task_comment = st.text_area("Комментарий / Уточнения (необязательно)")
        assignee = st.selectbox("Кто выполняет?", ["Муж", "Жена", "Оба"], format_func=lambda x: DISPLAY.get(x, x))
        t_type = st.radio("Режим задачи", ["Разовая", "Интервальная"])
        
        val, unit = 0, ""
        if t_type == "Интервальная":
            c_val, c_unit = st.columns(2)
            val = c_val.number_input("Интервал повтора", min_value=1, value=12)
            unit = c_unit.selectbox("Единица времени", ["Часы", "Дни"])
            
        if st.button("Создать задачу и выставить на доску", use_container_width=True):
            clean_title = title.strip()
            if not clean_title:
                st.warning("Напиши название задачи!")
            else:
                new_task = {
                    "title": clean_title,
                    "reward": reward,
                    "comment": task_comment.strip(),
                    "assigned_to": assignee,
                    "task_type": t_type,
                    "interval_value": val,
                    "interval_unit": unit,
                    "last_completed": "",
                    "created_by": current_user
                }
                db["tasks"] = pd.concat([db["tasks"], pd.DataFrame([new_task])], ignore_index=True)
                save_data("tasks", db["tasks"])
                
                # Уведомление ПЕРЕД рераном
                t_label = DISPLAY.get(assignee, assignee)
                send_telegram(f"🔔 Новая задача: {clean_title} ({reward} 🪙) для {t_label}!", target=assignee)
                
                st.success(f"Задача '{clean_title}' добавлена!")
                st.rerun()

    # --- НАСТРОЙКА ШАБЛОНОВ ---
    with st.expander("✨ Настройка шаблонов (Управление ценами)"):
        with st.form("new_template_form", clear_on_submit=True):
            tpl_title = st.text_input("Название шаблона")
            tpl_reward = st.number_input("Фиксированная награда (🪙)", min_value=1, value=5)
            if st.form_submit_button("Сохранить этот шаблон"):
                if tpl_title.strip():
                    new_tpl = {"title": tpl_title.strip(), "reward": int(tpl_reward)}
                    db["templates"] = pd.concat([db["templates"], pd.DataFrame([new_tpl])], ignore_index=True)
                    save_data("templates", db["templates"])
                    st.success("Шаблон сохранен!")
                    st.rerun()

    st.markdown("---")

    # --- ПАНЕЛЬ ФИЛЬТРОВ ---
    st.subheader("🔍 Фильтры")
    cf1, cf2, cf3 = st.columns(3)
    f_assignee = cf1.selectbox("Для кого?", ["Все", "Муж", "Жена", "Оба"], format_func=lambda x: DISPLAY.get(x, x))
    f_type = cf2.selectbox("Тип задачи", ["Все", "Разовые", "Интервальные"])
    f_sort = cf3.selectbox("Сортировка", ["По умолчанию", "Дорогие", "Дешевые"])

    # Готовим данные для фильтрации
    df_f = db["tasks"].copy()

    # Умный фильтр по исполнителю
    if f_assignee != "Все":
        if f_assignee in ["Муж", "Жена"]:
            df_f = df_f[df_f["assigned_to"].isin([f_assignee, "Оба"])]
        else:
            df_f = df_f[df_f["assigned_to"] == "Оба"]

    # Фильтр по типу
    if f_type != "Все":
        df_f = df_f[df_f["task_type"] == ("Разовая" if f_type == "Разовые" else "Интервальная")]

    # Сортировка по награде
    if f_sort == "Дорогие":
        df_f = df_f.sort_values(by="reward", ascending=False)
    elif f_sort == "Дешевые":
        df_f = df_f.sort_values(by="reward", ascending=True)

    # СБРАСЫВАЕМ ИНДЕКСЫ (Критически важно для работы цикла!)
    df_f = df_f.reset_index(drop=True)

    # Предварительный расчет доступности для сортировки "Сначала готовые"
    final_list = []
    for idx, row in df_f.iterrows():
        can_do = True
        if row['task_type'] == "Интервальная":
            raw_last = row.get('last_completed')
            if pd.notna(raw_last) and str(raw_last).strip() not in ["", "nan"]:
                try:
                    last_dt = pd.to_datetime(str(raw_last)).tz_localize(None)
                    delta = timedelta(hours=int(row['interval_value'])) if row['interval_unit'] == "Часы" else timedelta(days=int(row['interval_value']))
                    if now < (last_dt + delta):
                        can_do = False
                except: pass
        final_list.append({"row": row, "available": can_do, "orig_idx": idx})

    # Сортировка: доступные вперед
    final_list = sorted(final_list, key=lambda x: x['available'], reverse=True)

    # --- ОТРИСОВКА КАРТОЧЕК ---
    if not final_list:
        st.info("Задач нет. Попробуй изменить фильтры!")
    else:
        for item in final_list:
            row = item["row"]
            idx = item["orig_idx"]
            can_do = item["available"]
            is_my = row['assigned_to'] in [current_user, "Оба"]
            
            # Рендерим карточку
            with st.container(border=True):
                c1, c2 = st.columns([5, 0.5])
                c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")
                if c2.button("🗑️", key=f"del_{idx}"):
                    # Удаляем из ОСНОВНОЙ базы по индексу, который мы нашли через title (самый безопасный способ здесь)
                    db["tasks"] = db["tasks"][db["tasks"]["title"] != row["title"]]
                    save_data("tasks", db["tasks"])
                    st.rerun()

                if row.get('comment'): st.caption(f"💬 {row['comment']}")
                
                label_to = DISPLAY.get(row['assigned_to'], row['assigned_to'])
                label_from = DISPLAY.get(row.get('created_by', 'Система'), row.get('created_by', 'Система'))
                st.caption(f"✍️ {label_from} ➔ 🎯 {label_to}")

                btn_c, status_c = st.columns([1, 1])
                
                if row['task_type'] == "Интервальная" and not can_do:
                    # Считаем время до конца кулдауна
                    last_dt = pd.to_datetime(str(row['last_completed'])).tz_localize(None)
                    delta = timedelta(hours=int(row['interval_value'])) if row['interval_unit'] == "Часы" else timedelta(days=int(row['interval_value']))
                    diff = (last_dt + delta) - now
                    h, rem = divmod(diff.seconds, 3600)
                    m, _ = divmod(rem, 60)
                    status_c.write(f"⏳ {diff.days}д {h}ч {m}м")
                    btn_c.button("⏳", key=f"wait_{idx}", disabled=True, use_container_width=True)
                else:
                    if btn_c.button("✅ Готово!", key=f"done_{idx}", disabled=not is_my, use_container_width=True):
                        # Начисляем
                        db["balances"].loc[0, current_user] += int(row['reward'])
                        db["balances"].loc[0, f"{current_user}_Рейтинг"] += 10
                        
                        # Логируем
                        current_time = now.strftime("%d.%m.%Y %H:%M")
                        new_log = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": row['title'], "price": row['reward'], "seller": "Система", "type": "Работа"}])
                        db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                        
                        if row['task_type'] == "Интервальная":
                            # Находим задачу в основной базе по заголовку и обновляем время
                            db["tasks"].loc[db["tasks"]["title"] == row["title"], "last_completed"] = now.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            # Удаляем разовую
                            db["tasks"] = db["tasks"][db["tasks"]["title"] != row["title"]]
                        
                        save_data("balances", db["balances"]); save_data("tasks", db["tasks"]); save_data("history", db["history"])
                        st.rerun()
                
# ==========================================
# ЭКРАН: МАРКЕТПЛЕЙС
# ==========================================
elif st.session_state.page == "market":
    st.title("🛒 Маркетплейс")

    for j, row in db["market"].iterrows():
        # Подготовка данных лота
        l_type = row.get('type', 'Индивидуальный')
        price = int(row['price'])
        collected = int(row.get('collected', 0)) if pd.notna(row.get('collected')) else 0
        contribs = str(row.get('contributions', ''))
        
        c1, c2, c3 = st.columns([3, 1.2, 0.5])
        
        # Кнопка удаления (оставляем)
        if c3.button("🗑️", key=f"del_m_{j}"):
            db["market"] = db["market"].drop(j)
            save_data("market", db["market"])
            st.rerun()

        if l_type == "Общий":
            # --- ЛОГИКА ОБЩЕГО ЛОТА ---
            progress = min(collected / price, 1.0)
            c1.write(f"🤝 **{row['title']}**")
            c1.progress(progress)
            c1.caption(f"Накоплено: **{collected}** из **{price}** 🪙")
            
            # Показываем, кто сколько внес (мелким шрифтом)
            if contribs and contribs != "nan":
                c1.markdown(f"<p style='font-size: 11px; color: gray;'>Вклады: {contribs}</p>", unsafe_allow_html=True)
            
            if collected < price:
                # Поле для ввода суммы вклада
                donate_amount = c2.number_input("Сумма", min_value=1, max_value=max(1, price - collected), value=min(10, price - collected), key=f"don_val_{j}")
                if c2.button("Скинуться", key=f"don_btn_{j}", disabled=(my_balance < donate_amount)):
                    # Обновляем баланс
                    db["balances"].loc[0, current_user] -= donate_amount
                    # Обновляем прогресс лота
                    db["market"].at[j, 'collected'] = collected + donate_amount
                    
                    # Обновляем историю вкладов (строка формата "Имя: 10, Имя: 20")
                    user_label = DISPLAY[current_user]
                    new_contrib = f"{user_label}: {donate_amount}"
                    old_contribs = contribs if (contribs and contribs != "nan") else ""
                    db["market"].at[j, 'contributions'] = f"{old_contribs}, {new_contrib}".strip(", ")
                    
                    # Логируем в историю
                    current_time = now.strftime("%d.%m.%Y %H:%M")
                    new_log = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": f"Вклад в: {row['title']}", "price": donate_amount, "seller": "Общак", "type": "Покупка"}])
                    db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                    
                    save_data("balances", db["balances"]); save_data("market", db["market"]); save_data("history", db["history"])
                    st.rerun()
            else:
                c2.success("Цель достигнута! 🎉")
                if c2.button("Закрыть цель", key=f"close_target_{j}"):
                    db["market"] = db["market"].drop(j)
                    save_data("market", db["market"])
                    st.rerun()

        else:
            # --- ЛОГИКА ИНДИВИДУАЛЬНОГО ЛОТА ---
            is_my_item = (row['seller'] == current_user)
            can_buy = (not is_my_item) and (my_balance >= price)
            btn_label = "Мой лот" if is_my_item else f"Купить"
            
            c1.write(f"🎁 **{row['title']}** ({price} 🪙)")
            if is_my_item: c1.caption("*(Ваше на витрине)*")
            
            if c2.button(btn_label, key=f"m_{j}", disabled=not can_buy):
                db["balances"].loc[0, current_user] -= price
                if row['seller'] != "Оба":
                    partner_key = f"{row['seller']}_Рейтинг"
                    db["balances"].loc[0, partner_key] += price
                
                current_time = now.strftime("%d.%m.%Y %H:%M")
                new_log = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": row['title'], "price": price, "seller": row['seller'], "type": "Покупка"}])
                db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
                save_data("balances", db["balances"]); save_data("history", db["history"])
                st.balloons()
                st.rerun()
    
    with st.expander("🏷️ Выставить лот на продажу"):
       with st.form("new_market_form", clear_on_submit=True):
            m_title = st.text_input("Что продаем / На что копим?")
            m_price = st.number_input("Цена или Цель (🪙)", min_value=1, value=50)
            m_type = st.selectbox("Тип лота", ["Индивидуальный", "Общий"])
            m_seller = st.selectbox("Кто предоставляет?", [current_user, "Оба"], format_func=lambda x: DISPLAY.get(x, x))
            
            if st.form_submit_button("Выставить на маркет"):
                if m_title:
                    new_item = {
                        "title": m_title, 
                        "price": m_price, 
                        "seller": m_seller, 
                        "type": m_type,
                        "collected": 0,
                        "contributions": ""
                    }
                    db["market"] = pd.concat([db["market"], pd.DataFrame([new_item])], ignore_index=True)
                    
                    # Логируем создание
                    current_time = now.strftime("%d.%m.%Y %H:%M")
                    log_type = "Цель" if m_type == "Общий" else "Лот"
                    log_lot = pd.DataFrame([{"date": current_time, "buyer": m_seller, "item": f"Новая {log_type}: {m_title}", "price": 0, "seller": "Система", "type": "Инфраструктура"}])
                    db["history"] = pd.concat([db["history"], log_lot], ignore_index=True)
                    
                    save_data("market", db["market"])
                    save_data("history", db["history"])
                    st.success(f"{m_type} лот добавлен!")
                    st.rerun()
    
# ==========================================
# ЭКРАН 3: ЛИЧНЫЙ КАБИНЕТ
# ==========================================
elif st.session_state.page == "profile":
    st.title("👤 Личный кабинет")
    
    with st.expander("⚙️ Настройки профиля"):
        new_name = st.text_input("Мой никнейм", value=DISPLAY[current_user])
        if st.button("Сохранить"):
            col_name = f"{current_user}_Имя"
            if col_name not in db["balances"].columns:
                db["balances"][col_name] = ""
            db["balances"][col_name] = db["balances"][col_name].astype(str)
            db["balances"].loc[0, col_name] = new_name
            save_data("balances", db["balances"])
            st.success("Ник обновлен! Синхронизирую...")
            sync_database() 
            st.rerun()

    st.markdown("---")

    col_info1, col_info2, col_info3 = st.columns(3)
    earned = db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Работа')]['price'].sum()
    spent = db['history'][(db['history']['buyer'] == current_user) & (db['history']['type'] == 'Покупка')]['price'].sum()
    
    col_info1.metric("Заработано 🪙", f"{earned}")
    col_info2.metric("Потрачено 🪙", f"{spent}")
    col_info3.metric("Рейтинг 💖", f"{my_rating}")

    # ==========================================
    # ВЕЧНАЯ СИСТЕМА ДОСТИЖЕНИЙ
    # ==========================================
    st.markdown("---")
    st.subheader("🥇 Мои достижения")
    
    # Загружаем несгораемую базу ачивок
    ach_db = db.get("achievements", pd.DataFrame(columns=["user", "achievement"]))
    if ach_db.empty or "user" not in ach_db.columns:
        ach_db = pd.DataFrame(columns=["user", "achievement"])
        
    # Список того, что юзер уже открыл намертво
    my_forever_achievements = ach_db[ach_db["user"] == current_user]["achievement"].tolist()

    # Сбор сырых данных для проверки текущих условий
    hist_df = db.get("history", pd.DataFrame())
    tasks_df = db.get("tasks", pd.DataFrame())
    templates_df = db.get("templates", pd.DataFrame())
    market_df = db.get("market", pd.DataFrame())

    # Проверка условий (срабатывает, только если ачивка еще не была записана в вечный список)
    has_comment = "scrupulous" in my_forever_achievements
    if not has_comment and "comment" in tasks_df.columns and "created_by" in tasks_df.columns:
        has_comment = tasks_df[(tasks_df["created_by"] == current_user) & (tasks_df["comment"].astype(str).str.strip() != "") & (tasks_df["comment"].astype(str).str.lower() != "nan")].shape[0] > 0

    boss_unlocked = "boss" in my_forever_achievements
    if not boss_unlocked and "created_by" in tasks_df.columns and "assigned_to" in tasks_df.columns:
        boss_unlocked = tasks_df[(tasks_df["created_by"] == current_user) & (tasks_df["assigned_to"] != current_user)].shape[0] >= 5

    templates_unlocked = "templates" in my_forever_achievements
    if not templates_unlocked:
        templates_unlocked = (templates_df.shape[0] >= 7) if not templates_df.empty else False

    bazar_unlocked = "bazar" in my_forever_achievements
    if not bazar_unlocked:
        history_lots = hist_df[(hist_df["type"] == "Новый лот") & (hist_df["buyer"] == current_user)].shape[0] if not hist_df.empty else 0
        current_lots = market_df[market_df["seller"] == current_user].shape[0] if not market_df.empty else 0
        bazar_unlocked = (history_lots + current_lots) >= 3

    stakhanov_unlocked = "stakhanov" in my_forever_achievements
    if not stakhanov_unlocked:
        stakhanov_unlocked = (hist_df[(hist_df["type"] == "Работа") & (hist_df["buyer"] == current_user)].shape[0] >= 10) if not hist_df.empty else False

    teamwork_unlocked = "teamwork" in my_forever_achievements
    if not teamwork_unlocked:
        # Проверяем, есть ли в маркете или в истории создания лотов запись, где продавец — "Оба"
        has_joint_lot = market_df[market_df["seller"] == "Оба"].shape[0] > 0 if not market_df.empty else False
        teamwork_unlocked = has_joint_lot

    consumer_unlocked = "consumer" in my_forever_achievements
    if not consumer_unlocked:
        consumer_unlocked = (hist_df[(hist_df["type"] == "Покупка") & (hist_df["buyer"] == current_user)].shape[0] >= 1) if not hist_df.empty else False

    habit_unlocked = "habit" in my_forever_achievements
    if not habit_unlocked:
        if not hist_df.empty:
            # Считаем количество выполнений для каждой задачи (тип "Работа")
            work_history = hist_df[(hist_df["type"] == "Работа") & (hist_df["buyer"] == current_user)]
            if not work_history.empty:
                # Группируем по названию задачи и смотрим максимальное количество
                max_repeats = work_history["item"].value_counts().max()
                habit_unlocked = max_repeats >= 10
            else:
                habit_unlocked = False
        else:
            habit_unlocked = False

    # Массив для фиксации новых открытий прямо сейчас
    newly_unlocked = []
    
    # Проверяем и дописываем новые выполнения в базу данных
    conditions = {
        "scrupulous": has_comment,
        "boss": boss_unlocked,
        "templates": templates_unlocked,
        "bazar": bazar_unlocked,
        "stakhanov": stakhanov_unlocked,
        "teamwork": teamwork_unlocked,  
        "consumer": consumer_unlocked,  
        "habit": habit_unlocked         
    }
    
    for ach_id, is_met in conditions.items():
        if is_met and ach_id not in my_forever_achievements:
            newly_unlocked.append({"user": current_user, "achievement": ach_id})
            my_forever_achievements.append(ach_id) # Добавляем в локальный список для отрисовки

    if newly_unlocked:
        db["achievements"] = pd.concat([ach_db, pd.DataFrame(newly_unlocked)], ignore_index=True)
        save_data("achievements", db["achievements"])
        st.toast("🎉 Открыто новое достижение! Загляни в Личный Кабинет.")

    # Словарь красивого вывода
    ACH_INFO = {
        "scrupulous": {"title": "🧐 Скрупулёзный", "desc": "Первый комментарий к заданию успешно оставлен! 🎉"},
        "boss": {"title": "👑 Босс", "desc": "Поручено не менее 5 заданий на доске! Настоящий руководитель."},
        "templates": {"title": "🧩 Шаблонное мышление", "desc": "Создано не менее 7 шаблонов задач. Стандартизация рулит!"},
        "bazar": {"title": "🛍️ Баба базарная", "desc": "Выставлено не менее 3 лотов на продажу. Бизнес процветает!"},
        "stakhanov": {"title": "🚜 Стахановец", "desc": "Выполнено не менее 10 задач за период. Гордость семьи!"},
        "teamwork": {"title": "🤝 Командная работа", "desc": "Создан общий лот 'для двоих'. Один за всех и все за одного!"},
        "consumer": {"title": "🍪 Потребитель", "desc": "Первая покупка на маркете совершена. С почином!"},
        "habit": {"title": "🔁 Дело привычки", "desc": "Вы заставили рутину работать на себя! Задача выполнена 10 раз."}
    }

    # Отрисовка по новым правилам
    col_ach1, col_ach2 = st.columns(2)
    keys = list(ACH_INFO.keys())
    
    for idx, key in enumerate(keys):
        target_col = col_ach1 if idx % 2 == 0 else col_ach2
        info = ACH_INFO[key]
        
        if key in my_forever_achievements:
            # Открытая ачивка — полноценная красивая карточка
            target_col.success(f"**{info['title']}**\n\n{info['desc']}")
        else:
            # Закрытая ачивка — темно-серая скромная строчка без спойлеров
            target_col.markdown(f"<p style='color: #777777; font-size: 16px; margin-bottom: 18px; font-weight: bold;'>🔒 {info['title']} — <span style='font-style: italic; font-weight: normal;'>Еще не открыто</span></p>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- БЛОК: ОТЧЕТЫ И ЗАКРЫТИЕ МЕСЯЦА ---
    st.subheader("📊 Итоги месяцев")
    
    with st.expander("🧹 Закрыть текущий период (Сформировать отчет)"):
        st.warning("Внимание! Это соберет текущую историю, сделает вам ЛИЧНЫЕ текстовые отчеты и полностью очистит базу истории. Вечные ачивки при этом НЕ пострадают.")
        if st.button("Сформировать отчет и очистить историю", use_container_width=True):
            hist = db["history"]
            if hist.empty:
                st.error("История пуста, подводить итоги пока рано!")
            else:
                new_reports = []
                for u in ["Муж", "Жена"]:
                    tasks_done = len(hist[(hist["type"] == "Работа") & (hist["buyer"] == u)])
                    lots_listed = len(hist[(hist["type"] == "Новый лот") & ((hist["buyer"] == u) | (hist["buyer"] == "Оба"))])
                    lots_bought = len(hist[(hist["type"] == "Покупка") & (hist["buyer"] == u)])
                    lots_sold = len(hist[(hist["type"] == "Покупка") & ((hist["seller"] == u) | (hist["seller"] == "Оба"))])
                    
                    coins_earned = hist[(hist["type"] == "Работа") & (hist["buyer"] == u)]["price"].sum()
                    coins_spent = hist[(hist["type"] == "Покупка") & (hist["buyer"] == u)]["price"].sum()
                    rating_earned = hist[(hist["type"] == "Покупка") & (hist["seller"] == u)]["price"].sum()
                    
                    report_text = (
                        f"✅ Задач выполнено: {tasks_done} \n"
                        f"📦 Лотов выставлено: {lots_listed} \n"
                        f"🛍️ Лотов куплено: {lots_bought} \n"
                        f"🤝 Лотов продано: {lots_sold} \n"
                        f"🪙 Монет заработано: {coins_earned} \n"
                        f"💸 Монет потрачено: {coins_spent} \n"
                        f"💖 Рейтинга получено: {rating_earned}"
                    )
                    
                    new_reports.append({"month": now.strftime("%m.%Y"), "user": u, "report_text": report_text})
                
                db["reports"] = pd.concat([db.get("reports", pd.DataFrame(columns=["month", "user", "report_text"])), pd.DataFrame(new_reports)], ignore_index=True)
                db["history"] = pd.DataFrame(columns=hist.columns)
                
                save_data("reports", db["reports"])
                save_data("history", db["history"])
                st.success("Отчеты для каждого сформированы, а история очищена!")
                st.rerun()

    rep_df = db.get("reports", pd.DataFrame())
    if not rep_df.empty:
        if "user" not in rep_df.columns:
            rep_df["user"] = "Общий"
        my_reports = rep_df[(rep_df["user"] == current_user) | (rep_df["user"] == "Общий")]
        if not my_reports.empty:
            for idx, r in my_reports.iterrows():
                st.info(f"**Твой отчет за {r.get('month', 'Неизвестно')}**\n\n{r.get('report_text', '')}")
        else:
            st.write("Твоих сохраненных отчетов пока нет.")
    else:
        st.write("Сохраненных отчетов пока нет.")
        
    st.markdown("---")

    st.subheader("📦 Мои товары в продаже")
    my_lots = db["market"][db["market"]['seller'] == current_user]
    if not my_lots.empty:
        st.dataframe(my_lots[['title', 'price']], use_container_width=True, hide_index=True)
    else:
        st.write("Вы еще ничего не выставили на продажу.")

    st.subheader("🛍️ История моих покупок")
    my_buys = db["history"][(db["history"]['buyer'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_buys.empty:
        if 'date' in my_buys.columns:
            st.dataframe(my_buys[['date', 'item', 'price', 'seller']], use_container_width=True, hide_index=True)
        else:
            st.dataframe(my_buys[['item', 'price', 'seller']], use_container_width=True, hide_index=True)
    else:
        st.write("Пока пусто.")
    
    st.subheader("💖 За что получен рейтинг")
    my_sales = db["history"][(db["history"]['seller'] == current_user) & (db["history"]['type'] == 'Покупка')]
    if not my_sales.empty:
        if 'date' in my_sales.columns:
            display_sales = my_sales[['date', 'item', 'price', 'buyer']].copy()
        else:
            display_sales = my_sales[['item', 'price', 'buyer']].copy()
        display_sales = display_sales.rename(columns={'price': 'получено 💖'})
        st.dataframe(display_sales, use_container_width=True, hide_index=True)
    else:
        st.write("Пока пусто.")

    st.markdown("---")
    st.subheader("✅ Выполненные задачи")
    my_tasks = db["history"][(db["history"]['buyer'] == current_user) & (db["history"]['type'] == 'Работа')]
    if not my_tasks.empty:
        if 'date' in my_tasks.columns:
            display_tasks = my_tasks[['date', 'item', 'price']].copy()
            display_tasks = display_tasks.rename(columns={'date': 'Когда', 'item': 'Что было сделано', 'price': 'Заработано 🪙'})
        else:
            display_tasks = my_tasks[['item', 'price']].copy()
            display_tasks = display_tasks.rename(columns={'item': 'Что было сделано', 'price': 'Заработано 🪙'})
        st.dataframe(display_tasks, use_container_width=True, hide_index=True)
    else:
        st.write("Пока пусто.")
