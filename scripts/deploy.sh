#!/bin/bash

# Скрипт для деплоя Telegram бота на VPS
# Использование: ./deploy.sh

# Останавливаем текущий бот, если он запущен
echo "Останавливаем текущий бот..."
pkill -f "python.*main.py" || echo "Бот не был запущен"

# Обновляем систему
echo "Обновляем систему..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Устанавливаем необходимые зависимости
echo "Устанавливаем зависимости..."
sudo apt-get install -y python3 python3-pip python3-venv sqlite3 nginx certbot python3-certbot-nginx

# Создаем виртуальное окружение
echo "Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Устанавливаем Python зависимости
echo "Устанавливаем Python зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

# Инициализируем базу данных
echo "Инициализируем базу данных..."
python db/init_db.py

# Создаем директорию для логов
echo "Создаем директорию для логов..."
mkdir -p logs

# Создаем systemd сервис для бота
echo "Создаем systemd сервис..."
sudo tee /etc/systemd/system/subscription-bot.service > /dev/null <<EOL
[Unit]
Description=Subscription Organizer Telegram Bot
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python $(pwd)/bot/main.py
Restart=always
RestartSec=5
StandardOutput=append:$(pwd)/logs/bot.log
StandardError=append:$(pwd)/logs/bot.error.log

[Install]
WantedBy=multi-user.target
EOL

# Перезагружаем systemd и запускаем сервис
echo "Перезагружаем systemd и запускаем сервис..."
sudo systemctl daemon-reload
sudo systemctl enable subscription-bot
sudo systemctl start subscription-bot

# Настраиваем Nginx для веб-приложения
echo "Настраиваем Nginx..."
sudo tee /etc/nginx/sites-available/subscription-bot > /dev/null <<EOL
server {
    listen 80;
    server_name panel-bruhxax.ru;

    location / {
        root $(pwd)/web_app;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /static/ {
        alias $(pwd)/web_app/static/;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOL

# Включаем сайт и перезапускаем Nginx
echo "Включаем сайт и перезапускаем Nginx..."
sudo ln -s /etc/nginx/sites-available/subscription-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Настраиваем SSL с помощью Certbot
echo "Настраиваем SSL сертификат..."
sudo certbot --nginx -d panel-bruhxax.ru --non-interactive --agree-tos -m admin@panel-bruhxax.ru

# Создаем скрипт для обновления
echo "Создаем скрипт для обновления..."
sudo tee /usr/local/bin/update-bot > /dev/null <<EOL
#!/bin/bash
cd $(pwd)
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart subscription-bot
sudo systemctl restart nginx
EOL

sudo chmod +x /usr/local/bin/update-bot

# Выводим информацию о завершении
echo ""
echo "🎉 Деплой завершен успешно!"
echo ""
echo "Бот запущен и работает."
echo "Веб-приложение доступно по адресу: https://panel-bruhxax.ru"
echo ""
echo "Команды для управления:"
echo "  - sudo systemctl status subscription-bot  (просмотр статуса бота)"
echo "  - sudo systemctl restart subscription-bot (перезапуск бота)"
echo "  - sudo tail -f logs/bot.log            (просмотр логов)"
echo "  - update-bot                           (обновление бота)"
echo ""
