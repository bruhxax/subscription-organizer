"""
Конфигурационный файл бота
"""
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Токен Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# URL веб-приложения
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://panel-bruhxax.ru')

# Настройки базы данных PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'subscription_bot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# ID администраторов
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Настройки веб-сервера
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', '8080'))

# Настройки уведомлений
NOTIFICATION_CHECK_INTERVAL = int(os.getenv('NOTIFICATION_CHECK_INTERVAL', '300'))  # 5 минут

# Лимиты для бесплатной версии
FREE_SUBSCRIPTION_LIMIT = int(os.getenv('FREE_SUBSCRIPTION_LIMIT', '5'))

# Настройки Premium
PREMIUM_PRICE_MONTHLY = float(os.getenv('PREMIUM_PRICE_MONTHLY', '2.99'))
PREMIUM_TRIAL_DAYS = int(os.getenv('PREMIUM_TRIAL_DAYS', '7'))
