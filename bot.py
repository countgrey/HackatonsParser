import os
import logging
from dotenv import load_dotenv
from bot import EventBot

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=os.getenv('LOG_LEVEL', 'INFO')
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        bot = EventBot()
        print("🤖 Бот запущен...")
        print(f"📊 Настройки:")
        print(f"   • База данных: {bot.db_name}")
        print(f"   • Элементов на странице: {bot.items_per_page}")
        print(f"   • Уровень логирования: {os.getenv('LOG_LEVEL', 'INFO')}")
        bot.run()
    except ValueError as e:
        print(e)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
