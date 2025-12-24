"""
Модуль базы данных для бота управления подписками
Использует PostgreSQL для хранения данных
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Инициализация подключения к БД"""
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        
        self.connection_params = {
            'host': DB_HOST,
            'port': DB_PORT,
            'database': DB_NAME,
            'user': DB_USER,
            'password': DB_PASSWORD
        }
    
    def get_connection(self):
        """Получить подключение к базе данных"""
        return psycopg2.connect(**self.connection_params)
    
    def init_db(self):
        """Инициализация таблиц базы данных"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                full_name VARCHAR(255),
                language VARCHAR(10) DEFAULT 'ru',
                theme VARCHAR(20) DEFAULT 'light',
                notifications_enabled BOOLEAN DEFAULT TRUE,
                notification_days INTEGER DEFAULT 3,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица подписок
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'USD',
                category VARCHAR(100),
                billing_cycle VARCHAR(20) DEFAULT 'monthly',
                start_date DATE NOT NULL,
                next_payment DATE NOT NULL,
                trial_end_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                icon VARCHAR(255),
                color VARCHAR(20),
                website_url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица категорий
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                icon VARCHAR(50),
                color VARCHAR(20),
                translation_ru VARCHAR(100),
                translation_en VARCHAR(100)
            )
        """)
        
        # Таблица уведомлений
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
                notification_type VARCHAR(50),
                scheduled_date TIMESTAMP NOT NULL,
                sent_at TIMESTAMP,
                is_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица истории изменений (для Premium)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscription_history (
                id SERIAL PRIMARY KEY,
                subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                action VARCHAR(50),
                old_data JSONB,
                new_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы для оптимизации
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_next_payment ON subscriptions(next_payment)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON notifications(scheduled_date, is_sent)")
        
        # Заполнение категорий по умолчанию
        default_categories = [
            ('Entertainment', '🎬', '#FF6B6B', 'Развлечения', 'Entertainment'),
            ('Streaming', '📺', '#4ECDC4', 'Стриминг', 'Streaming'),
            ('Music', '🎵', '#45B7D1', 'Музыка', 'Music'),
            ('Gaming', '🎮', '#96CEB4', '#Игры', 'Gaming'),
            ('Education', '📚', '#FFEAA7', 'Обучение', 'Education'),
            ('Work', '💼', '#DFE6E9', 'Работа', 'Work'),
            ('VPN', '🔒', '#A29BFE', 'VPN', 'VPN'),
            ('Cloud Storage', '☁️', '#74B9FF', 'Облачное хранилище', 'Cloud Storage'),
            ('News', '📰', '#FD79A8', 'Новости', 'News'),
            ('Fitness', '💪', '#55EFC4', 'Фитнес', 'Fitness'),
            ('Software', '💻', '#636E72', 'ПО', 'Software'),
            ('Other', '📦', '#B2BEC3', 'Другое', 'Other')
        ]
        
        for cat in default_categories:
            cur.execute("""
                INSERT INTO categories (name, icon, color, translation_ru, translation_en)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, cat)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully")
    
    # === ПОЛЬЗОВАТЕЛИ ===
    
    def add_user(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить нового пользователя"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO users (user_id, username, full_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    last_active = CURRENT_TIMESTAMP
            """, (user_id, username, full_name))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить данные пользователя"""
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            
            cur.close()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_language(self, user_id: int) -> str:
        """Получить язык пользователя"""
        user = self.get_user(user_id)
        return user.get('language', 'ru') if user else 'ru'
    
    def update_user_language(self, user_id: int, language: str):
        """Обновить язык пользователя"""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET language = %s WHERE user_id = %s", (language, user_id))
        conn.commit()
        cur.close()
        conn.close()
    
    def update_user_notifications(self, user_id: int, enabled: bool):
        """Обновить настройки уведомлений"""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET notifications_enabled = %s WHERE user_id = %s", (enabled, user_id))
        conn.commit()
        cur.close()
        conn.close()
    
    def update_user_theme(self, user_id: int, theme: str):
        """Обновить тему пользователя"""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET theme = %s WHERE user_id = %s", (theme, user_id))
        conn.commit()
        cur.close()
        conn.close()
    
    def activate_premium_trial(self, user_id: int, days: int = 7):
        """Активировать пробный период Premium"""
        conn = self.get_connection()
        cur = conn.cursor()
        premium_until = datetime.now() + timedelta(days=days)
        cur.execute("""
            UPDATE users 
            SET is_premium = TRUE, premium_until = %s 
            WHERE user_id = %s
        """, (premium_until, user_id))
        conn.commit()
        cur.close()
        conn.close()
    
    # === ПОДПИСКИ ===
    
    def add_subscription(self, user_id: int, data: Dict) -> int:
        """Добавить новую подписку"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO subscriptions 
            (user_id, name, description, price, currency, category, billing_cycle, 
             start_date, next_payment, trial_end_date, icon, color, website_url, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            data.get('name'),
            data.get('description', ''),
            data.get('price'),
            data.get('currency', 'USD'),
            data.get('category'),
            data.get('billing_cycle', 'monthly'),
            data.get('start_date'),
            data.get('next_payment'),
            data.get('trial_end_date'),
            data.get('icon'),
            data.get('color'),
            data.get('website_url'),
            data.get('notes')
        ))
        
        subscription_id = cur.fetchone()[0]
        
        # Создать уведомления
        self._create_notifications_for_subscription(cur, user_id, subscription_id, data.get('next_payment'))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Subscription {subscription_id} added for user {user_id}")
        return subscription_id
    
    def get_subscriptions(self, user_id: int, active_only: bool = False) -> List[Dict]:
        """Получить все подписки пользователя"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM subscriptions WHERE user_id = %s"
        if active_only:
            query += " AND is_active = TRUE"
        query += " ORDER BY next_payment ASC"
        
        cur.execute(query, (user_id,))
        subscriptions = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [dict(sub) for sub in subscriptions]
    
    def get_subscription(self, subscription_id: int) -> Optional[Dict]:
        """Получить подписку по ID"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM subscriptions WHERE id = %s", (subscription_id,))
        subscription = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return dict(subscription) if subscription else None
    
    def update_subscription(self, user_id: int, subscription_id: int, data: Dict):
        """Обновить подписку"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Сохранить старые данные для истории (если Premium)
        user = self.get_user(user_id)
        if user and user.get('is_premium'):
            old_data = self.get_subscription(subscription_id)
            cur.execute("""
                INSERT INTO subscription_history (subscription_id, user_id, action, old_data, new_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (subscription_id, user_id, 'update', psycopg2.extras.Json(old_data), psycopg2.extras.Json(data)))
        
        cur.execute("""
            UPDATE subscriptions 
            SET name = %s, description = %s, price = %s, currency = %s, category = %s,
                billing_cycle = %s, next_payment = %s, trial_end_date = %s, 
                icon = %s, color = %s, website_url = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        """, (
            data.get('name'),
            data.get('description'),
            data.get('price'),
            data.get('currency'),
            data.get('category'),
            data.get('billing_cycle'),
            data.get('next_payment'),
            data.get('trial_end_date'),
            data.get('icon'),
            data.get('color'),
            data.get('website_url'),
            data.get('notes'),
            subscription_id,
            user_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
    
    def delete_subscription(self, user_id: int, subscription_id: int):
        """Удалить подписку"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM subscriptions WHERE id = %s AND user_id = %s", (subscription_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
    
    def toggle_subscription_status(self, user_id: int, subscription_id: int):
        """Переключить статус активности подписки"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE subscriptions 
            SET is_active = NOT is_active 
            WHERE id = %s AND user_id = %s
        """, (subscription_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
    
    # === СТАТИСТИКА ===
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Общая статистика
        cur.execute("""
            SELECT 
                COUNT(*) as total_subscriptions,
                COUNT(*) FILTER (WHERE is_active = TRUE) as active_subscriptions,
                COALESCE(SUM(CASE 
                    WHEN billing_cycle = 'monthly' THEN price
                    WHEN billing_cycle = 'yearly' THEN price / 12
                    WHEN billing_cycle = 'weekly' THEN price * 4
                    ELSE price
                END) FILTER (WHERE is_active = TRUE), 0) as monthly_cost
            FROM subscriptions
            WHERE user_id = %s
        """, (user_id,))
        
        stats = dict(cur.fetchone())
        stats['yearly_cost'] = stats['monthly_cost'] * 12
        
        # Статистика по категориям
        cur.execute("""
            SELECT 
                category,
                SUM(CASE 
                    WHEN billing_cycle = 'monthly' THEN price
                    WHEN billing_cycle = 'yearly' THEN price / 12
                    WHEN billing_cycle = 'weekly' THEN price * 4
                    ELSE price
                END) as amount
            FROM subscriptions
            WHERE user_id = %s AND is_active = TRUE
            GROUP BY category
            ORDER BY amount DESC
        """, (user_id,))
        
        stats['by_category'] = {row['category']: float(row['amount']) for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        return stats
    
    def get_upcoming_renewals(self, user_id: int, days: int = 30) -> List[Dict]:
        """Получить предстоящие продления"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM subscriptions
            WHERE user_id = %s 
            AND is_active = TRUE
            AND next_payment BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
            ORDER BY next_payment ASC
        """, (user_id, days))
        
        renewals = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [dict(r) for r in renewals]
    
    def get_admin_stats(self) -> Dict:
        """Получить статистику для админ-панели"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Общая статистика
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM users WHERE is_premium = TRUE) as premium_users,
                (SELECT COUNT(*) FROM subscriptions) as total_subscriptions,
                (SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE) as active_subscriptions,
                (SELECT COALESCE(SUM(price), 0) FROM subscriptions WHERE is_active = TRUE) as total_revenue,
                (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE) as new_users_today,
                (SELECT COUNT(*) FROM subscriptions WHERE DATE(created_at) = CURRENT_DATE) as new_subscriptions_today
        """)
        
        stats = dict(cur.fetchone())
        
        cur.close()
        conn.close()
        
        return stats
    
    # === КАТЕГОРИИ ===
    
    def get_categories(self) -> List[Dict]:
        """Получить все категории"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM categories ORDER BY name")
        categories = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [dict(cat) for cat in categories]
    
    # === УВЕДОМЛЕНИЯ ===
    
    def _create_notifications_for_subscription(self, cur, user_id: int, subscription_id: int, next_payment):
        """Создать уведомления для подписки"""
        user = self.get_user(user_id)
        if not user or not user.get('notifications_enabled'):
            return
        
        notification_days = user.get('notification_days', 3)
        notification_date = next_payment - timedelta(days=notification_days)
        
        cur.execute("""
            INSERT INTO notifications (user_id, subscription_id, notification_type, scheduled_date)
            VALUES (%s, %s, %s, %s)
        """, (user_id, subscription_id, 'renewal', notification_date))
    
    def get_pending_notifications(self) -> List[Dict]:
        """Получить неотправленные уведомления"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT n.*, s.name as subscription_name, s.price, u.language
            FROM notifications n
            JOIN subscriptions s ON n.subscription_id = s.id
            JOIN users u ON n.user_id = u.user_id
            WHERE n.is_sent = FALSE 
            AND n.scheduled_date <= CURRENT_TIMESTAMP
            AND u.notifications_enabled = TRUE
        """)
        
        notifications = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [dict(n) for n in notifications]
    
    def mark_notification_sent(self, notification_id: int):
        """Отметить уведомление как отправленное"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE notifications 
            SET is_sent = TRUE, sent_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (notification_id,))
        
        conn.commit()
        cur.close()
        conn.close()
