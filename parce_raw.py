import requests
from bs4 import BeautifulSoup
import sqlite3
import re
from urllib.parse import urljoin, urlparse
import time
import math
import json
from datetime import datetime
from collections import deque

# --- КОНФИГУРАЦИЯ ---
DATABASE_NAME = "events.db"
SOURCES_FILE = "sources.json" 

# --- ПАРАМЕТРЫ ЗАПУСКА ---
# Ограничивает проход только по первой трети (1/3) найденных целевых ссылок.
TEST_LIMIT_FRACTION = 1
# Если True, база данных очищается перед запуском.
DEBUG = True
# Максимальное количество страниц для обхода
MAX_CRAWL_PAGES = 10

# --- ФИЛЬТРЫ И КЛЮЧЕВЫЕ СЛОВА ---
# Слова для фильтрации ссылок (Этап 1)
EVENT_KEYWORDS = [
    'конференция', 'семинар', 'хакатон', 'конкурс', 'форум', 
    'соревнование', 'олимпиада', 'выставка', 'лекция', 'вебинар',
    'пройдет' # Часто указывает на анонс
]

# Типы мероприятий для классификации
EVENT_TYPES_MAP = {
    'конференц': 'Конференция',
    'семинар': 'Семинар',
    'хакатон': 'Хакатон',
    'конкурс': 'Конкурс/Соревнование',
    'олимпиад': 'Олимпиада',
    'выставк': 'Выставка',
    'форум': 'Форум'
}

## <-- НОВОЕ: ЭВРИСТИЧЕСКИЙ ФИЛЬТР
# Стоп-слова, указывающие на прошедшее событие или новостной "шум"
NOISE_INDICATORS = [
    'состоялась', 'прошел', 'подвели итоги', 'итоги конкурса', 'завершилась',
    'победитель', 'лауреат', 'призеров', 'награждение', 'открыт прием', # "открыт прием" может быть и релевантным, но часто относится к новостям
    'сотрудник', 'кафедра', 'поздравляем', 'вошел в топ', 'профессор', 'должность'
]
# Слова, которые сами по себе не являются событием (служебные страницы)
NON_EVENT_TERMS = [
    'институт', 'факультет', 'о нас', 'новости вуза', 'структура'
]
# Пороговое значение для плотности ключевых слов
KEYWORD_DENSITY_THRESHOLD = 0.005 # 0.5% плотности ключевых слов
## ---------------------------------

# --- Функции загрузки конфигурации ---

def load_sources():
    """Загружает список сайтов для парсинга из sources.json."""
    try:
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            sources = json.load(f)
        print(f"✅ Загружено {len(sources)} источников из {SOURCES_FILE}.")
        return sources
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл '{SOURCES_FILE}' не найден. Создайте его.")
        return []
    except json.JSONDecodeError:
        print(f"❌ Ошибка: Некорректный формат JSON в файле '{SOURCES_FILE}'.")
        return []

# --- Функции базы данных (Без изменений) ---

def clear_database():
    """Удаляет таблицу events, очищая все данные."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS events")
    conn.commit()
    conn.close()
    print("🗑️ База данных очищена (DEBUG=True).")

def setup_database():
    """Создает таблицу событий в SQLite, если она не существует."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            title TEXT,
            city TEXT,
            type TEXT,
            date_start TEXT,
            date_end TEXT,
            reg_start TEXT,
            reg_end TEXT,
            team_required BOOLEAN,
            audience TEXT,
            organizer TEXT,
            link TEXT UNIQUE,
            text TEXT 
        )
    """)
    conn.commit()
    conn.close()
    print(f"✅ База данных '{DATABASE_NAME}' готова.")

def save_event(event_data):
    """Сохраняет событие в базу данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        # Преобразование audience из списка в JSON-строку
        audience_json = json.dumps(event_data.get('audience', []))
        
        # Преобразование team_required в число (0 или 1)
        team_required_val = 1 if event_data.get('team_required') else 0

        cursor.execute("""
            INSERT INTO events (
                title, city, type, date_start, date_end, reg_start, reg_end,
                team_required, audience, organizer, link, text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data.get('title'),
            event_data.get('city'),
            event_data.get('type'),
            event_data.get('date_start'),
            event_data.get('date_end'),
            event_data.get('reg_start'),
            event_data.get('reg_end'),
            team_required_val, 
            audience_json, 
            event_data.get('organizer'),
            event_data.get('link'),
            event_data.get('text') 
        ))
        conn.commit()
        print(f"    💾 Успешно сохранено: {event_data.get('title', 'Без названия')[:50]}...")
        return True
    except sqlite3.IntegrityError:
        print("    ➡️ Пропуск: Ссылка уже есть в БД.")
        return False
    except Exception as e:
        print(f"    ❌ Ошибка при сохранении: {e}")
        return False
    finally:
        conn.close()

# --- Вспомогательные функции для парсинга и обхода (Без изменений) ---

def fetch_and_extract_text(url):
    """Загружает страницу, извлекает и очищает основной текст."""
    # (Функция остается без изменений, возвращает page_title и full_text_to_search)
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException:
        return None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Удаление элементов-шумов по тегам
    for element in soup(["header", "footer", "nav", "aside", "script", "style", "img", "form", "button", "iframe"]):
        element.decompose()
        
    # 2. Удаление элементов-шумов по общим классам
    noise_selectors = [
        '.sidebar', '.nav', '.menu', '#nav', '#menu', '.advertisement', 
        '.footer', '.widget', '.vacancies', '#footer', '#header', '#sidebar', 
        '.cookie-notice', '#cookie-banner', '.gdpr-container', '#privacy-policy'
    ]
    for selector in noise_selectors:
        for element in soup.select(selector):
            element.decompose()
        
    # 3. Поиск заголовка (Title)
    page_title_tag = soup.find('h1') or soup.find('title')
    page_title = page_title_tag.get_text(strip=True) if page_title_tag else ""

    # 4. Поиск основного содержимого
    main_content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'(content|main-content|article-content|post|entry|text-block)', re.I))
    
    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
    else:
        text = soup.get_text(separator=' ', strip=True)
        
    cleaned_text = re.sub(r'\s+', ' ', text)
    
    # 5. Убираем из контента страницы сам заголовок H1, если он был найден
    if page_title and cleaned_text.startswith(page_title):
        cleaned_text = cleaned_text[len(page_title):].strip()
        
    full_text_to_search = page_title + " " + cleaned_text
    
    # ФИНАЛЬНАЯ ПРОВЕРКА: если контента слишком мало (кроме заголовка), это, вероятно, ошибка парсинга
    if len(cleaned_text.split()) < 5:
        return None, None
        
    return page_title, full_text_to_search[:8000]

# (Функции обхода остаются без изменений)
def check_link_relevance_by_keywords(context):
    """Проверяет контекст на наличие ключевых слов мероприятия."""
    context_lower = context.lower()
    
    # Наличие ключевого слова
    is_event = any(keyword in context_lower for keyword in EVENT_KEYWORDS)
    
    # Отфильтровать нерелевантный шум
    is_noise = any(noise in context_lower for noise in ['реквизиты', 'вакансии', 'работодатель', 'приказ', 'поздравляем'])
    
    return is_event and not is_noise

def extract_links_from_page(url, base_url):
    """Извлекает ссылки из страницы."""
    base_domain = urlparse(base_url).netloc
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return set(), set()

    soup = BeautifulSoup(response.text, 'html.parser')
    all_links = soup.find_all('a', href=True)
    
    event_links = set()
    crawl_links = set()
    file_extensions = ['.pdf', '.doc', '.docx', '.zip', '.rar', '#', '.xlsx', '.jpg', '.jpeg', '.png']
    
    for link in all_links:
        href = link['href']
        full_url = urljoin(base_url, href).split('#')[0] 
        
        # 1. Фильтрация файлов, якорей и внешних/текущих ссылок
        if any(full_url.lower().endswith(ext) for ext in file_extensions) or \
           urlparse(full_url).netloc != base_domain or \
           full_url == url:
            continue
            
        link_text = link.get_text(strip=True)
        context = link_text
        
        parent = link.find_parent()
        if parent and parent.name in ['li', 'p', 'div', 'td']:
            context = parent.get_text(strip=True)
            
        # 2. Классификация
        if check_link_relevance_by_keywords(context):
            event_links.add(full_url)
        
        # Все ссылки на том же домене считаем потенциальными целями для обхода
        crawl_links.add(full_url)
        
    return event_links, crawl_links

def crawl_site_bfs(start_url, base_url, max_pages):
    """Обход сайта в ширину (BFS)."""
    
    # Очередь для обхода (FIFO)
    queue = deque([start_url])
    # Все посещенные страницы
    visited_pages = {start_url}
    # Окончательный список ссылок на события
    all_event_links = set()
    
    pages_crawled = 0
    
    print(f"\n--- ЭТАП 1: Обход сайта (BFS) для {base_url} ---")
    
    while queue and pages_crawled < max_pages:
        current_url = queue.popleft()
        pages_crawled += 1
        print(f"    [Обход {pages_crawled}/{max_pages}] -> {current_url}")
        
        event_links, crawl_links = extract_links_from_page(current_url, base_url)
        
        # Добавляем найденные ссылки на события в общий набор
        all_event_links.update(event_links)
        
        # Добавляем новые ссылки для обхода в очередь
        for link in crawl_links:
            if link not in visited_pages:
                visited_pages.add(link)
                queue.append(link)
                
    print(f"✅ Обход завершен. Посещено страниц: {pages_crawled}. Найдено уникальных ссылок на события: {len(all_event_links)}")
    return list(all_event_links)

# --- ЭТАП 2 и 3: Извлечение данных с эвристическим фильтром ---

def parse_dates(text):
    # (Функция остается без изменений)
    dates = []
    
    # 1. Поиск в явном формате (дд.мм.гггг)
    explicit_dates = re.findall(r'(\d{1,2}\.\d{1,2}\.\d{2,4})', text)
    for date_str in explicit_dates:
        try:
            # Пытаемся преобразовать, чтобы отсеять невалидные даты
            dt = datetime.strptime(date_str, '%d.%m.%Y')
            dates.append(dt.strftime('%Y-%m-%d'))
        except ValueError:
            pass

    # 2. Поиск в словесном формате
    month_map = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6, 
                 'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12}
    date_patterns = r'(\d{1,2})[\.\s](янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)[а-я]*[\.\s]?(\d{2,4})'
                 
    verbal_dates = re.findall(date_patterns, text, re.I)
    
    for day, month_abbr, year in verbal_dates:
        try:
            month_num = month_map[month_abbr[:3].lower()]
            if len(year) == 2:
                # Предполагаем, что 20XX год
                year = '20' + year
                
            dt = datetime(int(year), month_num, int(day))
            dates.append(dt.strftime('%Y-%m-%d'))
        except:
            pass

    # Удаляем дубликаты и сортируем
    unique_dates = sorted(list(set(dates)))
    
    date_start = unique_dates[0] if unique_dates else ""
    date_end = unique_dates[-1] if len(unique_dates) > 1 else date_start
    
    return date_start, date_end

def check_event_relevance_by_heuristics(page_title, page_text):
    """
    Эвристический фильтр: Проверяет текст на наличие стоп-слов и плотность ключевых слов.
    Возвращает False, если событие нерелевантно.
    """
    context_lower = (page_title + " " + page_text).lower()
    total_length = len(context_lower.split())

    # 1. Фильтр по стоп-словам (новости/прошедшие события)
    if any(noise_term in context_lower for noise_term in NOISE_INDICATORS):
        return False, "Найден новостной/прошедший маркер"

    # 2. Фильтр по не-событийным терминам (служебные страницы)
    # Проверяем, не является ли заголовок сам по себе не-событийным термином
    if any(term in page_title.lower() for term in NON_EVENT_TERMS):
        return False, "Заголовок указывает на служебную страницу"
        
    # 3. Фильтр по плотности ключевых слов
    event_keyword_count = sum(context_lower.count(keyword) for keyword in EVENT_KEYWORDS)
    if total_length > 100 and event_keyword_count / total_length < KEYWORD_DENSITY_THRESHOLD:
        return False, "Низкая плотность ключевых слов"

    # 4. Дополнительный фильтр: Если нет дат и нет типа события, считать нерелевантным
    # (Это будет сделано в вызывающей функции, после extract_event_data_python_only)

    return True, "Пройден"


def extract_event_data_python_only(page_title, page_text, original_link, default_organizer, default_city):
    """
    Извлекает структурированные данные из текста с помощью чистого Python (RegEx).
    """
    # <-- НОВОЕ: ПРОВЕРКА ЭВРИСТИЧЕСКИМ ФИЛЬТРОМ
    is_relevant, reason = check_event_relevance_by_heuristics(page_title, page_text)
    if not is_relevant:
        print(f"    ❌ Эвристический фильтр: Пропуск. Причина: {reason}")
        return None
    # ---------------------------------------------
    
    event_data = {
        "title": page_title.strip() if page_title else "",
        "city": default_city, # <-- Значение по умолчанию
        "type": "Мероприятие",
        "date_start": "",
        "date_end": "",
        "reg_start": "",
        "reg_end": "",
        "team_required": False,
        "audience": [],
        "organizer": default_organizer, # <-- Значение по умолчанию
        "link": original_link,
        "text": page_text # <-- Полный текст
    }
    
    # 1. Улучшенный заголовок: Если H1 пуст, берем первую осмысленную строку
    if not event_data['title']:
        first_sentence = re.split(r'[.!?]', page_text, 1)[0]
        if len(first_sentence.split()) > 3:
              event_data['title'] = first_sentence.strip()
    
    # 2. Извлечение типа мероприятия
    for keyword, event_type in EVENT_TYPES_MAP.items():
        if re.search(keyword, page_text, re.I):
            event_data['type'] = event_type
            break
            
    # 3. Извлечение дат
    start, end = parse_dates(page_text)
    event_data['date_start'] = start
    event_data['date_end'] = end
    
    # 4. Переопределение города, организатора, аудитории, команды (без изменений)
    if re.search(r'оренбург', page_text, re.I):
        event_data['city'] = "Оренбург"
        
    if re.search(r'оренбургский госуд|огу|оренбургский государственный университет', page_text, re.I):
        event_data['organizer'] = "ОГУ"
    
    audience_map = {'студент': 'студент', 'преподаватель': 'преподаватель', 'школьник': 'школьник', 'научный': 'научный сотрудник', 'аспирант': 'студент'}
    found_audience = set()
    for keyword, audience_type in audience_map.items():
        if re.search(keyword, page_text, re.I):
            found_audience.add(audience_type)
    event_data['audience'] = list(found_audience)
    
    reg_match = re.search(r'(регистрация|заявки)\s+(?:до|по)\s+(\d{1,2}\.\d{1,2}\.\d{2,4})', page_text, re.I)
    if reg_match:
        try:
            event_data['reg_end'] = datetime.strptime(reg_match.group(2), '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass
            
    if re.search(r'команд[аыу]', page_text, re.I):
        event_data['team_required'] = True
    
    # Финальная проверка: Если не найден ни заголовок, ни даты, пропускаем (остается)
    if not event_data['title'] and not event_data['date_start']:
        return None
        
    return event_data

# --- Основной цикл парсера (Без изменений) ---

def run_parser():
    """Основная функция для запуска парсинга с обходом нескольких сайтов."""
    
    # 1. Очистка БД (если DEBUG=True) и инициализация
    if DEBUG:
        clear_database()
        
    setup_database()
    
    # 2. Загрузка источников
    sources = load_sources()
    if not sources:
        print("🔴 Нет источников для обработки. Завершение работы.")
        return
        
    global_events_saved = 0
    
    for source in sources:
        source_name = source['name']
        start_url = source['start_url']
        base_url = source['base_url']
        default_city = source['city']
        default_organizer = source_name
        
        print(f"\n=======================================================")
        print(f"                НАЧАЛО ОБРАБОТКИ ИСТОЧНИКА: {source_name}")
        print(f"=======================================================")
        
        # 3. Сбор ссылок с помощью обхода сайта (BFS)
        target_links = crawl_site_bfs(start_url, base_url, MAX_CRAWL_PAGES)
        
        if not target_links:
            print(f"🔴 Для {source_name} не найдено релевантных ссылок.")
            continue
        
        # --- ОГРАНИЧЕНИЕ ДЛЯ ТЕСТА ---
        limit = math.ceil(len(target_links) * TEST_LIMIT_FRACTION)
        links_to_process = target_links[:limit]
        total_target_links = len(target_links)
        
        print(f"\n--- ЭТАПЫ 2 и 3: Извлечение данных для {source_name} ---")
        print(f"🎯 Выбрано {len(links_to_process)}/{total_target_links} целевых ссылок для обработки (лимит: {TEST_LIMIT_FRACTION * 100:.0f}%).")
        
        links_processed = 0
        events_saved = 0
        
        for i, link in enumerate(links_to_process):
            links_processed += 1
            print(f"\n* Обработка ссылки {i + 1}/{len(links_to_process)}: {link}")
            
            # 4. Загрузка и обрезание страницы
            page_title, page_content = fetch_and_extract_text(link)
            
            if not page_content:
                print("    ⏩ Пропуск (не удалось загрузить/очистить страницу или контент нерелевантен).")
                continue
                
            print("    🔍 Python/RegEx: Извлечение данных...")
            
            # 5. Извлечение данных (Python/RegEx) с передачей значений по умолчанию
            event_data = extract_event_data_python_only(
                page_title, 
                page_content, 
                link, 
                default_organizer, 
                default_city
            )
            
            if event_data:
                # 6. Сохранение в БД
                if save_event(event_data):
                    events_saved += 1
            else:
                # Этот блок теперь ловит как неудачное извлечение, так и фильтрацию
                pass 
                
            time.sleep(0.1) 
            
        global_events_saved += events_saved
        
        print(f"\n--- РЕЗУЛЬТАТЫ ДЛЯ {source_name} ---")
        print(f"✅ Обработано ссылок: {links_processed}/{total_target_links}.")
        print(f"💾 Успешно сохранено событий: {events_saved}.")

    print(f"\n=======================================================")
    print(f"                             ОБЩИЕ РЕЗУЛЬТАТЫ")
    print(f"=======================================================")
    print(f"💾 ВСЕГО УСПЕШНО СОХРАНЕНО СОБЫТИЙ: {global_events_saved}.")


if __name__ == "__main__":
    run_parser()