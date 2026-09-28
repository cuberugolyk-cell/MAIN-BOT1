import sqlite3
from datetime import datetime

conn = sqlite3.connect("leads.db", check_same_thread=False)
cur = conn.cursor()


def init_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS texts (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, description TEXT, price TEXT,
        price_stars INTEGER DEFAULT 0,
        price_rub INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, name TEXT, contact TEXT,
        service TEXT, task TEXT, status TEXT DEFAULT 'новая',
        comment TEXT DEFAULT '', created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lead_id INTEGER,
        service_id INTEGER,
        amount REAL,
        currency TEXT,
        method TEXT,
        status TEXT DEFAULT 'pending',
        payload TEXT,
        created_at TEXT
    )""")
    conn.commit()

    defaults = {
        "welcome": "Здравствуйте. Я принимаю заявки на разработку ботов и автоматизацию.\n\nВыберите действие в меню ниже.",
        "about": "Разработка Telegram-ботов и автоматизация под задачи бизнеса.",
        "contacts": "Telegram: @ваш_ник\nEmail: your@mail.com",
        "ask_name": "Как к вам обращаться?",
        "ask_contact": "Контакт для связи (Telegram, телефон или email):",
        "ask_service": "Какая услуга интересует?",
        "ask_task": "Опишите задачу: что нужно сделать, для кого, какой результат ожидаете.",
        "after_lead": "Заявка №{id} принята. Отвечу в течение дня.",
        "payment_note": "Оплата согласовывается после обсуждения задачи.",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO texts (key, value) VALUES (?, ?)", (k, v))
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM services")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO services (title, description, price, price_stars, price_rub) VALUES (?, ?, ?, ?, ?)",
            [
                ("Telegram-бот", "Приём заказов, запись, квизы, рассылки", "от 150$", 1500, 15000),
                ("Автоматизация", "Отчёты, интеграции, скрипты", "от 100$", 1000, 10000),
                ("Парсер", "Сбор данных, мониторинг цен", "от 100$", 1000, 10000),
            ]
        )
        conn.commit()


def get_text(key, default=""):
    cur.execute("SELECT value FROM texts WHERE key = ?", (key,))
    r = cur.fetchone()
    return r[0] if r else default


def set_text(key, value):
    cur.execute("INSERT OR REPLACE INTO texts (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def all_texts():
    cur.execute("SELECT key, value FROM texts ORDER BY key")
    return cur.fetchall()


def list_services(active_only=True):
    if active_only:
        cur.execute("SELECT id, title, description, price, price_stars, price_rub FROM services WHERE is_active = 1 ORDER BY id")
    else:
        cur.execute("SELECT id, title, description, price, price_stars, price_rub, is_active FROM services ORDER BY id")
    return cur.fetchall()


def get_service(sid):
    cur.execute("SELECT id, title, description, price, price_stars, price_rub FROM services WHERE id = ?", (sid,))
    return cur.fetchone()


def add_service(title, description, price, price_stars=0, price_rub=0):
    cur.execute(
        "INSERT INTO services (title, description, price, price_stars, price_rub) VALUES (?, ?, ?, ?, ?)",
        (title, description, price, price_stars, price_rub)
    )
    conn.commit()
    return cur.lastrowid


def update_service(sid, field, value):
    if field not in ("title", "description", "price", "price_stars", "price_rub"):
        return
    cur.execute(f"UPDATE services SET {field} = ? WHERE id = ?", (value, sid))
    conn.commit()


def toggle_service(sid):
    cur.execute("UPDATE services SET is_active = 1 - is_active WHERE id = ?", (sid,))
    conn.commit()


def delete_service(sid):
    cur.execute("DELETE FROM services WHERE id = ?", (sid,))
    conn.commit()


def save_lead(user_id, username, name, contact, service, task):
    cur.execute(
        "INSERT INTO leads (user_id, username, name, contact, service, task, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, name, contact, service, task, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    return cur.lastrowid


def list_leads(limit=20):
    cur.execute("SELECT id, name, contact, service, status, created_at FROM leads ORDER BY id DESC LIMIT ?", (limit,))
    return cur.fetchall()


def get_lead(lead_id):
    cur.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    return cur.fetchone()


def set_lead_status(lead_id, status):
    cur.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()


def set_lead_comment(lead_id, comment):
    cur.execute("UPDATE leads SET comment = ? WHERE id = ?", (comment, lead_id))
    conn.commit()


def count_leads():
    cur.execute("SELECT COUNT(*) FROM leads")
    return cur.fetchone()[0]


def get_user_leads(user_id, limit=10):
    cur.execute("SELECT id, service, status, created_at FROM leads WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    return cur.fetchall()


def get_user_lead(user_id, lead_id):
    cur.execute(
        "SELECT id, service, status, task, created_at, comment FROM leads WHERE id = ? AND user_id = ?",
        (lead_id, user_id)
    )
    return cur.fetchone()


def get_setting(key, default=""):
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    r = cur.fetchone()
    return r[0] if r else default


def set_setting(key, value):
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def create_payment(user_id, lead_id, service_id, amount, currency, method, payload):
    cur.execute(
        "INSERT INTO payments (user_id, lead_id, service_id, amount, currency, method, payload, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, lead_id, service_id, amount, currency, method, payload,
         datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    return cur.lastrowid


def get_payment_by_payload(payload):
    cur.execute("SELECT * FROM payments WHERE payload = ?", (payload,))
    return cur.fetchone()


def set_payment_status(payment_id, status):
    cur.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
    conn.commit()


def list_payments(limit=20):
    cur.execute(
        "SELECT id, user_id, amount, currency, method, status, created_at "
        "FROM payments ORDER BY id DESC LIMIT ?", (limit,)
    )
    return cur.fetchall()


def count_payments_sum():
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'paid'")
    return cur.fetchone()[0]
