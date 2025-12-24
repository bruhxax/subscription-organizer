"""
Модуль уведомлений для бота управления подписками
Автоматическая отправка уведомлений о продлении подписок
"""
import asyncio
import logging
from datetime import datetime
from aiogram import Bot

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Bot, db):
        """Инициализация сервиса уведомлений"""
        self.bot = bot
        self.db = db
        self.is_running = False
    
    async def start(self):
        """Запустить сервис уведомлений"""
        self.is_running = True
        logger.info("Notification service started")
        
        while self.is_running:
            try:
                await self.check_and_send_notifications()
                # Проверять каждые 5 минут
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Error in notification service: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Остановить сервис уведомлений"""
        self.is_running = False
        logger.info("Notification service stopped")
    
    async def check_and_send_notifications(self):
        """Проверить и отправить неотправленные уведомления"""
        notifications = self.db.get_pending_notifications()
        
        for notification in notifications:
            try:
                await self.send_notification(notification)
                self.db.mark_notification_sent(notification['id'])
            except Exception as e:
                logger.error(f"Error sending notification {notification['id']}: {e}")
    
    async def send_notification(self, notification: dict):
        """Отправить уведомление пользователю"""
        user_id = notification['user_id']
        subscription_name = notification['subscription_name']
        price = notification['price']
        notification_type = notification['notification_type']
        language = notification.get('language', 'ru')
        
        if notification_type == 'renewal':
            # Уведомление о продлении
            if language == 'ru':
                text = f"""🔔 Напоминание о продлении подписки

💳 Подписка: {subscription_name}
💰 Сумма: ${price}
📅 Скоро спишутся средства

Не забудьте проверить баланс!"""
            else:
                text = f"""🔔 Subscription renewal reminder

💳 Subscription: {subscription_name}
💰 Amount: ${price}
📅 Funds will be debited soon

Don't forget to check your balance!"""
        
        elif notification_type == 'trial_end':
            # Уведомление об окончании пробного периода
            if language == 'ru':
                text = f"""⏰ Окончание пробного периода

💳 Подписка: {subscription_name}
💰 После окончания пробного периода будет списано: ${price}

Если вы не хотите продолжать, отмените подписку!"""
            else:
                text = f"""⏰ Trial period ending

💳 Subscription: {subscription_name}
💰 After trial ends, you will be charged: ${price}

If you don't want to continue, cancel the subscription!"""
        
        else:
            # Общее уведомление
            if language == 'ru':
                text = f"""📢 Уведомление

💳 Подписка: {subscription_name}"""
            else:
                text = f"""📢 Notification

💳 Subscription: {subscription_name}"""
        
        try:
            await self.bot.send_message(user_id, text)
            logger.info(f"Notification sent to user {user_id} for subscription {subscription_name}")
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            raise
