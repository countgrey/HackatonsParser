import sqlite3
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, database_name):
        self.database_name = database_name

    def get_connection(self):
        """Создание соединения с базой данных"""
        conn = sqlite3.connect(self.database_name)
        conn.row_factory = sqlite3.Row
        return conn

    def create_users_table(self):
        """Создает таблицу пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT,
                university TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def get_user(self, user_id):
        """Получает пользователя по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def save_user(self, user_data):
        """Сохраняет или обновляет пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, role, university, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_data['user_id'],
            user_data.get('username'),
            user_data.get('first_name'),
            user_data.get('last_name'),
            user_data.get('role'),
            user_data.get('university')
        ))
        conn.commit()
        conn.close()

    def get_stats(self):
        """Получить статистику базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Статистика мероприятий
        cursor.execute("SELECT COUNT(*) as count FROM smart_events")
        total_events = cursor.fetchone()['count']
        
        cursor.execute("SELECT type, COUNT(*) as count FROM smart_events GROUP BY type")
        type_stats = cursor.fetchall()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) as count FROM smart_events WHERE date_start >= ?", (today,))
        upcoming_events = cursor.fetchone()['count']
        
        # Статистика пользователей
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            'total_events': total_events,
            'type_stats': type_stats,
            'upcoming_events': upcoming_events,
        }

    def get_events_page(self, page, items_per_page):
        """Получить страницу мероприятий"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM smart_events")
        total_count = cursor.fetchone()['count']
        
        offset = page * items_per_page
        
        cursor.execute("""
            SELECT * FROM smart_events 
            ORDER BY date_start DESC 
            LIMIT ? OFFSET ?
        """, (items_per_page, offset))
        
        events = cursor.fetchall()
        conn.close()
        
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        return {
            'events': events,
            'total_count': total_count,
            'total_pages': total_pages
        }

    def get_today_events(self):
        """Получить мероприятия на сегодня"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM smart_events WHERE date_start = ?", (today,))
        events = cursor.fetchall()
        conn.close()
        
        return events

    def get_upcoming_events(self):
        """Получить ближайшие мероприятия (на неделю вперед)"""
        today = datetime.now().strftime('%Y-%m-%d')
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM smart_events 
            WHERE date_start >= ? AND date_start <= ?
            ORDER BY date_start
        """, (today, next_week))
        
        events = cursor.fetchall()
        conn.close()
        
        return events

    def search_events(self, search_query):
        """Поиск мероприятий"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_query}%"
        cursor.execute("""
            SELECT * FROM smart_events 
            WHERE title LIKE ? OR type LIKE ? OR organizer LIKE ? OR audience LIKE ?
            ORDER BY date_start DESC
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        
        events = cursor.fetchall()
        conn.close()
        
        return events

    def get_event_by_id(self, event_id):
        """Получить мероприятие по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM smart_events WHERE id = ?", (event_id,))
        event = cursor.fetchone()
        conn.close()
        
        return event
