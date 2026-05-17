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
    total_needed = 100 # Порог для достижения 2 уровня
    
    while xp >= total_needed:
        level += 1
        next_level_step = int(next_level_step * 1.3)
        total_needed += next_level_step
    
    # Расчет прогресса внутри уровня
    current_level_start = total_needed - next_level_step
    current_xp = xp - current_level_start
    
    # 1. Высчитываем прогресс (от 0.0 до 1.0) для виджета st.progress
    progress = current_xp / next_level_step
    # Страховка, чтобы прогресс случайно не вышел за рамки (Streamlit этого не любит)
    progress = max(0.0, min(progress, 1.0))
    
    # 2. Достаем титул из словаря
    # .get() хорош тем, что если ключа нет (например, 11 уровень), он не выдаст ошибку, а подставит дефолт
    lvl_title = LEVEL_TITLES.get(level, "Безымянный герой")
    
    # Теперь возвращаем ровно 5 переменных, как ты и просишь на 210 строке
    return level, progress, current_xp, next_level_step, lvl_title

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

# --- НОВАЯ СИСТЕМА ЗАГРУЗКИ ПО ЭКРАНАМ ---
if "db" not in st.session_state:
 st.session_state.db = {}

def load_sheets(*sheet_names):
 """Подгружает нужные листы, если их еще нет в памяти"""
 for sheet in sheet_names:
  if sheet not in st.session_state.db:
   with st.spinner(f"Загрузка: {sheet}..."):
    st.session_state.db[sheet] = get_data(sheet)

def sync_database():
 """Сбрасывает локальную память, чтобы скачать всё заново"""
 st.session_state.db = {}
 st.rerun()

if "user" not in st.session_state: st.session_state.user = None
if "page" not in st.session_state: st.session_state.page = "tasks"

# 1. Сначала грузим ТОЛЬКО балансы (это нужно для входа и сайдбара)
load_sheets("balances")
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

# ==========================================
# ГЛОБАЛЬНЫЙ ПРОСЧЕТ УВЕДОМЛЕНИЙ
# ==========================================
load_sheets("tasks", "market", "achievements")

if "seen_notifications" not in st.session_state:
 st.session_state.seen_notifications = set()

active_notifications = []

# 1. Достижения
if "achievements" in db and not db["achievements"].empty:
 my_achs = db["achievements"][db["achievements"]['user'] == current_user]
 if not my_achs.empty:
  ach_names = {
   "scrupulous": "Скрупулезный 🧹",
   "bazar": "Базарный магнат 🛍️",
   "boss": "Босс качалки 💪",
   "templates": "Шаблонное мышление",
   "teamwork": "Командная работа",
   "consumer": "🍪 Потребитель",
   "habit": "🔁 Дело привычки"
  }
  for _, ach in my_achs.tail(3).iterrows():
   raw_ach = ach['achievement']
   display_ach = ach_names.get(raw_ach, raw_ach)
   active_notifications.append({
    "id": f"ach_{raw_ach}", "type": "success",
    "text": f"🏆 **Получено достижение:** {display_ach}"
   })

# 2. Порученные задания
if "tasks" in db and not db["tasks"].empty:
 assigned_tasks = db["tasks"][
  (db["tasks"]["created_by"] != current_user) & 
  (db["tasks"]["created_by"] != "Система") &
  (db["tasks"]["assigned_to"].isin([current_user, "Оба"]))
 ]
 for _, row in assigned_tasks.iterrows():
  creator = DISPLAY.get(row['created_by'], row['created_by'])
  active_notifications.append({
   "id": f"task_{row['title']}", "type": "info",
   "text": f"👈 **{creator}** поручил(а) тебе задачу: **{row['title']}** (+{row['reward']} 🪙)"
  })

 # 3. Кулдаун интервальных задач
 for _, row in db["tasks"].iterrows():
  if row.get('task_type') == "Интервальная" and row['assigned_to'] in [current_user, "Оба"]:
   raw_last_done = row.get('last_completed')
   if pd.notna(raw_last_done) and str(raw_last_done).strip() not in ["", "nan"]:
    try:
     last_done_dt = pd.to_datetime(str(raw_last_done)).tz_localize(None)
     val = int(row.get('interval_value', 0))
     unit = row.get('interval_unit', 'Часы')
     offset = timedelta(hours=val) if unit == "Часы" else timedelta(days=val)
     if now >= (last_done_dt + offset):
      active_notifications.append({
       "id": f"cooldown_{row['title']}", "type": "warning",
       "text": f"⏳ Снова доступно: **{row['title']}** (+{row['reward']} 🪙)"
      })
    except: pass

# 4. Доступные по деньгам лоты
if "market" in db and not db["market"].empty:
 affordable_lots = db["market"][
  (db["market"]["seller"] != current_user) & 
  (db["market"]["type"] != "Общий") & 
  (db["market"]["price"] <= my_balance)
 ]
 for _, lot in affordable_lots.iterrows():
  active_notifications.append({
   "id": f"lot_{lot['title']}", "type": "success_lot",
   "text": f"🛍️ Вы накопили на **{lot['title']}** (Цена: {lot['price']} 🪙)!"
  })

# Считаем количество НОВЫХ уведомлений
new_notif_count = sum(1 for n in active_notifications if n["id"] not in st.session_state.seen_notifications)


# ==========================================
# ЧИСТЫЙ И ПРАВИЛЬНЫЙ САЙДБАР
# ==========================================
with st.sidebar:
 st.header(f"👋 Привет, {DISPLAY[current_user]}!")
 
 # Виджет баланса
 with st.container(border=True):
  st.markdown(f"<h2 style='text-align: center; margin:0;'>{my_balance} 🪙</h2>", unsafe_allow_html=True)
  st.markdown("<p style='text-align: center; color: gray; margin:0;'>Ваш баланс</p>", unsafe_allow_html=True)
  
 st.markdown("---")
 
 # Виджет уровня
 lvl, progress, current_xp, next_xp, lvl_title = get_level_data(my_rating)
 st.markdown(f"🏅 **Уровень {lvl}: {lvl_title}**")
 st.progress(progress)
 st.caption(f"Опыт рейтинга: {current_xp} / {next_xp} 💖")
 
 st.markdown("---")
 st.subheader("🗺️ Навигация")
 
 # Кнопки страниц
 if st.button("📋 Список заданий", use_container_width=True):
  st.session_state.page = "tasks"
  st.rerun()
  
 if st.button("🛒 Маркетплейс", use_container_width=True):
  st.session_state.page = "market"
  st.rerun()
  
 if st.button("👤 Личный кабинет", use_container_width=True):
  st.session_state.page = "profile"
  st.rerun()

 # 🔥 Железобетонный вариант через обычный if/else (без однострочников)
 if new_notif_count > 0:
  btn_label = f"🔔 Уведомления ({new_notif_count})"
 else:
  btn_label = "🔔 Уведомления"

 if st.button(btn_label, use_container_width=True):
  st.session_state.page = "notifications"
  st.rerun()
  
 st.markdown("---")
 
 # Кнопка ручной синхронизации
 if st.button("🔄 Синхронизация", use_container_width=True):
  st.cache_data.clear()
  st.toast("Данные успешно обновлены из Google Sheets!")
  st.rerun()
  
 # Кнопка выхода
 if st.button("🚪 Выйти из аккаунта", use_container_width=True):
  st.session_state.user = None
  st.rerun()
# ==========================================
# ГЛАВНАЯ СТРАНИЦА (ЗАДАЧИ)
# ==========================================
if st.session_state.page == "tasks":
 st.title("✅ Задачи")

 # --- 1. ОПИСЫВАЕМ МОДАЛЬНЫЕ ОКНА ---
 @st.dialog("➕ Создать задачу")
 def add_task_modal():
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
   
  title = st.text_input("Что сделать?", value=default_title)
  reward = st.number_input("Награда (🪙)", min_value=1, value=default_reward)
  task_comment = st.text_area("Комментарий / Уточнения (необязательно)")
  assignee = st.selectbox("Кто выполняет?", ["Муж", "Жена", "Оба"], format_func=lambda x: DISPLAY.get(x, x))
  t_type = st.radio("Режим задачи", ["Разовая", "Интервальная"])
  
  val, unit = 0, ""
  if t_type == "Интервальная":
   c_val, c_unit = st.columns(2)
   val = c_val.number_input("Интервал повтора", min_value=1, value=12)
   unit = c_unit.selectbox("Единица времени", ["Часы", "Дни"])
   
  if st.button("Выставить на доску", use_container_width=True):
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
    
    t_label = DISPLAY.get(assignee, assignee)
    send_telegram(f"🔔 Новая задача: {clean_title} ({reward} 🪙) для {t_label}!", target=assignee)
    
    # st.rerun() внутри модального окна мгновенно закрывает его и обновляет основную страницу!
    st.rerun() 

 @st.dialog("✨ Настройка шаблонов")
 def add_template_modal():
  with st.form("new_template_form", clear_on_submit=True):
   tpl_title = st.text_input("Название шаблона")
   tpl_reward = st.number_input("Фиксированная награда (🪙)", min_value=1, value=5)
   if st.form_submit_button("Сохранить этот шаблон"):
    if tpl_title.strip():
     new_tpl = {"title": tpl_title.strip(), "reward": int(tpl_reward)}
     db["templates"] = pd.concat([db["templates"], pd.DataFrame([new_tpl])], ignore_index=True)
     save_data("templates", db["templates"])
     st.rerun()

 # --- 2. КНОПКИ ВЫЗОВА ОКОН ---
 # Теперь вместо громоздких экспандеров у тебя две аккуратные кнопки
 col_btn1, col_btn2 = st.columns(2)
 if col_btn1.button("➕ Добавить задачу", use_container_width=True):
  add_task_modal()
 if col_btn2.button("✨ Шаблоны цен", use_container_width=True):
  add_template_modal()

 st.markdown("---")

 # --- ПАНЕЛЬ ФИЛЬТРОВ ---
 col_h, col_r = st.columns([4, 1])
 col_h.subheader("🔍 Фильтры")
 
 # Кнопка сброса
 if col_r.button("🔄 Сброс", use_container_width=True):
  st.session_state.f_assignee = "Все"
  st.session_state.f_type = "Все"
  st.session_state.f_sort = "По умолчанию"
  st.rerun()

 cf1, cf2, cf3 = st.columns(3)
 
 # Добавили key, чтобы кнопка сброса могла ими управлять
 f_assignee = cf1.selectbox("Для кого?", ["Все", "Муж", "Жена", "Оба"], 
          format_func=lambda x: DISPLAY.get(x, x), key="f_assignee")
 f_type = cf2.selectbox("Тип задачи", ["Все", "Разовые", "Интервальные"], key="f_type")
 f_sort = cf3.selectbox("Сортировка", ["По умолчанию", "Дорогие", "Дешевые"], key="f_sort")

 df_f = db["tasks"].copy()

 if f_assignee != "Все":
  if f_assignee in ["Муж", "Жена"]:
   df_f = df_f[df_f["assigned_to"].isin([f_assignee, "Оба"])]
  else:
   df_f = df_f[df_f["assigned_to"] == "Оба"]

 if f_type != "Все":
  df_f = df_f[df_f["task_type"] == ("Разовая" if f_type == "Разовые" else "Интервальная")]

 if f_sort == "Дорогие":
  df_f = df_f.sort_values(by="reward", ascending=False)
 elif f_sort == "Дешевые":
  df_f = df_f.sort_values(by="reward", ascending=True)

 df_f = df_f.reset_index(drop=True)

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

 final_list = sorted(final_list, key=lambda x: x['available'], reverse=True)

 if not final_list:
  st.info("Задач нет. Попробуй изменить фильтры!")
 else:
  for item in final_list:
   row = item["row"]
   idx = item["orig_idx"]
   can_do = item["available"]
   is_my = row['assigned_to'] in [current_user, "Оба"]
   
   with st.container(border=True):
    c1, c2 = st.columns([5, 0.5])
    c1.write(f"**{row['title']}** (+{row['reward']} 🪙)")
    
    if c2.button("🗑️", key=f"del_{idx}"):
     db["tasks"] = db["tasks"][db["tasks"]["title"] != row["title"]]
     save_data("tasks", db["tasks"])
     st.rerun()

    # 🔥 ФИКС: Умная проверка комментария на "nan"
    comment = row.get('comment')
    if pd.notna(comment) and str(comment).strip().lower() not in ["nan", "none", ""]:
     st.caption(f"💬 {comment}")
    
    label_to = DISPLAY.get(row['assigned_to'], row['assigned_to'])
    label_from = DISPLAY.get(row.get('created_by', 'Система'), row.get('created_by', 'Система'))
    st.caption(f"✍️ {label_from} ➔ 🎯 {label_to}")

    btn_c, status_c = st.columns([1, 1])
    
      # --- ЛОГИКА ДЛЯ ЗАДАЧ "ОБА" (ТУМБЛЕР) ---
    is_joint = False
    if row['assigned_to'] == "Оба" and can_do:
     is_joint = st.toggle("🤝 Выполнили вдвоем?", key=f"joint_tog_{idx}")
     if is_joint:
      st.caption("✨ Награда и опыт упадут обоим!")

    if row['task_type'] == "Интервальная" and not can_do:
     # (Тут остается твой старый код расчета времени кулдауна)
     last_dt = pd.to_datetime(str(row['last_completed'])).tz_localize(None)
     delta = timedelta(hours=int(row['interval_value'])) if row['interval_unit'] == "Часы" else timedelta(days=int(row['interval_value']))
     diff = (last_dt + delta) - now
     h, rem = divmod(diff.seconds, 3600)
     m, _ = divmod(rem, 60)
     status_c.write(f"⏳ {diff.days}д {h}ч {m}м")
     btn_c.button("⏳", key=f"wait_{idx}", disabled=True, use_container_width=True)
    else:
     if btn_c.button("✅ Готово!", key=f"done_{idx}", disabled=not is_my, use_container_width=True):
      # 1. ОПРЕДЕЛЯЕМ, КОМУ НАЧИСЛЯТЬ
      users_to_reward = []
      if is_joint:
       users_to_reward = ["Муж", "Жена"]
      else:
       users_to_reward = [current_user]
      
      # 2. НАЧИСЛЯЕМ НАГРАДУ И ОПЫТ
      for u in users_to_reward:
       db["balances"].loc[0, u] += int(row['reward'])
       db["balances"].loc[0, f"{u}_Рейтинг"] += 10
      
      # 3. ЛОГИРУЕМ В ИСТОРИЮ
      current_time = now.strftime("%d.%m.%Y %H:%M")
      log_suffix = " (Совместно)" if is_joint else ""
      new_log = pd.DataFrame([{
       "date": current_time, 
       "buyer": current_user, 
       "item": f"{row['title']}{log_suffix}", 
       "price": row['reward'], 
       "seller": "Система", 
       "type": "Работа"
      }])
      db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
      
      # 4. ОБНОВЛЯЕМ СОСТОЯНИЕ ЗАДАЧИ
      if row['task_type'] == "Интервальная":
       db["tasks"].loc[db["tasks"]["title"] == row["title"], "last_completed"] = now.strftime('%Y-%m-%d %H:%M:%S')
      else:
       db["tasks"] = db["tasks"][db["tasks"]["title"] != row["title"]]
      
      save_data("balances", db["balances"])
      save_data("tasks", db["tasks"])
      save_data("history", db["history"])
      
      if is_joint: st.balloons() # Маленький праздник для двоих
      st.rerun()
    
# ==========================================
# ЭКРАН: МАРКЕТПЛЕЙС
# ==========================================
elif st.session_state.page == "market":
 st.title("🛒 Маркетплейс")

 # --- ФОРМА СОЗДАНИЯ ЛОТА (МОДАЛЬНОЕ ОКНО) ---
 @st.dialog("🏷️ Выставить лот на продажу")
 def add_market_modal():
  m_title = st.text_input("Что продаем / На что копим?")
  m_price = st.number_input("Цена или Цель (🪙)", min_value=1, value=50)
  m_type = st.selectbox("Тип лота", ["Индивидуальный", "Общий"])
  m_seller = st.selectbox("Кто предоставляет?", ["Муж", "Жена", "Оба"], format_func=lambda x: DISPLAY.get(x, x))
  
  if st.button("Выставить на маркет", use_container_width=True):
   if m_title.strip():
    new_item = {
     "title": m_title.strip(), 
     "price": m_price, 
     "seller": m_seller, 
     "type": m_type,
     "collected": 0,
     "contributions": ""
    }
    db["market"] = pd.concat([db["market"], pd.DataFrame([new_item])], ignore_index=True)
    
    current_time = now.strftime("%d.%m.%Y %H:%M")
    log_type = "Цель" if m_type == "Общий" else "Лот"
    log_lot = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": f"Новая {log_type}: {m_title}", "price": 0, "seller": "Система", "type": "Инфраструктура"}])
    db["history"] = pd.concat([db["history"], log_lot], ignore_index=True)
    
    save_data("market", db["market"])
    save_data("history", db["history"])
    
    st.rerun()
   else:
    st.warning("Введите название лота!")

 if st.button("➕ Выставить лот на продажу", use_container_width=True):
  add_market_modal()

 st.markdown("---")

 # --- ПАНЕЛЬ ФИЛЬТРОВ ---
 col_mh, col_mr = st.columns([4, 1])
 col_mh.subheader("🔍 Фильтры витрины")
 
 if col_mr.button("🔄 Сброс", key="res_market"):
  st.session_state.m_filter = "Все"
  st.rerun()

 m_filter = st.selectbox(
  "Что показать?", 
  ["Все", "Доступные для покупки", "Мои лоты на витрине"], 
  key="m_filter"
 )

 # Подготовка данных
 df_m = db["market"].copy()

 # Логика фильтрации
 if m_filter == "Доступные для покупки":
  df_m = df_m[df_m["seller"] != current_user]
 elif m_filter == "Мои лоты на витрине":
  df_m = df_m[df_m["seller"].isin([current_user, "Оба"])]

 # Сбрасываем индекс для корректной работы кнопок
 df_m = df_m.reset_index(drop=True)

 # --- ВЫВОД ЛОТОВ ---
 if df_m.empty:
  st.info("На витрине пока ничего не найдено по этим фильтрам.")
 else:
  for j, row in df_m.iterrows():
   l_type = row.get('type', 'Индивидуальный')
   price = int(row['price'])
   collected = int(row.get('collected', 0)) if pd.notna(row.get('collected')) else 0
   contribs = str(row.get('contributions', ''))
   
   # Карточка лота
   with st.container(border=True):
    # Немного расширил центральную колонку под длинные названия кнопок с ценой
    c1, c2, c3 = st.columns([3, 1.3, 0.5])
    
    # Кнопка удаления
    if c3.button("🗑️", key=f"del_m_{j}"):
     db["market"] = db["market"][db["market"]["title"] != row["title"]]
     save_data("market", db["market"])
     st.rerun()

    if l_type == "Общий":
     # --- ЛОГИКА ОБЩЕГО ЛОТА ---
     progress = min(collected / price, 1.0)
     c1.write(f"🤝 **{row['title']}**")
     c1.progress(progress)
     c1.caption(f"Накоплено: **{collected}** из **{price}** 🪙")
     
     if pd.notna(contribs) and contribs.strip().lower() not in ["nan", "none", ""]:
      c1.markdown(f"<p style='font-size: 11px; color: gray;'>Вклады: {contribs}</p>", unsafe_allow_html=True)
     
     if collected < price:
      donate_amount = c2.number_input("Сумма", min_value=1, max_value=max(1, price - collected), value=min(10, price - collected), key=f"don_val_{j}")
      if c2.button("Скинуться", key=f"don_btn_{j}", disabled=(my_balance < donate_amount), use_container_width=True):
       db["balances"].loc[0, current_user] -= donate_amount
       
       idx_in_db = db["market"][db["market"]["title"] == row["title"]].index[0]
       db["market"].at[idx_in_db, 'collected'] = collected + donate_amount
       
       user_label = DISPLAY[current_user]
       new_contrib = f"{user_label}: {donate_amount}"
       old_contribs = contribs if (pd.notna(contribs) and contribs.strip().lower() not in ["nan", ""]) else ""
       db["market"].at[idx_in_db, 'contributions'] = f"{old_contribs}, {new_contrib}".strip(", ")
       
       current_time = now.strftime("%d.%m.%Y %H:%M")
       new_log = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": f"Вклад в: {row['title']}", "price": donate_amount, "seller": "Общак", "type": "Покупка"}])
       db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
       
       save_data("balances", db["balances"]); save_data("market", db["market"]); save_data("history", db["history"])
       st.rerun()
     else:
      c2.success("Готово! 🎉")
      if c2.button("Закрыть цель", key=f"close_{j}", use_container_width=True):
       db["market"] = db["market"][db["market"]["title"] != row["title"]]
       save_data("market", db["market"])
       st.rerun()

    else:
     # --- ЛОГИКА ИНДИВИДУАЛЬНОГО ЛОТА ---
     is_my_item = (row['seller'] == current_user)
     can_buy = (not is_my_item) and (my_balance >= price)
     
     # 🔥 Цена переехала внутрь текста кнопки! В заголовке больше нет скобок.
     btn_label = f"Мой лот ({price} 🪙)" if is_my_item else f"Купить за {price} 🪙"
     
     c1.write(f"🎁 **{row['title']}**")
     if is_my_item: c1.caption("*(Ваше на витрине)*")
     
     if c2.button(btn_label, key=f"m_{j}", disabled=not can_buy, use_container_width=True):
      db["balances"].loc[0, current_user] -= price
      if row['seller'] != "Оба":
       partner_key = f"{row['seller']}_Рейтинг"
       db["balances"].loc[0, partner_key] += price
      
      current_time = now.strftime("%d.%m.%Y %H:%M")
      new_log = pd.DataFrame([{"date": current_time, "buyer": current_user, "item": row['title'], "price": price, "seller": row['seller'], "type": "Покупка", "status": "Ожидает"}])
      db["history"] = pd.concat([db["history"], new_log], ignore_index=True)
      
      # Удаляем купленный лот
      db["market"] = db["market"][db["market"]["title"] != row["title"]]
      
      save_data("balances", db["balances"]); save_data("market", db["market"]); save_data("history", db["history"])
      st.balloons()
      st.rerun()

 st.markdown("---")
  
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

   # --- ИСТОРИЯ ПОКУПОК С КНОПКОЙ СТАТУСА ---
 st.subheader("🛍️ История моих покупок")
 my_buys = db["history"][(db["history"]['buyer'] == current_user) & (db["history"]['type'] == 'Покупка')]

 if not my_buys.empty:
  for idx, row in my_buys.iterrows():
   # Безопасно проверяем статус. Если пустой — значит это старая запись, ставим "Ожидает"
   status = row.get("status", "Ожидает")
   if pd.isna(status) or str(status).strip() in ["", "nan", "None"]:
    status = "Ожидает"
    
   price = int(row['price'])
   seller = row['seller']
   seller_label = DISPLAY.get(seller, seller)
   
   with st.container(border=True):
    c1, c2 = st.columns([3, 1.3], vertical_alignment="center")
    
    if status == "Выполнено":
     c1.write(f"✅ ~~{row['item']}~~ ({price} 🪙) — Исполнитель: *{seller_label}*")
     c2.button("Выполнено", key=f"done_buy_{idx}", disabled=True, use_container_width=True)
    else:
     c1.write(f"⏳ **{row['item']}** ({price} 🪙) — Исполнитель: *{seller_label}*")
     
     # Кнопка активна только если продавец — конкретный человек (Муж/Жена), а не "Общак"
     if seller in ["Муж", "Жена"]:
      if c2.button("Выполнено", key=f"done_buy_{idx}", use_container_width=True):
       # Считаем 25% опыта от стоимости лота
       xp_reward = int(price * 0.25)
       
       # Начисляем опыт исполнителю (продавцу лота)
       partner_rating_key = f"{seller}_Рейтинг"
       db["balances"].loc[0, partner_rating_key] += xp_reward
       
       # Проверяем/создаем колонку status в основной истории и меняем значение
       if "status" not in db["history"].columns:
        db["history"]["status"] = "Ожидает"
       
       db["history"].at[idx, "status"] = "Выполнено"
       
       # Сохраняем всё в Google Sheets
       save_data("balances", db["balances"])
       save_data("history", db["history"])
       
       st.success(f"🎉 {seller_label} получает +{xp_reward} 💖 опыта за выполнение!")
       st.rerun()
     else:
      # Заглушка для общих целей (где продавец "Общак")
      c2.button("Цель закрыта", key=f"done_buy_{idx}", disabled=True, use_container_width=True)
 else:
  st.write("Вы еще ничего не купили.")
 
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

# ==========================================
# ЭКРАН 4: УВЕДОМЛЕНИЯ
# ==========================================
elif st.session_state.page == "notifications":
 st.title("🔔 Твои уведомления")
 now_dt = datetime.now()
 
 # Инициализируем хранилище прочитанных уведомлений в сессии
 if "seen_notifications" not in st.session_state:
  st.session_state.seen_notifications = set()
  
 active_notifications = []
 
 # 1. НОВЫЕ ДОСТИЖЕНИЯ
 if "achievements" in db and not db["achievements"].empty:
  my_achs = db["achievements"][db["achievements"]['user'] == current_user]
  if not my_achs.empty:
   # Твой расширенный словарь
   ach_names = {
    "scrupulous": "Скрупулезный 🧹",
    "bazar": "Базарный магнат 🛍️",
    "boss": "Босс качалки 💪",
    "templates": "Шаблонное мышление",
    "teamwork": "Командная работа",
    "consumer": "🍪 Потребитель",
    "habit": "🔁 Дело привычки"
   }
   for _, ach in my_achs.tail(3).iterrows():
    raw_ach = ach['achievement']
    display_ach = ach_names.get(raw_ach, raw_ach)
    active_notifications.append({
     "id": f"ach_{raw_ach}",
     "type": "success",
     "text": f"🏆 **Получено достижение:** {display_ach}"
    })

 # 2. ПОРУЧЕННЫЕ ЗАДАНИЯ
 if "tasks" in db and not db["tasks"].empty:
  assigned_tasks = db["tasks"][
   (db["tasks"]["created_by"] != current_user) & 
   (db["tasks"]["created_by"] != "Система") &
   (db["tasks"]["assigned_to"].isin([current_user, "Оба"]))
  ]
  for _, row in assigned_tasks.iterrows():
   creator = DISPLAY.get(row['created_by'], row['created_by'])
   active_notifications.append({
    "id": f"task_{row['title']}",
    "type": "info",
    "text": f"👈 **{creator}** оставил(а) задачу: **{row['title']}** (+{row['reward']} 🪙)"
   })

 # 3. ИНТЕРВАЛЬНЫЕ ЗАДАЧИ, ВЫШЕДШИЕ ИЗ КУЛДАУНА
 if "tasks" in db and not db["tasks"].empty:
  for _, row in db["tasks"].iterrows():
   if row.get('task_type') == "Интервальная" and row['assigned_to'] in [current_user, "Оба"]:
    raw_last_done = row.get('last_completed')
    if pd.notna(raw_last_done) and str(raw_last_done).strip() not in ["", "nan"]:
     try:
      last_done_dt = pd.to_datetime(str(raw_last_done))
      if last_done_dt.tzinfo is not None:
       last_done_dt = last_done_dt.tz_localize(None)
      
      val = int(row.get('interval_value', 0))
      unit = row.get('interval_unit', 'Часы')
      offset = timedelta(hours=val) if unit == "Часы" else timedelta(days=val)
      next_available = last_done_dt + offset
      
      if now_dt >= next_available:
       active_notifications.append({
        "id": f"cooldown_{row['title']}",
        "type": "warning",
        "text": f"⏳ Снова доступно к выполнению: **{row['title']}** (+{row['reward']} 🪙)"
       })
     except:
      pass

 # 4. ДОСТУПНЫЕ ПОКУПКИ (Накоплено монет на лоты)
 if "market" in db and not db["market"].empty:
  affordable_lots = db["market"][
   (db["market"]["seller"] != current_user) & 
   (db["market"]["type"] != "Общий") & 
   (db["market"]["price"] <= my_balance)
  ]
  for _, lot in affordable_lots.iterrows():
   active_notifications.append({
    "id": f"lot_{lot['title']}",
    "type": "success_lot",
    "text": f"🛍️ Вы накопили на **{lot['title']}** (Цена: {lot['price']} 🪙)!"
   })

 # --- ОТРИСОВКА УВЕДОМЛЕНИЙ ---
 if not active_notifications:
  st.info("Тишина и покой! Новых уведомлений пока нет. 🍃")
 else:
  # Фильтруем на основе сессии
  new_items = [n for n in active_notifications if n["id"] not in st.session_state.seen_notifications]
  read_items = [n for n in active_notifications if n["id"] in st.session_state.seen_notifications]
  
  # 1. Показываем новые (цветные)
  if new_items:
   st.subheader("🆕 Новые")
   for n in new_items:
    if n["type"] in ["success", "success_lot"]:
     st.success(n["text"])
     if n["type"] == "success_lot": 
      st.balloons() # Оставил твои шарики для радости покупок
    elif n["type"] == "info":
     st.info(n["text"])
    elif n["type"] == "warning":
     st.warning(n["text"])
  
  # 2. Показываем старые (серые)
  if read_items:
   st.subheader("📜 Прочитанные")
   for n in read_items:
    # Используем HTML, чтобы текст был блеклым
    st.markdown(f"🔘 <span style='color: #9cb0a9;'>{n['text']}</span>", unsafe_allow_html=True)
  
  # Записываем все показанные новые уведомления в "прочитанные"
  for n in new_items:
   st.session_state.seen_notifications.add(n["id"])

 st.markdown("---")
