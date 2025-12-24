# Конфигурационный файл для Telegram бота

# Telegram Bot Token (замените на свой токен)
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Настройки базы данных
DATABASE_NAME = 'subscriptions.db'
DATABASE_PATH = 'db/subscriptions.db'

# Настройки Premium
PREMIUM_PRICE_MONTHLY = 2.99  # в долларах
MAX_FREE_SUBSCRIPTIONS = 5

# Настройки уведомлений
DEFAULT_REMINDER_DAYS = 3
DEFAULT_FREE_TRIAL_REMINDER_DAYS = 1

# Настройки локализации
SUPPORTED_LANGUAGES = ['ru', 'en']
DEFAULT_LANGUAGE = 'ru'

# Настройки админ-панели
ADMIN_USER_IDS = [123456789]  # Замените на ваш Telegram ID

# Настройки платежных систем
STRIPE_API_KEY = 'your_stripe_api_key'
PAYPAL_CLIENT_ID = 'your_paypal_client_id'
PAYPAL_SECRET = 'your_paypal_secret'

# Настройки веб-приложения
WEB_APP_URL = 'https://panel-bruhxax.ru/web_app'  # Замените на ваш домен
