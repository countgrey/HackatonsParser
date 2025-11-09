import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from bot_handlers import (
    start, help_command, show_events, show_types, 
    show_stats, search_command, button_handler,
    register_role, register_university, register_faculty, 
    register_course, complete_registration, cancel_registration,
    show_profile, reset_profile_command,
    ROLE, UNIVERSITY, FACULTY, COURSE
)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для регистрации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROLE: [CallbackQueryHandler(register_role)],
            UNIVERSITY: [CallbackQueryHandler(register_university)],
            FACULTY: [CallbackQueryHandler(register_faculty)],
            COURSE: [CallbackQueryHandler(register_course)],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_profile_command))
    app.add_handler(CommandHandler("profile", show_profile))
    app.add_handler(CommandHandler("events", show_events))
    app.add_handler(CommandHandler("types", show_types))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("search", search_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
