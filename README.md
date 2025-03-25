# Telegram Website Parser Bot

Этот бот позволяет парсить веб-сайты через Telegram.

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте бота в Telegram:
   - Откройте [@BotFather](https://t.me/botfather)
   - Отправьте команду `/newbot`
   - Следуйте инструкциям для создания бота
   - Скопируйте полученный токен

4. Настройте переменные окружения:
   - Откройте файл `.env`
   - Замените `your_bot_token_here` на ваш токен бота

## Запуск

```bash
python bot.py
```

## Использование

1. Откройте вашего бота в Telegram
2. Отправьте команду `/start` для начала работы
3. Используйте команду `/parse <url>` для парсинга сайта
   Пример: `/parse https://example.com`

## Функциональность

Бот парсит следующие элементы сайта:
- Заголовок страницы
- Заголовки (h1-h3)
- Ссылки (первые 5)

## Настройка парсинга

Вы можете настроить парсинг под свои нужды, отредактировав файл `parser.py`. 