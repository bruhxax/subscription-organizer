"""
Telegram Bot для управления подписками
Органайзер подписок с Mini Apps
"""
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
from database import Database
from config import BOT_TOKEN, WEBAPP_URL, ADMIN_IDS
from notifications import NotificationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
db = Database()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
notification_service = NotificationService(bot, db)

# FSM States
class AddSubscription(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_category = State()
    waiting_for_start_date = State()
    waiting_for_trial_end = State()

# Тексты на русском и английском
TEXTS = {
    'ru': {
        'welcome': """🎉 Добро пожаловать в Органайзер Подписок!

Я помогу вам:
✅ Отслеживать все ваши подписки
💰 Контролировать расходы
🔔 Получать напоминания о продлении
📊 Анализировать траты

Нажмите кнопку ниже, чтобы открыть приложение!""",
        'menu': '🏠 Главное меню',
        'open_app': '📱 Открыть приложение',
        'stats': '📊 Статистика',
        'settings': '⚙️ Настройки',
        'premium': '⭐ Premium',
        'help': '❓ Помощь',
        'admin': '👨‍💼 Админ-панель'
    },
    'en': {
        'welcome': """🎉 Welcome to Subscription Organizer!

I will help you:
✅ Track all your subscriptions
💰 Control expenses
🔔 Get renewal reminders
📊 Analyze spending

Click the button below to open the app!""",
        'menu': '🏠 Main Menu',
        'open_app': '📱 Open App',
        'stats': '📊 Statistics',
        'settings': '⚙️ Settings',
        'premium': '⭐ Premium',
        'help': '❓ Help',
        'admin': '👨‍💼 Admin Panel'
    }
}

def get_text(user_id: int, key: str) -> str:
    """Получить текст с учетом языка пользователя"""
    lang = db.get_user_language(user_id) or 'ru'
    return TEXTS.get(lang, TEXTS['ru']).get(key, key)

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главная клавиатура бота"""
    lang = db.get_user_language(user_id) or 'ru'
    buttons = [
        [InlineKeyboardButton(
            text=TEXTS[lang]['open_app'],
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [
            InlineKeyboardButton(text=TEXTS[lang]['stats'], callback_data='stats'),
            InlineKeyboardButton(text=TEXTS[lang]['settings'], callback_data='settings')
        ],
        [InlineKeyboardButton(text=TEXTS[lang]['premium'], callback_data='premium')]
    ]
    
    # Админ-кнопка для администраторов
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton(text=TEXTS[lang]['admin'], callback_data='admin')])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ''
    full_name = message.from_user.full_name or ''
    
    # Регистрация пользователя
    db.add_user(user_id, username, full_name)
    
    welcome_text = get_text(user_id, 'welcome')
    keyboard = get_main_keyboard(user_id)
    
    await message.answer(welcome_text, reply_markup=keyboard)
    logger.info(f"User {user_id} started the bot")

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message):
    """Показать главное меню"""
    user_id = message.from_user.id
    menu_text = get_text(user_id, 'menu')
    keyboard = get_main_keyboard(user_id)
    
    await message.answer(menu_text, reply_markup=keyboard)

@dp.callback_query(F.data == 'stats')
async def show_stats(callback: types.CallbackQuery):
    """Показать статистику пользователя"""
    user_id = callback.from_user.id
    stats = db.get_user_stats(user_id)
    
    lang = db.get_user_language(user_id) or 'ru'
    
    if lang == 'ru':
        stats_text = f"""📊 Ваша статистика:

💳 Всего подписок: {stats['total_subscriptions']}
✅ Активных: {stats['active_subscriptions']}
💰 Месячные расходы: ${stats['monthly_cost']:.2f}
📅 Годовые расходы: ${stats['yearly_cost']:.2f}

📈 По категориям:"""
    else:
        stats_text = f"""📊 Your statistics:

💳 Total subscriptions: {stats['total_subscriptions']}
✅ Active: {stats['active_subscriptions']}
💰 Monthly expenses: ${stats['monthly_cost']:.2f}
📅 Yearly expenses: ${stats['yearly_cost']:.2f}

📈 By category:"""
    
    for category, amount in stats['by_category'].items():
        stats_text += f"\n  • {category}: ${amount:.2f}"
    
    # Ближайшие продления
    upcoming = db.get_upcoming_renewals(user_id, days=7)
    if upcoming:
        stats_text += "\n\n🔔 Ближайшие продления:" if lang == 'ru' else "\n\n🔔 Upcoming renewals:"
        for sub in upcoming[:3]:
            days_left = (sub['next_payment'] - datetime.now()).days
            stats_text += f"\n  • {sub['name']} - через {days_left} дн." if lang == 'ru' else f"\n  • {sub['name']} - in {days_left} days"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='« Назад' if lang == 'ru' else '« Back', callback_data='back_to_menu')]
    ])
    
    await callback.message.edit_text(stats_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == 'settings')
async def show_settings(callback: types.CallbackQuery):
    """Показать настройки"""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user.get('language', 'ru')
    
    settings_text = "⚙️ Настройки\n\n" if lang == 'ru' else "⚙️ Settings\n\n"
    settings_text += f"🌐 Язык: {'Русский' if lang == 'ru' else 'English'}\n"
    settings_text += f"🔔 Уведомления: {'Вкл' if user.get('notifications_enabled') else 'Выкл'}\n" if lang == 'ru' else f"🔔 Notifications: {'On' if user.get('notifications_enabled') else 'Off'}\n"
    settings_text += f"📅 Напоминать за: {user.get('notification_days', 3)} дн.\n" if lang == 'ru' else f"📅 Remind in: {user.get('notification_days', 3)} days\n"
    settings_text += f"🎨 Тема: {'Темная' if user.get('theme') == 'dark' else 'Светлая'}" if lang == 'ru' else f"🎨 Theme: {'Dark' if user.get('theme') == 'dark' else 'Light'}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='🌐 Сменить язык' if lang == 'ru' else '🌐 Change language',
            callback_data='change_language'
        )],
        [InlineKeyboardButton(
            text='🔔 Уведомления' if lang == 'ru' else '🔔 Notifications',
            callback_data='toggle_notifications'
        )],
        [InlineKeyboardButton(
            text='🎨 Сменить тему' if lang == 'ru' else '🎨 Change theme',
            callback_data='change_theme'
        )],
        [InlineKeyboardButton(text='« Назад' if lang == 'ru' else '« Back', callback_data='back_to_menu')]
    ])
    
    await callback.message.edit_text(settings_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == 'change_language')
async def change_language(callback: types.CallbackQuery):
    """Сменить язык"""
    user_id = callback.from_user.id
    current_lang = db.get_user_language(user_id) or 'ru'
    new_lang = 'en' if current_lang == 'ru' else 'ru'
    
    db.update_user_language(user_id, new_lang)
    
    text = "✅ Язык изменен на English" if new_lang == 'en' else "✅ Language changed to Русский"
    await callback.answer(text, show_alert=True)
    
    # Обновить настройки
    await show_settings(callback)

@dp.callback_query(F.data == 'toggle_notifications')
async def toggle_notifications(callback: types.CallbackQuery):
    """Переключить уведомления"""
    user_id = callback.from_user.id
    current_state = db.get_user(user_id).get('notifications_enabled', True)
    new_state = not current_state
    
    db.update_user_notifications(user_id, new_state)
    
    lang = db.get_user_language(user_id) or 'ru'
    text = f"✅ Уведомления {'включены' if new_state else 'выключены'}" if lang == 'ru' else f"✅ Notifications {'enabled' if new_state else 'disabled'}"
    await callback.answer(text, show_alert=True)
    
    await show_settings(callback)

@dp.callback_query(F.data == 'change_theme')
async def change_theme(callback: types.CallbackQuery):
    """Сменить тему"""
    user_id = callback.from_user.id
    current_theme = db.get_user(user_id).get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    
    db.update_user_theme(user_id, new_theme)
    
    lang = db.get_user_language(user_id) or 'ru'
    text = f"✅ Тема изменена на {'темную' if new_theme == 'dark' else 'светлую'}" if lang == 'ru' else f"✅ Theme changed to {new_theme}"
    await callback.answer(text, show_alert=True)
    
    await show_settings(callback)

@dp.callback_query(F.data == 'premium')
async def show_premium(callback: types.CallbackQuery):
    """Показать информацию о Premium"""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    is_premium = user.get('is_premium', False)
    lang = user.get('language', 'ru')
    
    if is_premium:
        premium_until = user.get('premium_until', '')
        if lang == 'ru':
            text = f"""⭐ Вы Premium-пользователь!

Активно до: {premium_until}

Ваши преимущества:
✅ Неограниченное количество подписок
📊 Расширенная аналитика и графики
📥 Экспорт данных (CSV, PDF)
🔔 Приоритетные уведомления
🎨 Эксклюзивные темы оформления
📈 История изменений подписок
🆘 Приоритетная поддержка"""
        else:
            text = f"""⭐ You are a Premium user!

Active until: {premium_until}

Your benefits:
✅ Unlimited subscriptions
📊 Advanced analytics and charts
📥 Data export (CSV, PDF)
🔔 Priority notifications
🎨 Exclusive themes
📈 Subscription history
🆘 Priority support"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='« Назад' if lang == 'ru' else '« Back', callback_data='back_to_menu')]
        ])
    else:
        if lang == 'ru':
            text = """⭐ Premium подписка

💎 Стоимость: $2.99/месяц

Что вы получите:
✅ Неограниченное количество подписок (бесплатно: 5)
📊 Расширенная аналитика и графики расходов
📥 Экспорт данных в CSV и PDF
🔔 Приоритетные уведомления
🎨 Эксклюзивные темы оформления
📈 История изменений подписок
🚫 Без рекламы
🆘 Приоритетная поддержка

Попробуйте 7 дней бесплатно!"""
        else:
            text = """⭐ Premium Subscription

💎 Price: $2.99/month

What you get:
✅ Unlimited subscriptions (free: 5)
📊 Advanced analytics and spending charts
📥 Export data to CSV and PDF
🔔 Priority notifications
🎨 Exclusive themes
📈 Subscription history
🚫 No ads
🆘 Priority support

Try 7 days free!"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text='💳 Оформить Premium' if lang == 'ru' else '💳 Get Premium',
                callback_data='buy_premium'
            )],
            [InlineKeyboardButton(text='« Назад' if lang == 'ru' else '« Back', callback_data='back_to_menu')]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == 'buy_premium')
async def buy_premium(callback: types.CallbackQuery):
    """Покупка Premium"""
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id) or 'ru'
    
    # Здесь должна быть интеграция с платежной системой
    # Для демо активируем пробный период
    db.activate_premium_trial(user_id, days=7)
    
    if lang == 'ru':
        text = """✅ Пробный период активирован!

Вы получили 7 дней Premium бесплатно!
Все функции уже доступны.

Для полной активации используйте /premium"""
    else:
        text = """✅ Trial period activated!

You got 7 days of Premium for free!
All features are now available.

For full activation use /premium"""
    
    await callback.answer(text, show_alert=True)
    await show_premium(callback)

@dp.callback_query(F.data == 'admin')
async def show_admin_panel(callback: types.CallbackQuery):
    """Админ-панель"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    admin_stats = db.get_admin_stats()
    
    text = f"""👨‍💼 Админ-панель

📊 Статистика:
👥 Всего пользователей: {admin_stats['total_users']}
⭐ Premium пользователей: {admin_stats['premium_users']}
💳 Всего подписок: {admin_stats['total_subscriptions']}
📈 Активных подписок: {admin_stats['active_subscriptions']}
💰 Общая сумма подписок: ${admin_stats['total_revenue']:.2f}

📅 За сегодня:
👤 Новых пользователей: {admin_stats['new_users_today']}
➕ Новых подписок: {admin_stats['new_subscriptions_today']}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Полная статистика', callback_data='admin_full_stats')],
        [InlineKeyboardButton(text='👥 Список пользователей', callback_data='admin_users')],
        [InlineKeyboardButton(text='📢 Рассылка', callback_data='admin_broadcast')],
        [InlineKeyboardButton(text='« Назад', callback_data='back_to_menu')]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == 'back_to_menu')
async def back_to_menu(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    menu_text = get_text(user_id, 'menu')
    keyboard = get_main_keyboard(user_id)
    
    await callback.message.edit_text(menu_text, reply_markup=keyboard)
    await callback.answer()

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    """Обработка данных от Web App"""
    import json
    
    user_id = message.from_user.id
    data = json.loads(message.web_app_data.data)
    
    action = data.get('action')
    
    if action == 'add_subscription':
        # Добавить подписку
        subscription_data = data.get('subscription')
        db.add_subscription(user_id, subscription_data)
        await message.answer("✅ Подписка добавлена!")
        
    elif action == 'update_subscription':
        # Обновить подписку
        subscription_id = data.get('subscription_id')
        subscription_data = data.get('subscription')
        db.update_subscription(user_id, subscription_id, subscription_data)
        await message.answer("✅ Подписка обновлена!")
        
    elif action == 'delete_subscription':
        # Удалить подписку
        subscription_id = data.get('subscription_id')
        db.delete_subscription(user_id, subscription_id)
        await message.answer("✅ Подписка удалена!")

# API эндпоинты для Web App
from aiohttp import web

async def get_user_data(request):
    """Получить данные пользователя"""
    user_id = int(request.query.get('user_id'))
    user = db.get_user(user_id)
    subscriptions = db.get_subscriptions(user_id)
    
    return web.json_response({
        'user': user,
        'subscriptions': subscriptions
    })

async def get_subscriptions(request):
    """Получить подписки пользователя"""
    user_id = int(request.query.get('user_id'))
    subscriptions = db.get_subscriptions(user_id)
    
    return web.json_response({
        'subscriptions': subscriptions
    })

async def add_subscription(request):
    """Добавить подписку"""
    data = await request.json()
    user_id = data['user_id']
    subscription = data['subscription']
    
    subscription_id = db.add_subscription(user_id, subscription)
    
    return web.json_response({
        'success': True,
        'subscription_id': subscription_id
    })

async def update_subscription(request):
    """Обновить подписку"""
    data = await request.json()
    user_id = data['user_id']
    subscription_id = data['subscription_id']
    subscription = data['subscription']
    
    db.update_subscription(user_id, subscription_id, subscription)
    
    return web.json_response({
        'success': True
    })

async def delete_subscription(request):
    """Удалить подписку"""
    data = await request.json()
    user_id = data['user_id']
    subscription_id = data['subscription_id']
    
    db.delete_subscription(user_id, subscription_id)
    
    return web.json_response({
        'success': True
    })

async def start_webapp():
    """Запустить веб-сервер для Web App"""
    app = web.Application()
    
    # Настройка CORS
    app.middlewares.append(cors_middleware)
    
    # Роуты API
    app.router.add_get('/api/user', get_user_data)
    app.router.add_get('/api/subscriptions', get_subscriptions)
    app.router.add_post('/api/subscriptions', add_subscription)
    app.router.add_put('/api/subscriptions', update_subscription)
    app.router.add_delete('/api/subscriptions', delete_subscription)
    
    # Статические файлы
    app.router.add_static('/static/', path='webapp/static', name='static')
    app.router.add_get('/', lambda req: web.FileResponse('webapp/index.html'))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("Web app started on port 8080")

@web.middleware
async def cors_middleware(request, handler):
    """CORS middleware"""
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

async def main():
    """Главная функция"""
    # Инициализация базы данных
    db.init_db()
    
    # Запуск веб-сервера
    await start_webapp()
    
    # Запуск сервиса уведомлений
    asyncio.create_task(notification_service.start())
    
    # Запуск бота
    logger.info("Bot started")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
