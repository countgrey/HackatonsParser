import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('DB_NAME', 'smart_filtered.db')  # Используем обогащенную БД
TABLE_NAME = os.getenv('TABLE_NAME', 'smart_events')
USERS_DB_NAME = 'users.db'

def get_events_by_type(event_type=None, limit=10, user_data=None):
    """Получение событий с фильтрацией по роли пользователя"""
    conn = sqlite3.connect(DB_NAME)
    
    # Базовый запрос
    base_query = f"SELECT * FROM {TABLE_NAME} WHERE 1=1"
    params = []
    
    # Фильтрация по типу события
    if event_type and event_type != "all":
        base_query += " AND detected_type = ?"
        params.append(event_type)
    
    # Фильтрация по роли пользователя
    if user_data:
        user_filter = build_user_filter(user_data)
        base_query += user_filter['where']
        params.extend(user_filter['params'])
    
    # Сортировка и лимит
    base_query += " ORDER BY date_start DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df

def build_user_filter(user_data):
    """Построение фильтра на основе данных пользователя"""
    where_clauses = []
    params = []
    
    role = user_data.get('role')
    university = user_data.get('university')  # Используем полное название для фильтрации
    faculty = user_data.get('faculty')  # Используем полное название для фильтрации
    course = user_data.get('course')
    
    # Фильтрация по университету
    if university:
        where_clauses.append("(organizer LIKE ? OR organizer = ?)")
        params.extend([f'%{university}%', university])
    
    # Фильтрация по факультету (если есть в данных событий)
    if faculty:
        where_clauses.append("(text LIKE ? OR title LIKE ?)")
        params.extend([f'%{faculty}%', f'%{faculty}%'])
    
    # Фильтрация по курсу для студентов
    if role == 'student' and course:
        # Предполагаем, что события для младших курсов подходят и старшим
        if course <= 2:
            # События для 1-2 курсов
            where_clauses.append("(audience LIKE ? OR audience LIKE ?)")
            params.extend(['%младш%', '%начал%'])
        else:
            # События для 3+ курсов
            where_clauses.append("(audience LIKE ? OR audience LIKE ? OR audience LIKE ?)")
            params.extend(['%старш%', '%продвинут%', '%выпуск%'])
    
    # Фильтрация по роли
    if role == 'student':
        where_clauses.append("(audience LIKE ? OR audience LIKE ? OR audience = ?)")
        params.extend(['%студент%', '%учащийся%', '[]'])
    elif role == 'teacher':
        where_clauses.append("(audience LIKE ? OR audience LIKE ? OR audience = ?)")
        params.extend(['%преподаватель%', '%педагог%', '[]'])
    
    where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
    return {'where': where_sql, 'params': params}

def get_event_types(user_data=None):
    """Получение типов событий с учетом роли пользователя"""
    conn = sqlite3.connect(DB_NAME)
    
    base_query = f"SELECT DISTINCT detected_type FROM {TABLE_NAME} WHERE detected_type != ''"
    params = []
    
    if user_data:
        user_filter = build_user_filter(user_data)
        base_query += user_filter['where']
        params.extend(user_filter['params'])
    
    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df['detected_type'].tolist()

def search_events(query, limit=10, user_data=None):
    """Поиск событий с фильтрацией по роли пользователя"""
    conn = sqlite3.connect(DB_NAME)
    
    base_query = f"""
    SELECT * FROM {TABLE_NAME} 
    WHERE (title LIKE ? OR description LIKE ? OR text LIKE ?)
    """
    params = [f'%{query}%', f'%{query}%', f'%{query}%']
    
    if user_data:
        user_filter = build_user_filter(user_data)
        base_query += user_filter['where']
        params.extend(user_filter['params'])
    
    base_query += " ORDER BY date_start DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df

def get_stats(user_data=None):
    """Получение статистики с учетом роли пользователя"""
    conn = sqlite3.connect(DB_NAME)
    
    base_query = f"SELECT COUNT(*) as count FROM {TABLE_NAME} WHERE 1=1"
    params = []
    
    if user_data:
        user_filter = build_user_filter(user_data)
        base_query += user_filter['where']
        params.extend(user_filter['params'])
    
    total_events = pd.read_sql_query(base_query, conn, params=params).iloc[0]['count']
    
    # Статистика по типам с фильтрацией
    type_query = f"""
    SELECT detected_type, COUNT(*) as count FROM {TABLE_NAME} 
    WHERE detected_type != ''
    """
    type_params = []
    
    if user_data:
        user_filter = build_user_filter(user_data)
        type_query += user_filter['where']
        type_params.extend(user_filter['params'])
    
    type_query += " GROUP BY detected_type ORDER BY count DESC"
    type_stats = pd.read_sql_query(type_query, conn, params=type_params)
    
    last_update = pd.read_sql_query(
        f"SELECT MAX(created_at) as last_date FROM {TABLE_NAME} WHERE created_at != ''", 
        conn
    ).iloc[0]['last_date']
    
    conn.close()
    
    return {
        'total_events': total_events,
        'type_stats': type_stats,
        'last_update': last_update
    }

# Функции для работы с пользователями
def get_user(user_id):
    """Получение данных пользователя"""
    conn = sqlite3.connect(USERS_DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'role': user[4],
            'university': user[5],
            'university_short': user[6] if len(user) > 6 else user[5],
            'university_code': user[7] if len(user) > 7 else None,
            'faculty': user[8] if len(user) > 8 else None,
            'faculty_short': user[9] if len(user) > 9 else None,
            'faculty_code': user[10] if len(user) > 10 else None,
            'course': user[11] if len(user) > 11 else None
        }
    return None

def save_user(user_data):
    """Сохранение/обновление данных пользователя"""
    conn = sqlite3.connect(USERS_DB_NAME)
    cursor = conn.cursor()
    
    # Проверяем существование таблицы и ее структуру
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Если таблица имеет старую структуру, обновляем ее
    if 'university_short' not in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN university_short TEXT
        """)
    if 'university_code' not in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN university_code TEXT
        """)
    if 'faculty_short' not in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN faculty_short TEXT
        """)
    if 'faculty_code' not in columns:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN faculty_code TEXT
        """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, role, university, university_short, university_code, 
         faculty, faculty_short, faculty_code, course, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        user_data['user_id'],
        user_data['username'],
        user_data['first_name'],
        user_data['last_name'],
        user_data['role'],
        user_data['university'],
        user_data.get('university_short', user_data['university']),
        user_data.get('university_code'),
        user_data.get('faculty'),
        user_data.get('faculty_short', user_data.get('faculty')),
        user_data.get('faculty_code'),
        user_data.get('course')
    ))
    
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Удаление пользователя из базы данных"""
    conn = sqlite3.connect(USERS_DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        success = cursor.rowcount > 0
    except Exception as e:
        print(f"Ошибка при удалении пользователя: {e}")
        success = False
    finally:
        conn.close()
    
    return success

def user_exists(user_id):
    """Проверка существования пользователя"""
    return get_user(user_id) is not None
