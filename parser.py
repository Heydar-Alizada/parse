import requests
from bs4 import BeautifulSoup
from typing import Dict, List
import random
import json
import os
import time

# Файл для хранения отправленных объявлений
SENT_ADS_FILE = 'sent_ads.json'
# Файл для хранения фильтров
FILTERS_FILE = 'filters.json'

def load_sent_ads() -> set:
    """Загружает список отправленных объявлений"""
    if os.path.exists(SENT_ADS_FILE):
        with open(SENT_ADS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_sent_ads(ads: set) -> None:
    """Сохраняет список отправленных объявлений"""
    with open(SENT_ADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(ads), f)

def load_filters() -> dict:
    """Загружает фильтры из файла"""
    if os.path.exists(FILTERS_FILE):
        with open(FILTERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'title': [], 'location': []}

def save_filters(filters: dict) -> None:
    """Сохраняет фильтры в файл"""
    with open(FILTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(filters, f)

def apply_filters(title: str, location: str) -> bool:
    """Проверяет, соответствует ли объявление фильтрам"""
    filters = load_filters()
    
    # Проверяем фильтры по заголовку
    for filter_text in filters['title']:
        if filter_text.lower() in title.lower():
            return False
            
    # Проверяем фильтры по местоположению
    for filter_text in filters['location']:
        if filter_text.lower() in location.lower():
            return False
            
    return True

def add_filter(filter_type: str, filter_text: str) -> None:
    """Добавляет новый фильтр"""
    filters = load_filters()
    
    if filter_type in ['title', 'location']:
        if filter_text not in filters[filter_type]:
            filters[filter_type].append(filter_text)
            save_filters(filters)

def remove_filter(filter_type: str, filter_text: str) -> None:
    """Удаляет фильтр"""
    filters = load_filters()
    
    if filter_type in ['title', 'location']:
        if filter_text in filters[filter_type]:
            filters[filter_type].remove(filter_text)
            save_filters(filters)

def get_filters() -> dict:
    """Возвращает текущие фильтры"""
    return load_filters()

def get_random_user_agent() -> str:
    """Return a random user agent string."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

def make_request(url: str, max_retries: int = 3) -> requests.Response:
    """Make a request with retries and random delays."""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'az-AZ,az;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache'
            }
            
            # Добавляем случайную задержку между попытками
            if attempt > 0:
                delay = random.uniform(2, 5)
                print(f"Попытка {attempt + 1} после задержки {delay:.1f} сек")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:  # Последняя попытка
                raise
            print(f"Попытка {attempt + 1} не удалась: {str(e)}")
            continue

def parse_tap_az(url: str, user_filters: dict = None) -> list:
    """Parse tap.az website and return formatted results and photo URLs"""
    try:
        response = make_request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        items = soup.find_all('div', class_='products-i')
        
        print(f"Найдено объявлений tap.az: {len(items)}")
        
        for item in items[:10]:  # Проверяем первые 10 объявлений
            try:
                # Проверяем наличие необходимых элементов
                title_elem = item.find('div', class_='products-name')
                if not title_elem:
                    continue
                    
                title_text = title_elem.text.strip().lower()
                
                # Получаем ссылку
                link = item.find('a', class_='products-link')
                if not link:
                    continue
                    
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = 'https://tap.az' + href
                
                print(f"\nОбработка объявления tap.az: {title_text}")
                print(f"Ссылка: {href}")
                
                # Проверяем фильтры
                if user_filters:
                    # Проверяем фильтры по заголовку
                    if any(filter_text.lower() in title_text for filter_text in user_filters['title']):
                        print(f"Пропущено по фильтру заголовка: {title_text}")
                        continue
                    
                    # Проверяем фильтры по местоположению
                    location_elem = item.find('div', class_='products-location')
                    if location_elem:
                        location = location_elem.text.strip().lower()
                        if any(filter_text.lower() in location for filter_text in user_filters['location']):
                            print(f"Пропущено по фильтру местоположения: {location}")
                            continue
                
                # Получаем цену
                price_elem = item.find('div', class_='products-price')
                price = price_elem.text.strip() if price_elem else 'Цена не указана'
                
                # Получаем фото
                photo_elem = item.find('img')
                photo_url = None
                if photo_elem:
                    photo_url = photo_elem.get('data-src') or photo_elem.get('src')
                    if photo_url and not photo_url.startswith('http'):
                        photo_url = 'https:' + photo_url
                
                # Ищем местоположение
                location_elem = item.find('div', class_='products-created')
                location_text = location_elem.text.strip() if location_elem else 'Местоположение не указано'
                
                # Проверяем фильтры по местоположению
                if user_filters and any(f in location_text.lower() for f in user_filters['location']):
                    continue
                
                # Формируем сообщение
                message = f"🏠 {title_text}\n"
                message += f"📍 {location_text}\n"
                message += f"💰 {price}\n"
                message += f"🔗 {href}"
                
                results.append({
                    'message': message,
                    'photo_url': photo_url,
                    'link': href  # Добавляем ссылку для проверки дубликатов
                })
                
            except Exception as e:
                print(f"Ошибка при обработке объявления tap.az: {str(e)}")
                continue
                
        print(f"Успешно обработано объявлений tap.az: {len(results)}")
        return results
        
    except requests.RequestException as e:
        raise Exception(f"Ошибка при запросе к сайту: {str(e)}")
    except Exception as e:
        raise Exception(f"Ошибка при парсинге: {str(e)}")

def parse_bina_az(url: str, user_filters: dict = None) -> list:
    """Parse bina.az website and return formatted results and photo URLs"""
    try:
        response = make_request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Ищем все объявления
        items = soup.find_all('div', class_='items-i') or soup.find_all('div', class_='items') or soup.find_all('div', class_='items-i-vip')
        
        print(f"Найдено объявлений: {len(items)}")
        
        for item in items[:10]:  # Проверяем первые 10 объявлений
            try:
                # Получаем фото и заголовок из атрибута alt
                photo_elem = item.find('img')
                if not photo_elem:
                    print("Не найдено изображение")
                    continue
                    
                full_title = photo_elem.get('alt', '').strip()
                if not full_title:
                    print("Не найден заголовок в атрибуте alt")
                    continue
                    
                print(f"\nОбработка объявления: {full_title}")
                
                # Извлекаем местоположение из заголовка и формируем чистый заголовок
                location = "Местоположение не указано"
                title = full_title
                if " - " in full_title:
                    parts = full_title.split(" - ")
                    if len(parts) >= 2:
                        # Берем местоположение и делаем первую букву заглавной
                        location = parts[1].strip()
                        location = location[0].upper() + location[1:] if location else location
                        # Формируем заголовок без местоположения
                        title = parts[0].strip()
                        if len(parts) > 2:
                            title += " - " + parts[2].strip()
                
                # Проверяем фильтры
                if user_filters:
                    # Проверяем фильтры по заголовку
                    if any(filter_text.lower() in full_title.lower() for filter_text in user_filters['title']):
                        print(f"Пропущено по фильтру заголовка: {full_title}")
                        continue
                    
                    # Проверяем фильтры по местоположению
                    if any(filter_text.lower() in location.lower() for filter_text in user_filters['location']):
                        print(f"Пропущено по фильтру местоположения: {location}")
                        continue
                
                # Получаем ссылку
                link = item.find('a', class_='item_link')
                if not link:
                    print("Не найдена ссылка на объявление")
                    continue
                    
                href = link.get('href', '')
                if not href.startswith('http'):
                    href = 'https://bina.az' + href
                
                # Получаем цену
                price_elem = item.find('div', class_='items-price') or item.find('div', class_='price') or item.find('div', class_='items-price-vip')
                price = price_elem.text.strip() if price_elem else 'Цена не указана'
                
                # Получаем URL фото
                photo_url = photo_elem.get('data-src') or photo_elem.get('src')
                if photo_url and not photo_url.startswith('http'):
                    photo_url = 'https:' + photo_url
                
                # Формируем сообщение
                message = f"🏠 {title}\n"
                message += f"📍 {location}\n"
                message += f"💰 {price}\n"
                message += f"🔗 {href}"
                
                results.append({
                    'message': message,
                    'photo_url': photo_url,
                    'link': href  # Добавляем ссылку для проверки дубликатов
                })
                
            except Exception as e:
                print(f"Ошибка при обработке объявления bina.az: {str(e)}")
                continue
                
        print(f"Успешно обработано объявлений: {len(results)}")
        return results
        
    except requests.RequestException as e:
        raise Exception(f"Ошибка при запросе к сайту: {str(e)}")
    except Exception as e:
        raise Exception(f"Ошибка при парсинге: {str(e)}")

def parse_website(url: str, user_filters: dict = None) -> list:
    """Parse website and return results."""
    if 'tap.az' in url:
        return parse_tap_az(url, user_filters)
    elif 'bina.az' in url:
        return parse_bina_az(url, user_filters)
    else:
        raise ValueError('Неподдерживаемый сайт') 