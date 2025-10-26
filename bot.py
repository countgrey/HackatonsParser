import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from bot_handlers import (
    start, help_command, show_events, show_types, 
    update_data, show_stats, search_command, button_handler
)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_NAME = os.getenv('DB_NAME')
TABLE_NAME = os.getenv('TABLE_NAME')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

#---MAIN---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("events", show_events))
    app.add_handler(CommandHandler("types", show_types))
    app.add_handler(CommandHandler("update", update_data))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("search", search_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
