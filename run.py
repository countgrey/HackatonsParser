#!/usr/bin/env python3

import subprocess
import sys
import time
import threading
import schedule
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def run_parser():
    """Запуск парсера и обновление базы данных"""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Запуск парсера...")
    result = subprocess.run([sys.executable, "parser.py"])
    if result.returncode == 0:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Парсер завершил работу успешно")
        
        # Запускаем LLM фильтр после парсера
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Запуск LLM фильтра...")
        result_llm = subprocess.run([sys.executable, "llm_smart_filter.py"])
        if result_llm.returncode == 0:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - LLM фильтр завершил работу успешно")
        else:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - LLM фильтр завершил работу с ошибкой")
            
        return True
    else:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Парсер завершил работу с ошибкой")
        return False

def run_bot():
    """Запуск телеграм бота"""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Запуск телеграм бота...")
    subprocess.run([sys.executable, "bot.py"])

def setup_user_database():
    """Создание базы данных пользователей"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            role TEXT NOT NULL CHECK(role IN ('student', 'teacher')),
            university TEXT,
            faculty TEXT,
            course INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ База данных пользователей готова")

def scheduler_thread():
    """Поток для выполнения задач по расписанию"""
    # Запуск парсера каждый день в 8:00
    schedule.every().day.at("08:00").do(run_parser)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Инициализация системы...")
    
    # Создаем базу данных пользователей
    setup_user_database()
    
    # Первоначальный запуск парсера
    print("\n" + "="*50)
    run_parser()
    
    # Запуск планировщика в отдельном потоке
    print("\n" + "="*50)
    print("⏰ Запуск планировщика задач...")
    scheduler = threading.Thread(target=scheduler_thread, daemon=True)
    scheduler.start()
    
    # Запуск бота
    print("\n" + "="*50)
    run_bot()
