import sqlite3
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.config import PREMIUM_PRICE_MONTHLY, MAX_FREE_SUBSCRIPTIONS

def check_premium_status(user_id):
    """Проверка Premium статуса пользователя"""
    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT is_premium, premium_expiry_date
    FROM users
    WHERE telegram_id = ?
    ''', (user_id,))

    result = cursor.fetchone()
    conn.close()

    if not result:
        return False, None

    is_premium, expiry_date = result

    if not is_premium:
        return False, None

    if expiry_date:
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        if expiry < datetime.now():
            # Premium истек
            return False, None

    return True, expiry_date

def get_premium_keyboard():
    """Создание клавиатуры для Premium функций"""
    keyboard = InlineKeyboardMarkup()

    # Кнопка для покупки Premium
    keyboard.add(InlineKeyboardButton(
        f"💎 Оформить Premium ({PREMIUM_PRICE_MONTHLY}$/мес)",
        callback_data="buy_premium"
    ))

    # Кнопки с информацией о Premium
    keyboard.add(InlineKeyboardButton(
        "📋 Что входит в Premium?",
        callback_data="premium_features"
    ))

    keyboard.add(InlineKeyboardButton(
        "⬅️ Назад",
        callback_data="back_to_main"
    ))

    return keyboard

def get_premium_features_message():
    """Сообщение с информацией о Premium функциях"""
    return (
        "💎 Premium функции:\n\n"
        "✅ Неограниченное количество подписок (в бесплатной версии до 5)\n"
        "✅ Расширенные виджеты и графики расходов\n"
        "✅ Возможность экспорта данных (CSV, PDF)\n"
        "✅ Приоритетные уведомления\n"
        "✅ Ранний доступ к новым функциям\n"
        "✅ Нет рекламы\n"
        "✅ Поддержка 24/7\n\n"
        f"Всего за {PREMIUM_PRICE_MONTHLY}$ в месяц!"
    )

def check_subscription_limit(user_id):
    """Проверка лимита подписок для бесплатных пользователей"""
    is_premium, _ = check_premium_status(user_id)

    if is_premium:
        return True, None  # Нет ограничений для Premium

    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "Пользователь не найден"

    user_db_id = user[0]

    cursor.execute('''
    SELECT COUNT(*)
    FROM subscriptions
    WHERE user_id = ?
    ''', (user_db_id,))

    count = cursor.fetchone()[0]
    conn.close()

    if count >= MAX_FREE_SUBSCRIPTIONS:
        return False, f"Вы достигли лимита в {MAX_FREE_SUBSCRIPTIONS} подписок. Оформите Premium для неограниченного количества."

    return True, None

def activate_premium(user_id, months=1):
    """Активация Premium статуса для пользователя"""
    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    expiry_date = (datetime.now() + timedelta(days=30*months)).strftime('%Y-%m-%d')

    cursor.execute('''
    UPDATE users
    SET is_premium = TRUE, premium_expiry_date = ?
    WHERE telegram_id = ?
    ''', (expiry_date, user_id))

    conn.commit()
    conn.close()

    return expiry_date

def get_premium_stats(user_id):
    """Получение статистики для Premium пользователей"""
    is_premium, expiry_date = check_premium_status(user_id)

    if not is_premium:
        return None

    conn = sqlite3.connect('db/subscriptions.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return None

    user_db_id = user[0]

    # Получаем общую сумму расходов
    cursor.execute('''
    SELECT SUM(amount)
    FROM subscriptions
    WHERE user_id = ? AND is_active = TRUE
    ''', (user_db_id,))

    total_expenses = cursor.fetchone()[0] or 0

    # Получаем расходы по категориям
    cursor.execute('''
    SELECT c.name, SUM(s.amount)
    FROM subscriptions s
    JOIN categories c ON s.category_id = c.id
    WHERE s.user_id = ? AND s.is_active = TRUE
    GROUP BY c.name
    ''', (user_db_id,))

    category_expenses = cursor.fetchall()

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

    return {
        'is_premium': True,
        'expiry_date': expiry_date,
        'total_expenses': total_expenses,
        'category_expenses': category_expenses,
        'upcoming_renewals': upcoming_renewals
    }

def get_premium_analytics(user_id):
    """Получение расширенной аналитики для Premium пользователей"""
    stats = get_premium_stats(user_id)

    if not stats:
        return "Вы не являетесь Premium пользователем или у вас нет активных подписок."

    response = "📊 Premium Аналитика\n\n"

    # Общая сумма расходов
    response += f"💰 Общие расходы: {stats['total_expenses']:.2f} RUB/мес\n\n"

    # Расходы по категориям
    response += "📋 Расходы по категориям:\n"
    for category, amount in stats['category_expenses']:
        percentage = (amount / stats['total_expenses']) * 100 if stats['total_expenses'] > 0 else 0
        response += f"   • {category}: {amount:.2f} RUB ({percentage:.1f}%)\n"
    response += "\n"

    # Ближайшие продления
    response += "📅 Ближайшие продления:\n"
    if stats['upcoming_renewals']:
        for name, end_date in stats['upcoming_renewals']:
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                days_left = (end - datetime.now()).days
                response += f"   • {name}: {end_date} ({days_left} дней осталось)\n"
    else:
        response += "   Нет предстоящих продлений\n"
    response += "\n"

    # Информация о Premium
    response += f"💎 Ваш Premium статус активен до: {stats['expiry_date']}\n"

    return response

def create_payment_invoice(user_id, payment_system='stripe'):
    """Создание счета для оплаты Premium"""
    # В реальном приложении здесь будет интеграция с платежными системами
    # Для демонстрации вернем фиктивные данные

    return {
        'success': True,
        'payment_url': f'https://payment.example.com/invoice/{user_id}',
        'amount': PREMIUM_PRICE_MONTHLY,
        'currency': 'USD',
        'description': f'Premium подписка на 1 месяц ({PREMIUM_PRICE_MONTHLY}$)'
    }
