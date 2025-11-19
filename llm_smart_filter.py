import sqlite3
import requests
import json
import time
from typing import Optional, Dict, Any, List

# --- КОНФИГУРАЦИЯ LLM ---
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

LLM_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + "/api/generate"
MODEL_NAME = os.getenv('MODEL_NAME', 'mistral')
SOURCE_DB_NAME = "events.db"
TARGET_DB_NAME = "smart_filtered.db" # <-- НОВАЯ ЦЕЛЕВАЯ БАЗА
# ---

# Структура ответа, которую мы ожидаем от LLM
class LLM_Output:
    def __init__(self, is_relevant: bool, cleaned_title: str, audience: List[str]):
        self.is_relevant = is_relevant
        self.cleaned_title = cleaned_title
        self.audience = audience

def setup_target_database(target_db):
    """Создает целевую таблицу в новой базе данных."""
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    # Структура таблицы должна соответствовать исходной
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smart_events (
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
    print(f"✅ Целевая база данных '{target_db}' готова.")

def save_smart_event(conn, event_data):
    """Сохраняет очищенное событие в целевую базу данных."""
    cursor = conn.cursor()
    try:
        # Преобразование audience из списка в JSON-строку
        audience_json = json.dumps(event_data.get('audience', []))
        
        # team_required должен быть числом
        team_required_val = 1 if event_data.get('team_required') else 0

        cursor.execute("""
            INSERT INTO smart_events (
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
        return True
    except sqlite3.IntegrityError:
        # Эта ошибка может возникнуть, если исходная БД имела дубликаты, но мы их не пропустим
        print("    ➡️ Пропуск: Ссылка уже есть в целевой БД.")
        return False
    except Exception as e:
        print(f"    ❌ Ошибка при сохранении в целевую БД: {e}")
        return False

def query_llm_for_cleaning_and_filtering(title: str, full_text: str, event_type: str) -> Optional[LLM_Output]:
    """
    Отправляет запрос к локальной LLM для фильтрации, очистки названия и определения аудитории.
    (Используется УТОЧНЁННЫЙ ПРОМПТ)
    """
    # Использование JSON-формата
    system_prompt = (
        "Ты — высокоэффективный ассистент по обработке данных мероприятий. "
        "Твоя задача — проанализировать предоставленное название и текст события, "
        "а затем предоставить структурированный JSON-ответ с тремя полями: "
        "'is_relevant', 'cleaned_title' и 'audience'.\n\n"
        
        "### УТОЧНЕННЫЕ ИНСТРУКЦИИ ДЛЯ КАЧЕСТВА ДАННЫХ:\n"
        
        "1. **is_relevant (boolean):** Установи в `false`, если событие:\n"
        "   - **Не является актуальным анонсом/регистрацией** (это новость о результатах, итогах, поздравлениях, вакансиях).\n"
        "   - **Описывает деятельность, связанную с конкретной группой людей/кафедрой**, а не широкое мероприятие (например, 'Магистранты кафедры X получили Y').\n"
        "   - **Не содержит явного указания на событие** (слишком общий текст или описание структуры сайта).\n"
        "   - В остальных случаях (актуальный анонс) установи `true`.\n"
        
        "2. **cleaned_title (string):** Очисти исходное название. Это название **должно быть самодостаточным и конкретным**. "
        "   - **Удали:** даты, время, города, имена организаторов (ОГУ, кафедра X), слова, дублирующие 'type' ('Конференция', 'Конкурс').\n"
        "   - **Обязательно дополни:** Если исходное название слишком общее или неполное (например, 'Международный инженер' или 'Лаборатория'), "
        "     используй контекст из текста, чтобы сделать его информативным, например: 'Международный инженерный конкурс 'Цифровая энергетика'.\n"
        "   - Оставь только чистое, стандартизированное и осмысленное название.\n"
        
        "3. **audience (array of strings):** Определи целевую аудиторию (например, 'студенты', 'школьники', 'специалисты', 'все желающие'). "
        "   - Используй только строчные буквы на русском языке. Верни пустой массив, если аудитория не определена.\n\n"
        
        "**Обязательный формат ответа: Только чистый JSON.**"
    )

    prompt_text = (
        f"Исходное название: {title}\n"
        f"Тип мероприятия (из БД): {event_type}\n"
        f"Контекст из текста (первые 500 символов): {full_text[:500]}..."
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_text,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_k": 1,
        },
        "format": "json" 
    }

    try:
        response = requests.post(LLM_URL, json=payload, timeout=45)
        response.raise_for_status() 
        
        result_json_str = response.json().get('response', '')
        llm_data: Dict[str, Any] = json.loads(result_json_str)

        output = LLM_Output(
            is_relevant=llm_data.get('is_relevant', False),
            cleaned_title=llm_data.get('cleaned_title', title).strip(),
            audience=llm_data.get('audience', [])
        )
        return output
        
    except requests.exceptions.RequestException as e:
        print(f"    ❌ Ошибка при запросе к LLM ({LLM_URL}): {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"    ❌ Ошибка декодирования/парсинга JSON ответа от LLM: {e}")
        # print(f"    Получен текст: {result_json_str}") # Раскомментировать для отладки
        return None

def smart_filter_and_enrich_to_new_db():
    """
    Основная функция: Чтение из events.db, обработка LLM, запись в smart_filtered.db.
    """
    setup_target_database(TARGET_DB_NAME)

    source_conn = sqlite3.connect(SOURCE_DB_NAME)
    source_cursor = source_conn.cursor()
    target_conn = sqlite3.connect(TARGET_DB_NAME)
    
    print(f"🚀 Чтение данных из '{SOURCE_DB_NAME}'...")
    
    # Извлечение ВСЕХ полей, кроме ID (он будет новым в целевой БД)
    source_cursor.execute("""
        SELECT 
            title, city, type, date_start, date_end, reg_start, reg_end, 
            team_required, audience, organizer, link, text 
        FROM events
    """)
    events = source_cursor.fetchall()
    
    if not events:
        print("ℹ️ В исходной базе данных не найдено событий для обработки.")
        source_conn.close()
        target_conn.close()
        return

    print(f"📚 Найдено {len(events)} событий для анализа и фильтрации.")
    
    saved_count = 0
    filtered_count = 0
    
    # Заголовки столбцов для создания словаря из кортежа данных
    column_names = [
        'title', 'city', 'type', 'date_start', 'date_end', 'reg_start', 
        'reg_end', 'team_required', 'audience', 'organizer', 'link', 'text'
    ]
    
    for i, event_row in enumerate(events):
        # Преобразование кортежа в словарь для удобства работы
        original_event_data = dict(zip(column_names, event_row))
        
        original_title = original_event_data['title']
        event_type = original_event_data['type']
        full_text = original_event_data['text']
        
        print(f"\n--- [Событие {i+1}/{len(events)}] Анализ: {original_title[:80]}...")
        
        # 1. Запрос к LLM на анализ
        llm_result = query_llm_for_cleaning_and_filtering(original_title, full_text, event_type)
        
        if not llm_result:
            print("    ❌ Пропуск: Не удалось получить надежный ответ от LLM.")
            continue
        
        # 2. Фильтрация (Пропуск нерелевантного)
        if not llm_result.is_relevant:
            filtered_count += 1
            print(f"    🗑️ ФИЛЬТР: Событие признано нерелевантным (is_relevant=false).")
            continue
            
        # 3. Обогащение и очистка (Подготовка данных для сохранения)
        
        final_event_data = original_event_data.copy()
        
        # Обновление очищенным заголовком
        final_event_data['title'] = llm_result.cleaned_title
        
        # Обновление обогащенной аудиторией
        final_event_data['audience'] = llm_result.audience if llm_result.audience else json.loads(final_event_data['audience'])
        
        # 4. Сохранение в целевую БД
        if save_smart_event(target_conn, final_event_data):
            saved_count += 1
            print(f"    ✨ СОХРАНЕНО в {TARGET_DB_NAME}. Название: '{llm_result.cleaned_title[:50]}...'")
        
        time.sleep(0.5) 
        
    source_conn.close()
    target_conn.close()
    
    # --- РЕЗУЛЬТАТЫ ---
    print(f"\n=======================================================")
    print(f"                                 ОБЩИЕ РЕЗУЛЬТАТЫ")
    print(f"=======================================================")
    print(f"✅ Успешно сохранено (очищено и обогащено) в '{TARGET_DB_NAME}': {saved_count}")
    print(f"🗑️ Отфильтровано (удалено как 'шум'): {filtered_count}")
    print(f"ℹ️ Всего обработано событий: {len(events)}")

if __name__ == "__main__":
    smart_filter_and_enrich_to_new_db()