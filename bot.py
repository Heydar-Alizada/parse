import os
import logging
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from dotenv import load_dotenv
from parser import parse_website
from datetime import datetime
import pytz
import json
import requests
from io import BytesIO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Get your bot token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Check if token is loaded
if not TOKEN:
    raise ValueError("Не найден токен бота! Проверьте файл .env")

# Файл для хранения URL
URLS_FILE = 'urls.json'

# Файл для хранения фильтров
FILTERS_FILE = 'filters.json'

# Значения URL по умолчанию
DEFAULT_URLS = {
    'tap_az': "https://tap.az/elanlar/dasinmaz-emlak/menziller",
    'bina_az': "https://bina.az/baki/kiraye/menziller"
}

# Глобальные переменные для хранения данных пользователей
user_data = {}

def trim_sent_ads(user_id: int) -> None:
    """Ограничивает размер списка отправленных объявлений"""
    user_data_dict = user_data[user_id]
    if 'sent_ads' in user_data_dict and len(user_data_dict['sent_ads']) > 100:
        print(f"Очистка истории для пользователя {user_id}: удаляем {len(user_data_dict['sent_ads']) - 80} старых записей")
        # Оставляем только последние 2 записи
        user_data_dict['sent_ads'] = user_data_dict['sent_ads'][-80:]
        print(f"После очистки: {len(user_data_dict['sent_ads'])} записей")

def get_user_data(user_id: int) -> dict:
    """Get user data from file"""
    if user_id not in user_data:
        try:
            # Пробуем загрузить существующие данные из файла
            if os.path.exists('users.json'):
                with open('users.json', 'r', encoding='utf-8') as f:
                    all_users = json.load(f)
                    if str(user_id) in all_users:
                        user_data[user_id] = all_users[str(user_id)]
                        print(f"Загружены данные пользователя {user_id}")
                        # Проверяем размер истории и обрезаем при необходимости
                        if 'sent_ads' in user_data[user_id] and len(user_data[user_id]['sent_ads']) > 10:
                            trim_sent_ads(user_id)
                            save_user_data(user_id)
                    else:
                        # Если пользователя нет, создаем новую структуру данных
                        user_data[user_id] = {
                            'urls': DEFAULT_URLS.copy(),
                            'filters': {
                                'title': [],
                                'location': []
                            },
                            'sent_ads': [],
                            'auto_check': {
                                'enabled': False,
                                'interval': 300  # значение по умолчанию - 5 минут
                            }
                        }
                        print(f"Создана новая структура данных для пользователя {user_id}")
            else:
                # Если файла нет, создаем новую структуру данных
                user_data[user_id] = {
                    'urls': DEFAULT_URLS.copy(),
                    'filters': {
                        'title': [],
                        'location': []
                    },
                    'sent_ads': [],
                    'auto_check': {
                        'enabled': False,
                        'interval': 300  # значение по умолчанию - 5 минут
                    }
                }
                print(f"Создана новая структура данных для пользователя {user_id}")
        except Exception as e:
            print(f"Ошибка при загрузке данных пользователя {user_id}: {str(e)}")
            user_data[user_id] = {
                'urls': DEFAULT_URLS.copy(),
                'filters': {
                    'title': [],
                    'location': []
                },
                'sent_ads': [],
                'auto_check': {
                    'enabled': False,
                    'interval': 300  # значение по умолчанию - 5 минут
                }
            }
    return user_data[user_id]

def save_user_data(user_id: int):
    """Save user data to file"""
    try:
        print(f"== НАЧАЛО СОХРАНЕНИЯ ДАННЫХ для пользователя {user_id} ==")
        # Проверим, что данные пользователя существуют в user_data
        if user_id not in user_data:
            print(f"ERROR: user_id {user_id} отсутствует в user_data!")
            return
            
        # Проверка ключей в user_data[user_id]
        if 'sent_ads' not in user_data[user_id]:
            print(f"ERROR: 'sent_ads' отсутствует в user_data[{user_id}]!")
            return
            
        # Информация о sent_ads перед сохранением
        sent_ads = user_data[user_id]['sent_ads']
        print(f"Сохраняем sent_ads, количество: {len(sent_ads)}")
        if sent_ads:
            print(f"Первые 3 записи: {sent_ads[:3]}")
        
        # Загружаем все существующие данные
        all_users = {}
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                all_users = json.load(f)
                print(f"Загружен users.json, пользователей: {len(all_users)}")
        else:
            print("Файл users.json не найден, будет создан новый файл")
        
        # Обновляем данные текущего пользователя
        all_users[str(user_id)] = user_data[user_id]
        
        # Проверка, присутствуют ли данные в all_users
        if str(user_id) in all_users:
            if 'sent_ads' in all_users[str(user_id)]:
                print(f"Проверка: {len(all_users[str(user_id)]['sent_ads'])} записей в all_users")
            else:
                print("ERROR: 'sent_ads' отсутствует в all_users после обновления!")
        else:
            print(f"ERROR: {user_id} отсутствует в all_users после обновления!")
        
        # Сохраняем все данные
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(all_users, f, ensure_ascii=False, indent=2)
            print(f"Данные записаны в users.json")
        
        # Проверяем, что данные действительно сохранились
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                check_data = json.load(f)
                if str(user_id) in check_data:
                    if 'sent_ads' in check_data[str(user_id)]:
                        saved_count = len(check_data[str(user_id)]['sent_ads'])
                        print(f"Проверка после сохранения: {saved_count} записей")
                        if saved_count != len(sent_ads):
                            print(f"ВНИМАНИЕ: Количество записей до ({len(sent_ads)}) и после ({saved_count}) сохранения различается!")
                    else:
                        print("ERROR: 'sent_ads' отсутствует в данных после сохранения!")
                else:
                    print(f"ERROR: {user_id} отсутствует в данных после сохранения!")
        
        print(f"== ЗАВЕРШЕНО СОХРАНЕНИЕ ДАННЫХ для пользователя {user_id} ==")
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА при сохранении данных пользователя {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data['active_chat_id'] = update.effective_chat.id
    
    # Устанавливаем кнопки меню
    menu_buttons = [
        [
            InlineKeyboardButton("🔄 Автопроверка", callback_data='menu_auto'),
            InlineKeyboardButton("⏹ Стоп", callback_data='menu_stop')
        ],
        [
            InlineKeyboardButton("🔍 Фильтры", callback_data='menu_filter')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(menu_buttons)
    
    welcome_message = (
        'Привет! Я бот для поиска квартир на tap.az и bina.az. 👋\n\n'
        
        '📋 *Как начать пользоваться ботом:*\n\n'
        
        '1️⃣ Посетите сайты [tap.az](https://tap.az/elanlar/dasinmaz-emlak/menziller) и [bina.az](https://bina.az/baki/kiraye/menziller)\n\n'
        
        '2️⃣ Настройте фильтры на сайте по своим критериям (цена, район, количество комнат и т.д.)\n\n'
        
        '3️⃣ Скопируйте URL из адресной строки браузера\n\n'
        
        '4️⃣ Установите новый URL в боте с помощью команд:\n'
        '   /turl <скопированный URL с tap.az>\n'
        '   /burl <скопированный URL с bina.az>\n\n'
        
        '5️⃣ Теперь можете использовать команды:\n'
        '   /t - для поиска на tap.az\n'
        '   /b - для поиска на bina.az\n'
        '   /auto - для автоматической проверки каждые 5 минут\n\n'
        
        '❓ Для получения дополнительной информации используйте /help'
    )
    
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    help_message = (
        '*📚 Подробная инструкция по использованию бота:*\n\n'
        
        '*🌐 Настройка URL для поиска:*\n'
        '1. Зайдите на сайты [tap.az](https://tap.az/elanlar/dasinmaz-emlak/menziller) и [bina.az](https://bina.az/baki/kiraye/menziller)\n'
        '2. Установите все нужные фильтры (цена, район, площадь, количество комнат и т.д.)\n'
        '3. Скопируйте полученный URL из адресной строки\n'
        '4. Используйте команду /turl и /burl для установки нового URL\n\n'
        
        '*🔍 Команды для поиска:*\n'
        '/t - поиск на tap.az по настроенному URL\n'
        '/b - поиск на bina.az по настроенному URL\n'
        '/parse <url> - поиск по произвольному URL\n\n'
        
        '*⚙️ Настройка автоматического поиска:*\n'
        '/auto - автоматическая проверка каждые 5 минут\n'
        '/auto <время в секундах> - установка своего интервала проверки\n'
        '/stop - остановка автоматической проверки\n\n'
        
        '*📋 Управление фильтрами:*\n'
        '/filter - управление фильтрами для блокировки нежелательных объявлений\n\n'
        
        '*📝 Текущие URL:*\n'
        f'tap.az:\n{get_user_data(update.effective_user.id)["urls"]["tap_az"]}\n\n'
        f'bina.az:\n{get_user_data(update.effective_user.id)["urls"]["bina_az"]}'
    )
    
    update.message.reply_text(help_message, parse_mode='Markdown', disable_web_page_preview=True)

def change_tap_url(update: Update, context: CallbackContext) -> None:
    """Change tap.az URL for searches."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not context.args:
        update.message.reply_text('Пожалуйста, укажите новый URL для tap.az.\n'
                                'Текущий URL:\n' + user_data['urls']['tap_az'])
        return
        
    new_url = context.args[0]
    if 'tap.az' not in new_url:
        update.message.reply_text('URL должен быть с сайта tap.az!')
        return
        
    user_data['urls']['tap_az'] = new_url
    save_user_data(user_id)
    update.message.reply_text('URL для tap.az успешно обновлен и сохранен!')

def change_bina_url(update: Update, context: CallbackContext) -> None:
    """Change bina.az URL for searches."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not context.args:
        update.message.reply_text('Пожалуйста, укажите новый URL для bina.az.\n'
                                'Текущий URL:\n' + user_data['urls']['bina_az'])
        return
        
    new_url = context.args[0]
    if 'bina.az' not in new_url:
        update.message.reply_text('URL должен быть с сайта bina.az!')
        return
        
    user_data['urls']['bina_az'] = new_url
    save_user_data(user_id)
    update.message.reply_text('URL для bina.az успешно обновлен и сохранен!')

def parse_command(update: Update, context: CallbackContext) -> None:
    """Parse website and send results."""
    if not context.args:
        update.message.reply_text('Пожалуйста, укажите URL сайта для парсинга.')
        return
        
    user_id = update.effective_user.id
    url = context.args[0]
    send_parsing_results(update, context, url)

def quick_search(update: Update, context: CallbackContext) -> None:
    """Quick search for apartments on tap.az."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    send_parsing_results(update, context, user_data['urls']['tap_az'])

def bina_search(update: Update, context: CallbackContext) -> None:
    """Quick search for apartments on bina.az."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    send_parsing_results(update, context, user_data['urls']['bina_az'])

def auto_check(update: Update, context: CallbackContext) -> None:
    """Enable automatic checking."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    # Останавливаем текущие задачи, если есть
    stop_auto_check(update, context)
    
    # Устанавливаем интервал
    interval = 300  # По умолчанию 5 минут (300 секунд)
    if context.args and len(context.args) > 0:
        try:
            interval = int(context.args[0])
            if interval < 60:
                update.message.reply_text('Минимальный интервал - 60 секунд!')
                interval = 60
        except ValueError:
            update.message.reply_text('Неверный формат времени! Используется значение по умолчанию (5 минут).')
    
    # Сохраняем информацию о включенной автопроверке
    user_data['auto_check'] = {
        'enabled': True,
        'interval': interval,
        'active_chat_id': update.effective_chat.id
    }
    save_user_data(user_id)
    
    # Добавляем задачи
    context.job_queue.run_repeating(
        auto_check_callback,
        interval=interval,
        first=10,
        context={'user_id': user_id},
        name=f'tap_az_check_{user_id}'
    )
    
    context.job_queue.run_repeating(
        auto_check_bina_callback,
        interval=interval,
        first=20,
        context={'user_id': user_id},
        name=f'bina_az_check_{user_id}'
    )
    
    update.message.reply_text(f'Автоматическая проверка включена (интервал: {interval} секунд)!')

def auto_check_callback(context: CallbackContext) -> None:
    """Callback for automatic checking tap.az."""
    user_id = context.job.context['user_id']
    user_data = get_user_data(user_id)
    
    if not user_data['active_chat_id']:
        print(f"ACTIVE_CHAT_ID не установлен для пользователя {user_id}")
        return
        
    print(f"Запуск проверки tap.az для пользователя {user_id}")
    
    try:
        results = parse_website(user_data['urls']['tap_az'], user_data['filters'])
        print(f"Получено {len(results) if results else 0} результатов с tap.az")
        if results and len(results) > 0:
            for result in results:
                try:
                    # Выводим результат для отладки
                    print(f"Результат tap.az: {result}")
                    print(f"Ссылка: {result.get('link', 'НЕТ ССЫЛКИ')}")
                    print(f"Текущая история: {user_data['sent_ads'][:5] if user_data['sent_ads'] else '[]'}")
                    
                    # Проверяем, не было ли это объявление уже отправлено
                    if result.get('link') and result['link'] in user_data['sent_ads']:
                        print(f"Пропускаем уже отправленное объявление tap.az: {result['link']}")
                        continue
                    
                    message_sent = False
                    if result.get('photo_url'):
                        try:
                            response = requests.get(result['photo_url'])
                            photo = BytesIO(response.content)
                            photo.name = 'image.jpg'
                            
                            context.bot.send_photo(
                                chat_id=user_data['active_chat_id'],
                                photo=photo,
                                caption=result['message'],
                                parse_mode='HTML',
                                filename='image.jpg'
                            )
                            message_sent = True
                        except Exception as photo_error:
                            print(f"Ошибка при отправке фото tap.az: {str(photo_error)}")
                            context.bot.send_message(
                                chat_id=user_data['active_chat_id'],
                                text=result['message'],
                                parse_mode='HTML'
                            )
                            message_sent = True
                    else:
                        context.bot.send_message(
                            chat_id=user_data['active_chat_id'],
                            text=result['message'],
                            parse_mode='HTML'
                        )
                        message_sent = True
                    
                    # Если сообщение успешно отправлено и есть ссылка, добавляем в историю
                    if message_sent and result.get('link'):
                        print(f"Добавляем в историю tap.az: {result['link']}")
                        print(f"Был ли в истории: {result['link'] in user_data['sent_ads']}")
                        
                        if result['link'] not in user_data['sent_ads']:
                            user_data['sent_ads'].append(result['link'])
                            # Проверяем, добавилась ли ссылка
                            print(f"Проверка добавления: {result['link'] in user_data['sent_ads']}")
                            
                            # Проверяем размер истории и обрезаем при необходимости
                            trim_sent_ads(user_id)
                            
                            try:
                                save_user_data(user_id)
                                print(f"История tap.az обновлена. Текущее количество объявлений: {len(user_data['sent_ads'])}")
                            except Exception as save_error:
                                print(f"ОШИБКА при сохранении истории tap.az: {str(save_error)}")
                except Exception as e:
                    print(f"Ошибка при обработке объявления tap.az: {str(e)}")
                    continue
    except Exception as e:
        print(f"Ошибка при автопроверке tap.az: {str(e)}")
        context.bot.send_message(
            chat_id=user_data['active_chat_id'],
            text=f'Произошла ошибка при автоматической проверке Tap.az: {str(e)}'
        )

def auto_check_bina_callback(context: CallbackContext) -> None:
    """Callback for automatic checking bina.az."""
    user_id = context.job.context['user_id']
    user_data = get_user_data(user_id)
    
    if not user_data['active_chat_id']:
        print(f"ACTIVE_CHAT_ID не установлен для пользователя {user_id}")
        return
        
    print(f"Запуск проверки bina.az для пользователя {user_id}")
    
    try:
        results = parse_website(user_data['urls']['bina_az'], user_data['filters'])
        print(f"Получено {len(results) if results else 0} результатов с bina.az")
        if results and len(results) > 0:
            for result in results:
                try:
                    # Проверяем, не было ли это объявление уже отправлено
                    if result.get('link') and result['link'] in user_data['sent_ads']:
                        print(f"Пропускаем уже отправленное объявление bina.az: {result['link']}")
                        continue
                    
                    message_sent = False
                    if result.get('photo_url'):
                        try:
                            response = requests.get(result['photo_url'])
                            photo = BytesIO(response.content)
                            photo.name = 'image.jpg'
                            
                            context.bot.send_photo(
                                chat_id=user_data['active_chat_id'],
                                photo=photo,
                                caption=result['message'],
                                parse_mode='HTML',
                                filename='image.jpg'
                            )
                            message_sent = True
                        except Exception as photo_error:
                            print(f"Ошибка при отправке фото bina.az: {str(photo_error)}")
                            context.bot.send_message(
                                chat_id=user_data['active_chat_id'],
                                text=result['message'],
                                parse_mode='HTML'
                            )
                            message_sent = True
                    else:
                        context.bot.send_message(
                            chat_id=user_data['active_chat_id'],
                            text=result['message'],
                            parse_mode='HTML'
                        )
                        message_sent = True
                    
                    # Если сообщение успешно отправлено и есть ссылка, добавляем в историю
                    if message_sent and result.get('link'):
                        print(f"Добавляем в историю bina.az: {result['link']}")
                        if result['link'] not in user_data['sent_ads']:
                            user_data['sent_ads'].append(result['link'])
                            
                            # Проверяем размер истории и обрезаем при необходимости
                            trim_sent_ads(user_id)
                            
                            save_user_data(user_id)
                            print(f"История bina.az обновлена. Текущее количество объявлений: {len(user_data['sent_ads'])}")
                except Exception as e:
                    print(f"Ошибка при обработке объявления bina.az: {str(e)}")
                    continue
    except Exception as e:
        print(f"Ошибка при автопроверке bina.az: {str(e)}")
        context.bot.send_message(
            chat_id=user_data['active_chat_id'],
            text=f'Произошла ошибка при автоматической проверке Bina.az: {str(e)}'
        )

def send_parsing_results(update: Update, context: CallbackContext, url: str) -> None:
    """Send parsing results to the user."""
    user_id = update.effective_user.id
    user_data_dict = get_user_data(user_id)
    
    try:
        results = parse_website(url, user_data_dict['filters'])
        if not results:
            update.message.reply_text('Новых объявлений не найдено!')
            return
            
        for result in results:
            try:
                # Проверяем, не было ли это объявление уже отправлено
                if result.get('link') and result['link'] in user_data_dict['sent_ads']:
                    print(f"Пропускаем уже отправленное объявление: {result['link']}")
                    continue
                    
                message_sent = False
                if result.get('photo_url'):
                    try:
                        response = requests.get(result['photo_url'])
                        photo = BytesIO(response.content)
                        photo.name = 'image.jpg'
                        
                        update.message.reply_photo(
                            photo=photo,
                            caption=result['message'],
                            parse_mode='HTML',
                            filename='image.jpg',
                            quote=False
                        )
                        message_sent = True
                    except Exception as photo_error:
                        print(f"Ошибка при отправке фото: {str(photo_error)}")
                        update.message.reply_text(
                            result['message'],
                            parse_mode='HTML'
                        )
                        message_sent = True
                else:
                    update.message.reply_text(
                        result['message'],
                        parse_mode='HTML'
                    )
                    message_sent = True
                
                # Если сообщение успешно отправлено и есть ссылка, добавляем в историю
                if message_sent and result.get('link'):
                    print(f"Добавляем в историю: {result['link']}")
                    if result['link'] not in user_data_dict['sent_ads']:
                        user_data_dict['sent_ads'].append(result['link'])
                        
                        # Проверяем размер истории и обрезаем при необходимости
                        trim_sent_ads(user_id)
                        
                        save_user_data(user_id)
                        print(f"История обновлена. Текущее количество объявлений: {len(user_data_dict['sent_ads'])}")
                    
            except Exception as e:
                print(f"Ошибка при обработке объявления: {str(e)}")
                continue
                
    except Exception as e:
        error_message = f'Произошла ошибка при парсинге: {str(e)}'
        print(error_message)
        update.message.reply_text(error_message)

def stop_auto_check(update: Update, context: CallbackContext) -> None:
    """Stop automatic checking."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    # Останавливаем все задачи пользователя
    current_jobs = context.job_queue.get_jobs_by_name(f'tap_az_check_{user_id}')
    for job in current_jobs:
        job.schedule_removal()
    
    current_jobs = context.job_queue.get_jobs_by_name(f'bina_az_check_{user_id}')
    for job in current_jobs:
        job.schedule_removal()
    
    # Сохраняем информацию о выключенной автопроверке
    if 'auto_check' in user_data:
        user_data['auto_check']['enabled'] = False
        save_user_data(user_id)
    
    # Отправляем сообщение только если это прямой вызов команды
    if update.message:
        update.message.reply_text('Автоматическая проверка остановлена!')

def filter_command(update: Update, context: CallbackContext) -> None:
    """Show filter management menu with inline buttons."""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить фильтр", callback_data='filter_add'),
            InlineKeyboardButton("❌ Удалить фильтр", callback_data='filter_remove')
        ],
        [
            InlineKeyboardButton("🗑 Очистить все фильтры", callback_data='filter_clear')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Показываем текущие фильтры
    message = "Текущие фильтры:\n\n"
    
    if user_data['filters']['location']:
        message += "Фильтры:\n"
        for f in user_data['filters']['location']:
            message += f"- {f}\n"
    else:
        message += "Фильтры: нет\n"
        
    message += "\nВыберите действие:"
    
    # Если это ответ на callback query, используем edit_text
    if update.callback_query:
        update.callback_query.message.edit_text(message, reply_markup=reply_markup)
    else:
        # Если это новый вызов команды, используем reply_text
        update.message.reply_text(message, reply_markup=reply_markup)

def filter_callback(update: Update, context: CallbackContext) -> None:
    """Handle filter button callbacks."""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    data = query.data.split('_')
    action = data[1]
    
    if action == 'clear':
        # Очищаем все фильтры
        user_data['filters'] = {'title': [], 'location': []}
        save_user_data(user_id)
        query.message.reply_text('Все фильтры удалены!')
        filter_command(update, context)  # Показываем обновленное меню
        return
        
    if action == 'add':
        # Показываем кнопки с городами
        keyboard = [
            [
                InlineKeyboardButton("Xırdalan", callback_data='filter_city_Xırdalan'),
                InlineKeyboardButton("Masazır", callback_data='filter_city_Masazır')
            ],
            [
                InlineKeyboardButton("Sumqayıt", callback_data='filter_city_Sumqayıt'),
                InlineKeyboardButton("Другое", callback_data='filter_city_other')
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data='filter_back')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            'Выберите город или "Другое" для ручного ввода:',
            reply_markup=reply_markup
        )
        return
        
    if action == 'city':
        city = data[2]
        if city == 'other':
            # Запрашиваем ручной ввод
            context.user_data['filter_action'] = 'add'
            query.message.reply_text(
                'Введите название города или района:\n'
                '(или отправьте /cancel для отмены)'
            )
        else:
            # Добавляем выбранный город
            if city not in user_data['filters']['title']:
                user_data['filters']['title'].append(city)
            if city not in user_data['filters']['location']:
                user_data['filters']['location'].append(city)
            save_user_data(user_id)
            query.message.reply_text(f'Фильтр "{city}" добавлен!')
            filter_command(update, context)
        return
        
    if action == 'remove':
        # Показываем кнопки с текущими фильтрами
        if not user_data['filters']['location']:
            query.message.reply_text('Нет активных фильтров для удаления!')
            return
            
        # Создаем кнопки для каждого фильтра
        keyboard = []
        for f in user_data['filters']['location']:
            keyboard.append([InlineKeyboardButton(f"❌ {f}", callback_data=f'filter_delete_{f}')])
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='filter_back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            'Выберите фильтр для удаления:',
            reply_markup=reply_markup
        )
        return
        
    if action == 'delete':
        # Удаляем выбранный фильтр
        filter_text = data[2]
        if filter_text in user_data['filters']['title']:
            user_data['filters']['title'].remove(filter_text)
        if filter_text in user_data['filters']['location']:
            user_data['filters']['location'].remove(filter_text)
        save_user_data(user_id)
        query.message.reply_text(f'Фильтр "{filter_text}" удален!')
        filter_command(update, context)  # Показываем обновленное меню
        return
        
    if action == 'back':
        # Возвращаемся к основному меню фильтров
        filter_command(update, context)
        return

def handle_filter_text(update: Update, context: CallbackContext) -> None:
    """Handle filter text input."""
    if 'filter_action' not in context.user_data:
        return
        
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    action = context.user_data['filter_action']
    filter_text = update.message.text
    
    if action == 'add':
        # Добавляем фильтр и в title, и в location
        if filter_text not in user_data['filters']['title']:
            user_data['filters']['title'].append(filter_text)
        if filter_text not in user_data['filters']['location']:
            user_data['filters']['location'].append(filter_text)
        save_user_data(user_id)
        update.message.reply_text(f'Фильтр "{filter_text}" добавлен!')
    
    # Очищаем данные
    del context.user_data['filter_action']
    
    # Показываем обновленное меню
    filter_command(update, context)

def cancel_filter(update: Update, context: CallbackContext) -> None:
    """Cancel filter operation."""
    if 'filter_action' in context.user_data:
        del context.user_data['filter_action']
        update.message.reply_text('Операция отменена.')
        filter_command(update, context)

def menu_callback(update: Update, context: CallbackContext) -> None:
    """Handle menu button callbacks."""
    query = update.callback_query
    query.answer()
    
    data = query.data.split('_')
    action = data[1]
    
    if action == 'auto':
        # Создаем временный объект Update с message
        temp_update = Update(update.update_id)
        temp_update.message = query.message
        auto_check(temp_update, context)
    elif action == 'stop':
        # Создаем временный объект Update с message
        temp_update = Update(update.update_id)
        temp_update.message = query.message
        stop_auto_check(temp_update, context)
    elif action == 'filter':
        # Создаем временный объект Update с message
        temp_update = Update(update.update_id)
        temp_update.message = query.message
        filter_command(temp_update, context)

def restore_auto_checks(dispatcher) -> None:
    """Восстанавливает автопроверки после перезапуска бота"""
    print("Восстановление автопроверок...")
    
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                all_users = json.load(f)
                
                for user_id_str, user_data_dict in all_users.items():
                    try:
                        user_id = int(user_id_str)
                        
                        # Проверяем, есть ли у пользователя включенная автопроверка
                        if 'auto_check' in user_data_dict and user_data_dict['auto_check'].get('enabled', False):
                            interval = user_data_dict['auto_check'].get('interval', 300)
                            active_chat_id = user_data_dict['auto_check'].get('active_chat_id')
                            
                            if active_chat_id:
                                print(f"Восстановление автопроверки для пользователя {user_id}, интервал: {interval} сек.")
                                
                                # Добавляем задачи в планировщик
                                dispatcher.job_queue.run_repeating(
                                    auto_check_callback,
                                    interval=interval,
                                    first=10,
                                    context={'user_id': user_id},
                                    name=f'tap_az_check_{user_id}'
                                )
                                
                                dispatcher.job_queue.run_repeating(
                                    auto_check_bina_callback,
                                    interval=interval,
                                    first=20,
                                    context={'user_id': user_id},
                                    name=f'bina_az_check_{user_id}'
                                )
                                
                                # Уведомляем пользователя о восстановлении автопроверки
                                try:
                                    dispatcher.bot.send_message(
                                        chat_id=active_chat_id,
                                        text=f'Бот был перезапущен. Автоматическая проверка восстановлена (интервал: {interval} секунд)!'
                                    )
                                except Exception as e:
                                    print(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")
                    except Exception as e:
                        print(f"Ошибка при восстановлении автопроверки для пользователя {user_id_str}: {str(e)}")
                        
        print("Восстановление автопроверок завершено")
    except Exception as e:
        print(f"Ошибка при восстановлении автопроверок: {str(e)}")

def main() -> None:
    """Start the bot."""
    try:
        # Create the Updater
        updater = Updater(TOKEN)

        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher

        # Создаем список команд для меню
        commands = [
            ('start', 'Запустить бота'),
            ('filter', 'Управление фильтрами'),
            ('auto', 'Включить автопроверку'),
            ('stop', 'Остановить автопроверку'),
            ('help', 'Показать справку'),
            ('t', 'Поиск на tap.az'),
            ('b', 'Поиск на bina.az')
        ]
        
        # Устанавливаем команды в меню
        updater.bot.set_my_commands(commands)

        # Add command handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("parse", parse_command))
        dispatcher.add_handler(CommandHandler("t", quick_search))
        dispatcher.add_handler(CommandHandler("b", bina_search))
        dispatcher.add_handler(CommandHandler("turl", change_tap_url))
        dispatcher.add_handler(CommandHandler("burl", change_bina_url))
        dispatcher.add_handler(CommandHandler("auto", auto_check))
        dispatcher.add_handler(CommandHandler("stop", stop_auto_check))
        dispatcher.add_handler(CommandHandler("filter", filter_command))
        dispatcher.add_handler(CommandHandler("cancel", cancel_filter))
        
        # Add callback query handlers
        dispatcher.add_handler(CallbackQueryHandler(menu_callback, pattern='^menu_'))
        dispatcher.add_handler(CallbackQueryHandler(filter_callback, pattern='^filter_'))
        
        # Add message handler for filter text input
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_filter_text))
        
        # Восстанавливаем автопроверки
        restore_auto_checks(dispatcher)
        
        # Start the Bot
        updater.start_polling()

        # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
        updater.idle()
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 