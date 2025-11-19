#!/usr/bin/env python3
"""
Скрипт для запуска парсера мероприятий.
Поддерживает как разовый запуск, так и автоматический по расписанию.
"""

import os
import sys
import logging
import signal
import time
import argparse
from pathlib import Path
from datetime import datetime

# Добавляем текущую директорию в Python path
sys.path.append(str(Path(__file__).parent))

import schedule
from dotenv import load_dotenv

# Импорт парсеров
try:
    import parce_raw
    import llm_smart_filter
except ImportError as e:
    print(f"❌ Ошибка импорта модулей парсера: {e}")
    sys.exit(1)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
def setup_logging():
    """Настройка логирования для парсера"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_filename = f"parser_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Обработчик сигналов для корректной остановки"""
    logger.info("🛑 Получен сигнал остановки...")
    logger.info("🛑 Остановка планировщика парсера...")
    sys.exit(0)

def run_raw_parser():
    """Запуск сырого парсера"""
    try:
        logger.info("🔄 Запуск парсера сырых данных...")
        parce_raw.run_parser()
        logger.info("✅ Парсер сырых данных завершен")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка в парсере сырых данных: {e}", exc_info=True)
        return False

def run_smart_filter():
    """Запуск LLM-фильтра"""
    try:
        logger.info("🤖 Запуск LLM-фильтра...")
        llm_smart_filter.smart_filter_and_enrich_to_new_db()
        logger.info("✅ LLM-фильтр завершен")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка в LLM-фильтре: {e}", exc_info=True)
        return False

def run_full_parsing_cycle():
    """Запуск полного цикла парсинга (сырой парсер + LLM-фильтр)"""
    logger.info("🚀 Начало полного цикла парсинга...")
    
    # Шаг 1: Парсинг сырых данных
    if not run_raw_parser():
        logger.error("❌ Цикл прерван на этапе парсинга сырых данных")
        return False
    
    # Пауза между этапами
    logger.info("⏸️ Пауза между этапами (5 секунд)...")
    time.sleep(5)
    
    # Шаг 2: LLM-фильтрация
    if not run_smart_filter():
        logger.error("❌ Цикл прерван на этапе LLM-фильтрации")
        return False
    
    logger.info("🎉 Полный цикл парсинга успешно завершен!")
    return True

def run_scheduler():
    """Запуск планировщика для автоматического парсинга"""
    logger.info("📅 Настройка планировщика парсера...")
    
    # Парсинг каждый день в 03:00
    schedule.every().day.at("03:00").do(run_full_parsing_cycle)
    
    # Для отладки: парсинг каждый час (раскомментировать при необходимости)
    # schedule.every().hour.do(run_full_parsing_cycle)
    
    logger.info("✅ Планировщик настроен")
    logger.info("🕐 Следующий запуск: 03:00 ежедневно")
    logger.info("💡 Для остановки нажмите Ctrl+C")
    
    # Запуск немедленно при старте (опционально)
    if os.getenv('RUN_ON_START', 'false').lower() == 'true':
        logger.info("🔄 Выполнение первичного запуска...")
        run_full_parsing_cycle()
    
    # Основной цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту

def main():
    """Основная функция"""
    global logger
    logger = setup_logging()
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Запуск парсера мероприятий',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_parser.py --once              # Запуск полного цикла один раз
  python run_parser.py --raw-only          # Только парсинг сырых данных
  python run_parser.py --filter-only       # Только LLM-фильтрация
  python run_parser.py --scheduler         # Запуск планировщика
  python run_parser.py --scheduler --run-on-start  # Планировщик с первичным запуском
        """
    )
    
    parser.add_argument(
        '--once', 
        action='store_true',
        help='Запустить полный цикл парсинга один раз и завершить'
    )
    
    parser.add_argument(
        '--raw-only', 
        action='store_true',
        help='Запустить только парсинг сырых данных'
    )
    
    parser.add_argument(
        '--filter-only', 
        action='store_true',
        help='Запустить только LLM-фильтрацию'
    )
    
    parser.add_argument(
        '--scheduler', 
        action='store_true',
        help='Запустить планировщик для автоматического парсинга'
    )
    
    parser.add_argument(
        '--run-on-start',
        action='store_true',
        help='Выполнить парсинг сразу при запуске планировщика (только с --scheduler)'
    )
    
    args = parser.parse_args()
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Логика выбора режима работы
        if args.once:
            logger.info("🔄 Режим: Однократный запуск полного цикла")
            success = run_full_parsing_cycle()
            sys.exit(0 if success else 1)
            
        elif args.raw_only:
            logger.info("🔄 Режим: Только парсинг сырых данных")
            success = run_raw_parser()
            sys.exit(0 if success else 1)
            
        elif args.filter_only:
            logger.info("🔄 Режим: Только LLM-фильтрация")
            success = run_smart_filter()
            sys.exit(0 if success else 1)
            
        elif args.scheduler:
            if args.run_on_start:
                os.environ['RUN_ON_START'] = 'true'
            logger.info("🔄 Режим: Планировщик")
            run_scheduler()
            
        else:
            # По умолчанию - однократный запуск
            logger.info("🔄 Режим по умолчанию: Однократный запуск полного цикла")
            success = run_full_parsing_cycle()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по запросу пользователя...")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()