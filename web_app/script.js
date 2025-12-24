document.addEventListener('DOMContentLoaded', function() {
    // Инициализация Telegram Web App
    const tg = window.Telegram.WebApp;

    // Проверяем, доступен ли Telegram Web App
    if (tg) {
        tg.expand();
        tg.ready();

        // Получаем информацию о пользователе
        const user = tg.initDataUnsafe.user;
        if (user) {
            document.getElementById('user-name').textContent = user.first_name || 'Пользователь';

            // Проверяем Premium статус (в реальном приложении это будет проверяться на сервере)
            if (user.id && [123456789, 987654321].includes(user.id)) {
                const premiumBadge = document.createElement('span');
                premiumBadge.className = 'premium-badge';
                premiumBadge.textContent = 'PREMIUM';
                document.querySelector('.user-info').appendChild(premiumBadge);
            }
        }
    }

    // Переключение темы
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Проверяем сохраненные настройки темы
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
        themeToggle.textContent = '☀️';
    }

    themeToggle.addEventListener('click', function() {
        body.classList.toggle('dark-theme');
        const isDark = body.classList.contains('dark-theme');
        themeToggle.textContent = isDark ? '☀️' : '🌙';
        localStorage.setItem('theme', isDark ? 'dark' : 'light');

        // Сообщаем Telegram об изменении темы
        if (tg) {
            tg.setBackgroundColor(isDark ? '#121212' : '#f5f5f5');
            tg.setHeaderColor(isDark ? '#1e1e1e' : '#ffffff');
        }
    });

    // Модальные окна
    const addSubscriptionBtn = document.getElementById('add-subscription-btn');
    const addSubscriptionModal = document.getElementById('add-subscription-modal');
    const closeModal = document.getElementById('close-modal');
    const closeEditModal = document.getElementById('close-edit-modal');
    const editSubscriptionModal = document.getElementById('edit-subscription-modal');

    // Открытие модального окна добавления подписки
    addSubscriptionBtn.addEventListener('click', function() {
        addSubscriptionModal.style.display = 'flex';
        document.getElementById('subscription-start-date').valueAsDate = new Date();
    });

    // Закрытие модальных окон
    closeModal.addEventListener('click', function() {
        addSubscriptionModal.style.display = 'none';
    });

    closeEditModal.addEventListener('click', function() {
        editSubscriptionModal.style.display = 'none';
    });

    // Закрытие по клику вне модального окна
    window.addEventListener('click', function(event) {
        if (event.target === addSubscriptionModal) {
            addSubscriptionModal.style.display = 'none';
        }
        if (event.target === editSubscriptionModal) {
            editSubscriptionModal.style.display = 'none';
        }
    });

    // Обработка формы добавления подписки
    const subscriptionForm = document.getElementById('subscription-form');
    subscriptionForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const subscriptionData = {
            name: document.getElementById('subscription-name').value,
            amount: parseFloat(document.getElementById('subscription-amount').value),
            start_date: document.getElementById('subscription-start-date').value,
            end_date: document.getElementById('subscription-end-date').value || null,
            free_trial_end_date: document.getElementById('subscription-free-trial').value || null,
            category_id: parseInt(document.getElementById('subscription-category').value),
            notes: document.getElementById('subscription-notes').value || null,
            is_active: document.getElementById('subscription-active').checked
        };

        // В реальном приложении здесь будет отправка данных на сервер
        console.log('Добавление подписки:', subscriptionData);

        // Добавляем подписку в интерфейс
        addSubscriptionToUI(subscriptionData);

        // Сбрасываем форму и закрываем модальное окно
        subscriptionForm.reset();
        addSubscriptionModal.style.display = 'none';

        // Обновляем статистику
        updateStatistics();

        // Показываем уведомление
        showNotification('Подписка успешно добавлена!', 'success');
    });

    // Функция для добавления подписки в интерфейс
    function addSubscriptionToUI(subscription) {
        const subscriptionsList = document.getElementById('subscriptions-list');

        // Удаляем сообщение о пустом состоянии, если оно есть
        const emptyState = subscriptionsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Создаем карточку подписки
        const subscriptionCard = document.createElement('div');
        subscriptionCard.className = 'subscription-card';

        // Проверяем статус подписки
        if (subscription.free_trial_end_date) {
            const trialEnd = new Date(subscription.free_trial_end_date);
            const today = new Date();
            const daysLeft = Math.ceil((trialEnd - today) / (1000 * 60 * 60 * 24));

            if (daysLeft <= 0) {
                subscriptionCard.classList.add('expired');
            } else if (daysLeft <= 3) {
                subscriptionCard.classList.add('expiring-soon');
            } else {
                subscriptionCard.classList.add('free-trial-active');
            }
        } else if (subscription.end_date) {
            const endDate = new Date(subscription.end_date);
            const today = new Date();
            const daysLeft = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));

            if (daysLeft <= 0) {
                subscriptionCard.classList.add('expired');
            } else if (daysLeft <= 3) {
                subscriptionCard.classList.add('expiring-soon');
            }
        }

        // Форматируем даты для отображения
        const formatDate = (dateString) => {
            if (!dateString) return 'Не указано';
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU');
        };

        // Создаем HTML для карточки
        subscriptionCard.innerHTML = `
            <div class="subscription-header">
                <div class="subscription-name">${subscription.name}</div>
                <div class="subscription-status ${subscription.is_active ? 'active' : 'inactive'}">
                    ${subscription.is_active ? '✅ Активна' : '❌ Неактивна'}
                </div>
            </div>
            <div class="subscription-details">
                <div class="detail-item">
                    <div class="detail-label">💰 Сумма</div>
                    <div class="detail-value">${subscription.amount} RUB/мес</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">📅 Начало</div>
                    <div class="detail-value">${formatDate(subscription.start_date)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">📅 Окончание</div>
                    <div class="detail-value">${formatDate(subscription.end_date)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">🎁 Бесплатный период</div>
                    <div class="detail-value">${formatDate(subscription.free_trial_end_date)}</div>
                </div>
            </div>
            <div class="subscription-actions">
                <button class="action-btn edit-btn" data-id="${Date.now()}">Редактировать</button>
                <button class="action-btn delete-btn" data-id="${Date.now()}">Удалить</button>
            </div>
        `;

        subscriptionsList.appendChild(subscriptionCard);

        // Добавляем обработчики событий для кнопок
        const editBtn = subscriptionCard.querySelector('.edit-btn');
        const deleteBtn = subscriptionCard.querySelector('.delete-btn');

        editBtn.addEventListener('click', function() {
            openEditModal(subscription, this.dataset.id);
        });

        deleteBtn.addEventListener('click', function() {
            deleteSubscription(this.dataset.id, subscriptionCard);
        });
    }

    // Функция для открытия модального окна редактирования
    function openEditModal(subscription, id) {
        // Заполняем форму данными подписки
        document.getElementById('edit-subscription-id').value = id;
        document.getElementById('edit-subscription-name').value = subscription.name;
        document.getElementById('edit-subscription-amount').value = subscription.amount;
        document.getElementById('edit-subscription-start-date').value = subscription.start_date;
        document.getElementById('edit-subscription-end-date').value = subscription.end_date || '';
        document.getElementById('edit-subscription-free-trial').value = subscription.free_trial_end_date || '';
        document.getElementById('edit-subscription-category').value = subscription.category_id;
        document.getElementById('edit-subscription-notes').value = subscription.notes || '';
        document.getElementById('edit-subscription-active').checked = subscription.is_active;

        // Открываем модальное окно
        editSubscriptionModal.style.display = 'flex';
    }

    // Обработка формы редактирования подписки
    const editSubscriptionForm = document.getElementById('edit-subscription-form');
    editSubscriptionForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const subscriptionId = document.getElementById('edit-subscription-id').value;
        const updatedSubscription = {
            name: document.getElementById('edit-subscription-name').value,
            amount: parseFloat(document.getElementById('edit-subscription-amount').value),
            start_date: document.getElementById('edit-subscription-start-date').value,
            end_date: document.getElementById('edit-subscription-end-date').value || null,
            free_trial_end_date: document.getElementById('edit-subscription-free-trial').value || null,
            category_id: parseInt(document.getElementById('edit-subscription-category').value),
            notes: document.getElementById('edit-subscription-notes').value || null,
            is_active: document.getElementById('edit-subscription-active').checked
        };

        // В реальном приложении здесь будет отправка данных на сервер
        console.log('Обновление подписки:', subscriptionId, updatedSubscription);

        // Обновляем подписку в интерфейсе
        updateSubscriptionInUI(subscriptionId, updatedSubscription);

        // Сбрасываем форму и закрываем модальное окно
        editSubscriptionForm.reset();
        editSubscriptionModal.style.display = 'none';

        // Обновляем статистику
        updateStatistics();

        // Показываем уведомление
        showNotification('Подписка успешно обновлена!', 'success');
    });

    // Функция для обновления подписки в интерфейсе
    function updateSubscriptionInUI(id, updatedSubscription) {
        const subscriptionCard = document.querySelector(`.subscription-card .edit-btn[data-id="${id}"]`).closest('.subscription-card');

        if (subscriptionCard) {
            // Обновляем данные в карточке
            subscriptionCard.querySelector('.subscription-name').textContent = updatedSubscription.name;
            subscriptionCard.querySelector('.subscription-status').textContent =
                updatedSubscription.is_active ? '✅ Активна' : '❌ Неактивна';
            subscriptionCard.querySelector('.subscription-status').className =
                `subscription-status ${updatedSubscription.is_active ? 'active' : 'inactive'}`;

            const details = subscriptionCard.querySelectorAll('.detail-value');
            details[0].textContent = `${updatedSubscription.amount} RUB/мес`;
            details[1].textContent = formatDate(updatedSubscription.start_date);
            details[2].textContent = formatDate(updatedSubscription.end_date);
            details[3].textContent = formatDate(updatedSubscription.free_trial_end_date);

            // Обновляем классы для предупреждений
            subscriptionCard.className = 'subscription-card';
            if (updatedSubscription.free_trial_end_date) {
                const trialEnd = new Date(updatedSubscription.free_trial_end_date);
                const today = new Date();
                const daysLeft = Math.ceil((trialEnd - today) / (1000 * 60 * 60 * 24));

                if (daysLeft <= 0) {
                    subscriptionCard.classList.add('expired');
                } else if (daysLeft <= 3) {
                    subscriptionCard.classList.add('expiring-soon');
                } else {
                    subscriptionCard.classList.add('free-trial-active');
            }
            } else if (updatedSubscription.end_date) {
                const endDate = new Date(updatedSubscription.end_date);
                const today = new Date();
                const daysLeft = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));

                if (daysLeft <= 0) {
                    subscriptionCard.classList.add('expired');
                } else if (daysLeft <= 3) {
                    subscriptionCard.classList.add('expiring-soon');
                }
            }
        }
    }

    // Функция для форматирования даты
    function formatDate(dateString) {
        if (!dateString) return 'Не указано';
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU');
    }

    // Функция для удаления подписки
    function deleteSubscription(id, cardElement) {
        if (confirm('Вы уверены, что хотите удалить эту подписку?')) {
            // В реальном приложении здесь будет отправка запроса на сервер
            console.log('Удаление подписки:', id);

            // Удаляем карточку из интерфейса
            cardElement.remove();

            // Обновляем статистику
            updateStatistics();

            // Показываем уведомление
            showNotification('Подписка успешно удалена!', 'success');

            // Если больше нет подписок, показываем сообщение о пустом состоянии
            const subscriptionsList = document.getElementById('subscriptions-list');
            if (subscriptionsList.children.length === 0) {
                const emptyState = document.createElement('div');
                emptyState.className = 'empty-state';
                emptyState.innerHTML = '<p>У вас пока нет подписок. Нажмите "Добавить подписку", чтобы начать.</p>';
                subscriptionsList.appendChild(emptyState);
            }
        }
    }

    // Обработчик для кнопки удаления в модальном окне редактирования
    document.getElementById('delete-subscription-btn').addEventListener('click', function() {
        const subscriptionId = document.getElementById('edit-subscription-id').value;
        const subscriptionCard = document.querySelector(`.subscription-card .edit-btn[data-id="${subscriptionId}"]`).closest('.subscription-card');

        if (subscriptionCard) {
            deleteSubscription(subscriptionId, subscriptionCard);
            editSubscriptionModal.style.display = 'none';
        }
    });

    // Функция для обновления статистики
    function updateStatistics() {
        const subscriptionCards = document.querySelectorAll('.subscription-card');
        let totalExpenses = 0;
        let upcomingRenewals = 0;
        let freeTrials = 0;

        const today = new Date();

        subscriptionCards.forEach(card => {
            const amountText = card.querySelector('.detail-value').textContent;
            const amount = parseFloat(amountText);
            if (!isNaN(amount)) {
                totalExpenses += amount;
            }

            // Проверяем ближайшие продления
            const endDateText = card.querySelectorAll('.detail-value')[2].textContent;
            if (endDateText !== 'Не указано') {
                const endDate = new Date(endDateText.split('.').reverse().join('-'));
                const daysLeft = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
                if (daysLeft >= 0 && daysLeft <= 7) {
                    upcomingRenewals++;
                }
            }

            // Проверяем бесплатные периоды
            const trialDateText = card.querySelectorAll('.detail-value')[3].textContent;
            if (trialDateText !== 'Не указано') {
                const trialEndDate = new Date(trialDateText.split('.').reverse().join('-'));
                if (trialEndDate > today) {
                    freeTrials++;
                }
            }
        });

        document.getElementById('total-expenses').textContent = `${totalExpenses.toFixed(2)} RUB/мес`;
        document.getElementById('upcoming-renewals').textContent = `${upcomingRenewals} подписок`;
        document.getElementById('free-trials').textContent = `${freeTrials} активных`;
    }

    // Функция для показа уведомлений
    function showNotification(message, type) {
        // В реальном приложении это будет интеграция с Telegram уведомлениями
        if (tg) {
            tg.showAlert(message);
        } else {
            alert(message);
        }
    }

    // Инициализация фильтров и сортировки
    const categoryFilter = document.getElementById('category-filter');
    const sortBy = document.getElementById('sort-by');

    categoryFilter.addEventListener('change', filterSubscriptions);
    sortBy.addEventListener('change', sortSubscriptions);

    function filterSubscriptions() {
        const category = categoryFilter.value;
        const subscriptionCards = document.querySelectorAll('.subscription-card');

        subscriptionCards.forEach(card => {
            // В реальном приложении здесь будет фильтрация по категории
            // Для демонстрации просто показываем все карточки
            card.style.display = 'block';
        });
    }

    function sortSubscriptions() {
        const sortOption = sortBy.value;
        const subscriptionsList = document.getElementById('subscriptions-list');
        const subscriptionCards = Array.from(subscriptionsList.querySelectorAll('.subscription-card'));

        // Удаляем пустое состояние, если оно есть
        const emptyState = subscriptionsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Сортируем карточки
        subscriptionCards.sort((a, b) => {
            if (sortOption === 'name') {
                const nameA = a.querySelector('.subscription-name').textContent.toLowerCase();
                const nameB = b.querySelector('.subscription-name').textContent.toLowerCase();
                return nameA.localeCompare(nameB);
            } else if (sortOption === 'amount') {
                const amountA = parseFloat(a.querySelector('.detail-value').textContent);
                const amountB = parseFloat(b.querySelector('.detail-value').textContent);
                return amountA - amountB;
            } else { // по дате окончания
                const dateAText = a.querySelectorAll('.detail-value')[2].textContent;
                const dateBText = b.querySelectorAll('.detail-value')[2].textContent;

                if (dateAText === 'Не указано' && dateBText === 'Не указано') return 0;
                if (dateAText === 'Не указано') return 1;
                if (dateBText === 'Не указано') return -1;

                const dateA = new Date(dateAText.split('.').reverse().join('-'));
                const dateB = new Date(dateBText.split('.').reverse().join('-'));
                return dateA - dateB;
            }
        });

        // Очищаем список и добавляем отсортированные карточки
        subscriptionsList.innerHTML = '';
        subscriptionCards.forEach(card => subscriptionsList.appendChild(card));

        // Если нет карточек, показываем пустое состояние
        if (subscriptionCards.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.innerHTML = '<p>У вас пока нет подписок. Нажмите "Добавить подписку", чтобы начать.</p>';
            subscriptionsList.appendChild(emptyState);
        }
    }

    // Инициализация с тестовыми данными (для демонстрации)
    if (document.getElementById('subscriptions-list').querySelector('.empty-state')) {
        // Добавим несколько тестовых подписок для демонстрации
        const testSubscriptions = [
            {
                name: "Netflix",
                amount: 599,
                start_date: "2023-11-01",
                end_date: "2024-01-15",
                free_trial_end_date: null,
                category_id: 1,
                notes: "Семейный аккаунт",
                is_active: true
            },
            {
                name: "Spotify Premium",
                amount: 169,
                start_date: "2023-10-10",
                end_date: "2023-12-10",
                free_trial_end_date: null,
                category_id: 1,
                notes: "Студенческая скидка",
                is_active: true
            },
            {
                name: "NordVPN",
                amount: 299,
                start_date: "2023-11-20",
                end_date: "2025-11-20",
                free_trial_end_date: "2023-11-27",
                category_id: 4,
                notes: "2-летняя подписка",
                is_active: true
            }
        ];

        testSubscriptions.forEach(sub => addSubscriptionToUI(sub));
        updateStatistics();
    }

    // Проверка Premium статуса и ограничений
    function checkPremiumStatus() {
        // В реальном приложении это будет проверяться на сервере
        const isPremium = document.querySelector('.premium-badge') !== null;
        const subscriptionCount = document.querySelectorAll('.subscription-card').length;

        if (!isPremium && subscriptionCount >= 5) {
            addSubscriptionBtn.disabled = true;
            addSubscriptionBtn.textContent = '🔒 Достигнут лимит (5/5)';
            addSubscriptionBtn.title = 'Оформите Premium, чтобы добавлять неограниченное количество подписок';

            // Показываем уведомление о Premium
            if (tg) {
                tg.showPopup({
                    title: 'Оформите Premium',
                    message: 'Вы достигли лимита в 5 подписок. Оформите Premium, чтобы добавлять неограниченное количество подписок и получить доступ к дополнительным функциям!',
                    buttons: [
                        { type: 'default', text: 'Позже' },
                        { type: 'default', text: 'Узнать больше', id: 'premium_info' }
                    ]
                }, function(buttonId) {
                    if (buttonId === 'premium_info') {
                        // Перенаправляем на информацию о Premium
                        if (tg) {
                            tg.sendData(JSON.stringify({ action: 'show_premium_info' }));
                        }
                    }
                });
            }
        }
    }

    // Проверяем Premium статус при загрузке
    checkPremiumStatus();

    // Добавляем обработчик для кнопки Premium в главном меню
    // (В реальном приложении это будет в боте)
    console.log('Telegram Web App initialized. Ready to use!');
});
