import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('subscriptions.db')
    cursor = conn.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        language TEXT DEFAULT 'ru',
        is_premium BOOLEAN DEFAULT FALSE,
        premium_expiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Создание таблицы категорий подписок
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )
    ''')

    # Добавим стандартные категории
    categories = [
        ('Развлечения', 'Фильмы, музыка, игры'),
        ('Работа', 'Инструменты для работы'),
        ('Обучение', 'Образовательные сервисы'),
        ('VPN', 'Сервисы VPN'),
        ('Другое', 'Прочие подписки')
    ]

    for category in categories:
        cursor.execute('''
        INSERT OR IGNORE INTO categories (name, description)
        VALUES (?, ?)
        ''', category)

    # Создание таблицы подписок
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'RUB',
        start_date TEXT NOT NULL,
        end_date TEXT,
        free_trial_end_date TEXT,
        category_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')

    # Создание таблицы уведомлений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subscription_id INTEGER,
        message TEXT NOT NULL,
        is_sent BOOLEAN DEFAULT FALSE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
    )
    ''')

    # Создание таблицы настроек уведомлений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notification_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        subscription_reminder_days INTEGER DEFAULT 3,
        free_trial_reminder_days INTEGER DEFAULT 1,
        daily_summary BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("База данных успешно инициализирована.")

if __name__ == '__main__':
    init_db()
