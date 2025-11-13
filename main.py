# scheduler_main.py
import schedule
import time
import subprocess
import threading
import logging
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotScheduler:
    def __init__(self):
        self.bot_process = None
        self.parser_process = None
        self.is_running = False
        
        # Настройки из .env
        self.parser_schedule = os.getenv('PARSER_SCHEDULE', '03:00')
        self.bot_restart_delay = int(os.getenv('BOT_RESTART_DELAY', '10'))
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
    def start_bot(self):
        """Запуск бота в отдельном процессе"""
        try:
            logger.info("🤖 Запуск бота...")
            self.bot_process = subprocess.Popen(
                ['python', 'bot.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            logger.info("✅ Бот успешно запущен")
            
            # Запуск потоков для чтения вывода
            threading.Thread(target=self._read_stdout, args=(self.bot_process,), daemon=True).start()
            threading.Thread(target=self._read_stderr, args=(self.bot_process,), daemon=True).start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            
    def run_parser(self):
        """Запуск парсера и LLM-фильтра"""
        try:
            logger.info("🔄 Запуск парсера...")
            
            # Запуск парсера
            parser_result = subprocess.run(
                ['python', 'parce_raw.py'],
                capture_output=True,
                text=True,
                timeout=3600  # Таймаут 1 час
            )
            
            if parser_result.returncode == 0:
                logger.info("✅ Парсер успешно завершил работу")
                logger.info(f"📊 Вывод парсера: {parser_result.stdout[-500:]}")  # Последние 500 символов
                
                # Запуск LLM-фильтра после парсера
                logger.info("🧠 Запуск LLM-фильтра...")
                filter_result = subprocess.run(
                    ['python', 'llm_smart_filter.py'],
                    capture_output=True,
                    text=True,
                    timeout=7200  # Таймаут 2 часа
                )
                
                if filter_result.returncode == 0:
                    logger.info("✅ LLM-фильтр успешно завершил работу")
                    logger.info(f"📊 Вывод фильтра: {filter_result.stdout[-500:]}")
                    
                    # Перезапуск бота для загрузки обновленных данных
                    time.sleep(self.bot_restart_delay)
                    self.restart_bot()
                else:
                    logger.error(f"❌ Ошибка LLM-фильтра (код {filter_result.returncode}): {filter_result.stderr}")
            else:
                logger.error(f"❌ Ошибка парсера (код {parser_result.returncode}): {parser_result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Таймаут выполнения парсера/фильтра")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске парсера: {e}")
    
    def restart_bot(self):
        """Перезапуск бота для применения обновленных данных"""
        try:
            logger.info("🔄 Перезапуск бота...")
            
            if self.bot_process:
                self.bot_process.terminate()
                try:
                    self.bot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.bot_process.kill()
                    self.bot_process.wait()
                
            self.start_bot()
            logger.info("✅ Бот успешно перезапущен с обновленными данными")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при перезапуске бота: {e}")
            # Пытаемся запустить бота заново
            self.start_bot()
    
    def _read_stdout(self, process):
        """Чтение stdout процесса"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    logger.info(f"🤖 [BOT] {line.strip()}")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения stdout бота: {e}")
    
    def _read_stderr(self, process):
        """Чтение stderr процесса"""
        try:
            for line in iter(process.stderr.readline, ''):
                if line:
                    logger.error(f"🤖 [BOT ERROR] {line.strip()}")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения stderr бота: {e}")
    
    def schedule_parser(self):
        """Настройка расписания для парсера"""
        # Ежедневный запуск в указанное время
        schedule.every().day.at(self.parser_schedule).do(self.run_parser)
        
        logger.info(f"📅 Парсер запланирован на ежедневный запуск в {self.parser_schedule}")
        
        # Для отладки: раскомментируйте следующую строку для запуска каждые 10 минут
        # schedule.every(10).minutes.do(self.run_parser)
    
    def run(self):
        """Основной цикл выполнения"""
        self.is_running = True
        
        try:
            # Запуск бота
            self.start_bot()
            
            # Настройка расписания
            self.schedule_parser()
            
            logger.info("🚀 Планировщик запущен. Бот работает, парсер запускается по расписанию.")
            logger.info("💡 Для остановки нажмите Ctrl+C")
            
            # Основной цикл проверки расписания
            while self.is_running:
                schedule.run_pending()
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки...")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка всех процессов"""
        self.is_running = False
        
        logger.info("🛑 Остановка процессов...")
        
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
            except:
                self.bot_process.kill()
                
        logger.info("✅ Все процессы остановлены")

def main():
    """Основная функция"""
    print("=" * 50)
    print("🤖 ПЛАНИРОВЩИК БОТА И ПАРСЕРА")
    print("=" * 50)
    print(f"Режимы работы:")
    print(f"  • Бот: постоянно активен")
    print(f"  • Парсер: ежедневно в {os.getenv('PARSER_SCHEDULE', '03:00')}")
    print(f"  • Логи: scheduler.log")
    print("=" * 50)
    
    scheduler = BotScheduler()
    
    try:
        scheduler.run()
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка: {e}")
        scheduler.stop()

if __name__ == "__main__":
    main()
