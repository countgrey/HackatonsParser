#!/usr/bin/env python3
"""
Скрипт для запуска Telegram-бота парсера мероприятий.
Запускает только бота без планировщика.
"""

import os
import sys
import logging
import signal
import time
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
from bot import EventBot

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
def setup_logging():
    """Настройка логирования для бота"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "bot.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Обработчик сигналов для корректной остановки"""
    logger.info("🛑 Получен сигнал остановки...")
    logger.info("🛑 Остановка бота...")
    sys.exit(0)

def main():
    """Основная функция запуска бота"""
    global logger
    logger = setup_logging()
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🤖 Запуск Telegram-бота...")
        
        # Проверка наличия токена бота
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN не найден в .env файле")
            sys.exit(1)
        
        # Создание и запуск бота
        bot = EventBot()
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info(f"📊 Настройки:")
        logger.info(f"   • База данных: {bot.db_name}")
        logger.info(f"   • Элементов на странице: {bot.items_per_page}")
        logger.info(f"   • Уровень логирования: {os.getenv('LOG_LEVEL', 'INFO')}")
        
        logger.info("🚀 Бот запущен и готов к работе!")
        logger.info("💡 Для остановки нажмите Ctrl+C")
        
        # Запуск бота (блокирующая операция)
        bot.run()
        
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по запросу пользователя...")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Бот остановлен")

if __name__ == "__main__":
    main()