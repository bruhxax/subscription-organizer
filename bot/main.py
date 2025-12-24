import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import sqlite3
from datetime import datetime, timedelta
import os
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем путь к модулям в sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from db.init_db import init_db
from config.config import BOT_TOKEN
from bot.premium import (
    check_premium_status, get_premium_keyboard,
    get_premium_features_message, check_subscription_limit,
    activate_premium, get_premium_analytics
)

# Инициализация базы данных
init_db()

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния для машины состояний
class SubscriptionStates(StatesGroup):
    adding_name = State()
    adding_amount = State()
    adding_start_date = State()
    adding_end_date = State()
    adding_free_trial_end_date = State()
    adding_category = State()
    adding_notes = State()

class SubscriptionEditStates(StatesGroup):
    editing_subscription = State()
    editing_field = State()
    editing_value = State()

# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton("📝 Мои подписки"),
        KeyboardButton("➕ Добавить подписку"),
        KeyboardButton("📊 Статистика"),
        KeyboardButton("⚙️ Настройки"),
        KeyboardButton("💎 Premium")
    ]
    keyboard.add(*buttons)
    return keyboard

def get_back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("⬅️ Назад"))
    return keyboard

def get_categories_keyboard():
    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    conn.close()

    keyboard = InlineKeyboardMarkup()
    for category in categories:
        keyboard.add(InlineKeyboardButton(category[1], callback_data=f'category_{category[0]}'))
    return keyboard

# Обработчики команд
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в базе
    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        # Добавляем нового пользователя
        cursor.execute('''
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))

        # Добавляем настройки уведомлений по умолчанию
        cursor.execute('''
        INSERT INTO notification_settings (user_id)
        VALUES (?)
        ''', (user_id,))

        conn.commit()

    conn.close()

    await message.reply(
        "🌟 Добро пожаловать в Органайзер Подписок!\n\n"
        "Я помогу вам управлять всеми вашими подписками в одном месте.\n\n"
        "Вы можете:\n"
        "📝 Просматривать свои подписки\n"
        "➕ Добавлять новые подписки\n"
        "📊 Видеть статистику расходов\n"
        "⚙️ Настраивать уведомления\n"
        "💎 Получать Premium-функции\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda message: message.text == "📝 Мои подписки")
async def list_subscriptions(message: types.Message):
    user_id = message.from_user.id

    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    # Получаем пользователя
    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        await message.reply("Вы не зарегистрированы. Пожалуйста, начните с команды /start")
        return

    user_db_id = user[0]

    # Получаем подписки пользователя
    cursor.execute('''
    SELECT s.id, s.name, s.amount, s.currency, s.start_date, s.end_date, s.free_trial_end_date, s.is_active, c.name
    FROM subscriptions s
    LEFT JOIN categories c ON s.category_id = c.id
    WHERE s.user_id = ?
    ORDER BY s.end_date
    ''', (user_db_id,))

    subscriptions = cursor.fetchall()
    conn.close()

    if not subscriptions:
        await message.reply("У вас пока нет подписок. Добавьте первую подписку!", reply_markup=get_main_keyboard())
        return

    response = "📋 Ваши подписки:\n\n"
    for sub in subscriptions:
        sub_id, name, amount, currency, start_date, end_date, free_trial_end_date, is_active, category = sub
        status = "✅ Активна" if is_active else "❌ Неактивна"

        # Проверяем, есть ли дата окончания бесплатного периода
        trial_info = ""
        if free_trial_end_date:
            trial_end = datetime.strptime(free_trial_end_date, '%Y-%m-%d')
            days_left = (trial_end - datetime.now()).days
            if days_left > 0:
                trial_info = f" (Бесплатный период: {days_left} дней)"
            else:
                trial_info = " (Бесплатный период закончился)"

        response += f"🔹 {name}\n"
        response += f"   💰 {amount} {currency}/мес\n"
        response += f"   📅 Начало: {start_date}\n"
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days_left = (end - datetime.now()).days
            response += f"   📅 Окончание: {end_date} ({days_left} дней осталось)\n"
        response += f"   📂 Категория: {category}\n"
        response += f"   🔘 {status}{trial_info}\n\n"

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Редактировать подписку", callback_data="edit_subscription"))
    keyboard.add(InlineKeyboardButton("🗑️ Удалить подписку", callback_data="delete_subscription"))
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"))

    await message.reply(response, reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "➕ Добавить подписку")
async def add_subscription_start(message: types.Message):
    await message.reply(
        "📝 Добавить новую подписку\n\n"
        "Введите название подписки (например, Netflix, Spotify):",
        reply_markup=get_back_keyboard()
    )
    await SubscriptionStates.adding_name.set()

@dp.message_handler(state=SubscriptionStates.adding_name)
async def process_subscription_name(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as data:
        data['name'] = message.text

    await message.reply("Введите сумму оплаты в месяц (например, 399):")
    await SubscriptionStates.next()

@dp.message_handler(state=SubscriptionStates.adding_amount)
async def process_subscription_amount(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    try:
        amount = float(message.text)
        async with state.proxy() as data:
            data['amount'] = amount
    except ValueError:
        await message.reply("Пожалуйста, введите корректную сумму (например, 399):")
        return

    await message.reply("Введите дату начала подписки в формате ГГГГ-ММ-ДД (например, 2023-12-01):")
    await SubscriptionStates.next()

@dp.message_handler(state=SubscriptionStates.adding_start_date)
async def process_subscription_start_date(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    try:
        start_date = datetime.strptime(message.text, '%Y-%m-%d')
        async with state.proxy() as data:
            data['start_date'] = start_date.strftime('%Y-%m-%d')
    except ValueError:
        await message.reply("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД (например, 2023-12-01):")
        return

    await message.reply("Введите дату окончания подписки в формате ГГГГ-ММ-ДД (или 'нет', если не известно):")
    await SubscriptionStates.next()

@dp.message_handler(state=SubscriptionStates.adding_end_date)
async def process_subscription_end_date(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as data:
        if message.text.lower() != 'нет':
            try:
                end_date = datetime.strptime(message.text, '%Y-%m-%d')
                data['end_date'] = end_date.strftime('%Y-%m-%d')
            except ValueError:
                await message.reply("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД или 'нет':")
                return
        else:
            data['end_date'] = None

    await message.reply("Введите дату окончания бесплатного периода в формате ГГГГ-ММ-ДД (или 'нет', если нет бесплатного периода):")
    await SubscriptionStates.next()

@dp.message_handler(state=SubscriptionStates.adding_free_trial_end_date)
async def process_subscription_free_trial_end_date(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as data:
        if message.text.lower() != 'нет':
            try:
                free_trial_end_date = datetime.strptime(message.text, '%Y-%m-%d')
                data['free_trial_end_date'] = free_trial_end_date.strftime('%Y-%m-%d')
            except ValueError:
                await message.reply("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД или 'нет':")
                return
        else:
            data['free_trial_end_date'] = None

    await message.reply("Выберите категорию подписки:", reply_markup=get_categories_keyboard())
    await SubscriptionStates.next()

@dp.callback_query_handler(lambda c: c.data.startswith('category_'), state=SubscriptionStates.adding_category)
async def process_subscription_category(callback_query: types.CallbackQuery, state: FSMContext):
    category_id = int(callback_query.data.split('_')[1])
    async with state.proxy() as data:
        data['category_id'] = category_id

    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Введите дополнительные заметки (или 'нет', если нет заметок):",
        reply_markup=get_back_keyboard()
    )
    await SubscriptionStates.next()

@dp.message_handler(state=SubscriptionStates.adding_notes)
async def process_subscription_notes(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.finish()
        await message.reply("Добавление подписки отменено.", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as data:
        if message.text.lower() != 'нет':
            data['notes'] = message.text
        else:
            data['notes'] = None

        # Сохраняем подписку в базу данных
        user_id = message.from_user.id
        conn = sqlite3.connect('db/subscriptions.db')
        cursor = conn.cursor()

        # Получаем пользователя
        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
        user = cursor.fetchone()
        user_db_id = user[0]

        # Вставляем подписку
        cursor.execute('''
        INSERT INTO subscriptions (
            user_id, name, amount, start_date, end_date, free_trial_end_date, category_id, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_db_id,
            data['name'],
            data['amount'],
            data['start_date'],
            data['end_date'],
            data['free_trial_end_date'],
            data['category_id'],
            data['notes']
        ))

        conn.commit()
        conn.close()

        await state.finish()
        await message.reply(
            "✅ Подписка успешно добавлена!\n\n"
            f"🔹 Название: {data['name']}\n"
            f"💰 Сумма: {data['amount']} RUB/мес\n"
            f"📅 Начало: {data['start_date']}\n"
            f"📅 Окончание: {data['end_date'] or 'Не указано'}\n"
            f"🎁 Бесплатный период: {data['free_trial_end_date'] or 'Нет'}\n"
            f"📂 Категория: {data.get('category_name', 'Не указано')}\n"
            f"📝 Заметки: {data['notes'] or 'Нет'}\n",
            reply_markup=get_main_keyboard()
        )

# Обработчики callback-запросов
@dp.callback_query_handler(lambda c: c.data == 'back_to_main')
async def back_to_main(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Вы вернулись в главное меню.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == 'edit_subscription')
async def edit_subscription(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Введите ID подписки, которую хотите редактировать (или 'отмена' для отмены):",
        reply_markup=get_back_keyboard()
    )
    await SubscriptionEditStates.editing_subscription.set()

@dp.message_handler(state=SubscriptionEditStates.editing_subscription)
async def process_edit_subscription_id(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад" or message.text.lower() == 'отмена':
        await state.finish()
        await message.reply("Редактирование отменено.", reply_markup=get_main_keyboard())
        return

    try:
        subscription_id = int(message.text)
        async with state.proxy() as data:
            data['subscription_id'] = subscription_id

        # Получаем информацию о подписке
        conn = sqlite3.connect('db/subscriptions.db')
        cursor = conn.cursor()

        user_id = message.from_user.id
        cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
        user = cursor.fetchone()
        user_db_id = user[0]

        cursor.execute('''
        SELECT id, name, amount, start_date, end_date, free_trial_end_date, category_id, notes, is_active
        FROM subscriptions
        WHERE id = ? AND user_id = ?
        ''', (subscription_id, user_db_id))

        subscription = cursor.fetchone()
        conn.close()

        if not subscription:
            await message.reply("Подписка с таким ID не найдена. Пожалуйста, введите корректный ID:")
            return

        sub_id, name, amount, start_date, end_date, free_trial_end_date, category_id, notes, is_active = subscription

        response = f"📝 Редактирование подписки: {name}\n\n"
        response += f"1. Название: {name}\n"
        response += f"2. Сумма: {amount} RUB/мес\n"
        response += f"3. Дата начала: {start_date}\n"
        response += f"4. Дата окончания: {end_date or 'Не указано'}\n"
        response += f"5. Бесплатный период: {free_trial_end_date or 'Нет'}\n"
        response += f"6. Категория: {category_id}\n"
        response += f"7. Заметки: {notes or 'Нет'}\n"
        response += f"8. Статус: {'Активна' if is_active else 'Неактивна'}\n\n"
        response += "Введите номер поля, которое хотите изменить (или 'отмена' для отмены):"

        async with state.proxy() as data:
            data['current_subscription'] = {
                'id': sub_id,
                'name': name,
                'amount': amount,
                'start_date': start_date,
                'end_date': end_date,
                'free_trial_end_date': free_trial_end_date,
                'category_id': category_id,
                'notes': notes,
                'is_active': is_active
            }

        await message.reply(response, reply_markup=get_back_keyboard())
        await SubscriptionEditStates.next()

    except ValueError:
        await message.reply("Пожалуйста, введите корректный ID подписки (число):")

@dp.message_handler(state=SubscriptionEditStates.editing_field)
async def process_edit_field(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад" or message.text.lower() == 'отмена':
        await state.finish()
        await message.reply("Редактирование отменено.", reply_markup=get_main_keyboard())
        return

    try:
        field_num = int(message.text)
        async with state.proxy() as data:
            data['field_num'] = field_num

            field_names = {
                1: 'name',
                2: 'amount',
                3: 'start_date',
                4: 'end_date',
                5: 'free_trial_end_date',
                6: 'category_id',
                7: 'notes',
                8: 'is_active'
            }

            if field_num not in field_names:
                await message.reply("Пожалуйста, введите номер от 1 до 8:")
                return

            field_name = field_names[field_num]
            data['field_name'] = field_name

            current_value = data['current_subscription'][field_name]
            if field_name == 'is_active':
                await message.reply(f"Текущее значение: {'Активна' if current_value else 'Неактивна'}\n"
                                  f"Введите новое значение (1 для активна, 0 для неактивна):")
            elif field_name == 'category_id':
                await message.reply(f"Текущая категория: {current_value}\n"
                                  f"Выберите новую категорию:", reply_markup=get_categories_keyboard())
            else:
                await message.reply(f"Текущее значение: {current_value}\n"
                                  f"Введите новое значение:")

        await SubscriptionEditStates.next()

    except ValueError:
        await message.reply("Пожалуйста, введите номер поля (число от 1 до 8):")

@dp.message_handler(state=SubscriptionEditStates.editing_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад" or message.text.lower() == 'отмена':
        await state.finish()
        await message.reply("Редактирование отменено.", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as data:
        field_name = data['field_name']
        subscription_id = data['subscription_id']

        if field_name == 'is_active':
            try:
                new_value = bool(int(message.text))
            except ValueError:
                await message.reply("Пожалуйста, введите 1 для активна или 0 для неактивна:")
                return
        elif field_name == 'category_id':
            if message.text.startswith('category_'):
                new_value = int(message.text.split('_')[1])
            else:
                await message.reply("Пожалуйста, выберите категорию из кнопок:")
                return
        elif field_name in ['amount']:
            try:
                new_value = float(message.text)
            except ValueError:
                await message.reply("Пожалуйста, введите корректное число:")
                return
        elif field_name in ['start_date', 'end_date', 'free_trial_end_date']:
            try:
                new_value = datetime.strptime(message.text, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                await message.reply("Пожалуйста, введите дату в формате ГГГГ-ММ-ДД:")
                return
        else:
            new_value = message.text

        # Обновляем подписку в базе данных
        conn = sqlite3.connect('db/subscriptions.db')
        cursor = conn.cursor()

        cursor.execute(f'''
        UPDATE subscriptions
        SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (new_value, subscription_id))

        conn.commit()
        conn.close()

        await state.finish()
        await message.reply(
            f"✅ Поле '{field_name}' успешно обновлено!\n"
            f"Новое значение: {new_value}",
            reply_markup=get_main_keyboard()
        )

# Обработчики для Premium функций
@dp.message_handler(lambda message: message.text == "💎 Premium")
async def show_premium_menu(message: types.Message):
    user_id = message.from_user.id
    is_premium, expiry_date = check_premium_status(user_id)

    if is_premium:
        premium_info = f"💎 Ваш Premium статус активен до: {expiry_date}\n\n"
        premium_info += "Спасибо за поддержку проекта! 🙏\n"
        premium_info += "Вы получаете доступ ко всем Premium функциям."

        await message.reply(premium_info, reply_markup=get_premium_keyboard())
    else:
        await message.reply(
            "💎 Premium функции доступны для подписчиков!\n\n"
            "Оформите Premium подписку, чтобы получить доступ к расширенным функциям.",
            reply_markup=get_premium_keyboard()
        )

@dp.message_handler(lambda message: message.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    user_id = message.from_user.id
    is_premium, _ = check_premium_status(user_id)

    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        await message.reply("Вы не зарегистрированы. Пожалуйста, начните с команды /start")
        return

    user_db_id = user[0]

    # Получаем общую сумму расходов
    cursor.execute('''
    SELECT SUM(amount)
    FROM subscriptions
    WHERE user_id = ? AND is_active = TRUE
    ''', (user_db_id,))

    total_expenses = cursor.fetchone()[0] or 0

    # Получаем количество активных подписок
    cursor.execute('''
    SELECT COUNT(*)
    FROM subscriptions
    WHERE user_id = ? AND is_active = TRUE
    ''', (user_db_id,))

    active_subscriptions = cursor.fetchone()[0]

    # Получаем ближайшие продления
    cursor.execute('''
    SELECT name, end_date
    FROM subscriptions
    WHERE user_id = ? AND is_active = TRUE AND end_date IS NOT NULL
    ORDER BY end_date
    LIMIT 3
    ''', (user_db_id,))

    upcoming_renewals = cursor.fetchall()

    conn.close()

    response = "📊 Ваша статистика\n\n"
    response += f"💰 Общие расходы: {total_expenses:.2f} RUB/мес\n"
    response += f"📋 Активных подписок: {active_subscriptions}\n\n"

    if upcoming_renewals:
        response += "📅 Ближайшие продления:\n"
        for name, end_date in upcoming_renewals:
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                days_left = (end - datetime.now()).days
                response += f"   • {name}: {end_date} ({days_left} дней осталось)\n"
        response += "\n"
    else:
        response += "📅 Нет предстоящих продлений подписок\n\n"

    if is_premium:
        # Для Premium пользователей показываем расширенную статистику
        analytics = get_premium_analytics(user_id)
        response += "\n💎 Premium Аналитика:\n" + analytics
    else:
        response += "💎 Оформите Premium, чтобы получить расширенную аналитику и дополнительные функции!"

    await message.reply(response, reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data == "premium_features")
async def show_premium_features(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        get_premium_features_message(),
        reply_markup=get_premium_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_premium(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    # В реальном приложении здесь будет интеграция с платежной системой
    # Для демонстрации просто активируем Premium на 1 месяц
    expiry_date = activate_premium(user_id, months=1)

    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"🎉 Поздравляем! Вы оформили Premium подписку!\n\n"
        f"💎 Ваш Premium статус активен до: {expiry_date}\n\n"
        f"Теперь вы получаете доступ ко всем Premium функциям:\n"
        f"✅ Неограниченное количество подписок\n"
        f"✅ Расширенные виджеты и графики\n"
        f"✅ Экспорт данных\n"
        f"✅ Приоритетные уведомления\n"
        f"✅ Нет рекламы\n\n"
        f"Спасибо за поддержку проекта! 🙏",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda message: message.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    await message.reply(
        "⚙️ Настройки\n\n"
        "Здесь вы можете настроить:\n"
        "🔔 Уведомления о подписках\n"
        "🌙 Темную тему\n"
        "🌍 Язык интерфейса\n\n"
        "Эти функции будут реализованы в следующих версиях.",
        reply_markup=get_main_keyboard()
    )

# Обработчик для неизвестных сообщений
@dp.message_handler()
async def handle_unknown_message(message: types.Message):
    await message.reply("Извините, я не понял ваше сообщение. Пожалуйста, используйте меню.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
