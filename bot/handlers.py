import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from .database import DatabaseManager
from .keyboards import KeyboardManager
from .utils import MessageFormatter

class EventBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.db_name = os.getenv('DATABASE_NAME', 'smart_filtered.db')
        self.items_per_page = int(os.getenv('ITEMS_PER_PAGE', '5'))
        
        if not self.bot_token:
            raise ValueError("❌ BOT_TOKEN не найден в .env файле")
        
        self.db = DatabaseManager(self.db_name)
        self.keyboards = KeyboardManager()
        self.formatter = MessageFormatter()
        
        self.application = Application.builder().token(self.bot_token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("events", self.events_command))
        self.application.add_handler(CommandHandler("today", self.today_events_command))
        self.application.add_handler(CommandHandler("upcoming", self.upcoming_events_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.message.from_user
        welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для поиска мероприятий из образовательных учреждений Оренбурга.

📋 Доступные команды:
/events - Все мероприятия
/today - Мероприятия сегодня
/upcoming - Ближайшие мероприятия  
/search - Поиск мероприятий
/stats - Статистика базы
/help - Помощь

Выберите команду или просто напишите что ищете!
        """
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 **Помощь по командам:**

/events - Показать все мероприятия с пагинацией
/today - Мероприятия на сегодня
/upcoming - Ближайшие мероприятия (на неделю вперед)
/search - Поиск мероприятий по ключевым словам
/stats - Показать статистику базы данных

🔍 **Простой поиск:**
Просто напишите в чат ключевые слова для поиска:
- Название мероприятия
- Тип (конференция, семинар, хакатон)
- Аудиторию (студенты, школьники)
        """
        await update.message.reply_text(help_text)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику базы данных"""
        stats = self.db.get_stats()
        
        stats_text = f"""
📊 **Статистика базы данных**

📈 Всего мероприятий: {stats['total_events']}
🔜 Предстоящих: {stats['upcoming_events']}

📋 **Распределение по типам:**
"""
        
        for stat in stats['type_stats']:
            stats_text += f"• {stat['type']}: {stat['count']}\n"
        
        stats_text += f"\n🗄️ База данных: {self.db_name}"
        
        await update.message.reply_text(stats_text)

    async def events_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все мероприятия с пагинацией"""
        page = 0
        await self.show_events_page(update, context, page)

    async def show_events_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        """Показать страницу с мероприятиями"""
        events_data = self.db.get_events_page(page, self.items_per_page)
        
        if not events_data['events']:
            await update.message.reply_text("📭 В базе данных нет мероприятий.")
            return
        
        message = f"📋 **Мероприятия** (страница {page + 1} из {events_data['total_pages']})\n\n"
        reply_markup = self.keyboards.create_events_keyboard(
            events_data['events'], 
            page, 
            events_data['total_pages'],
            events_data['total_count']
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def today_events_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мероприятия на сегодня"""
        events = self.db.get_today_events()
        
        if not events:
            await update.message.reply_text("📅 На сегодня мероприятий не найдено.")
            return
        
        await update.message.reply_text("🎉 **Мероприятия на сегодня:**")
        
        for event in events:
            message = self.formatter.format_event_message(event)
            await update.message.reply_text(message, parse_mode='Markdown')

    async def upcoming_events_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ближайшие мероприятия (на неделю вперед)"""
        events = self.db.get_upcoming_events()
        
        if not events:
            await update.message.reply_text("📅 Ближайшие мероприятия не найдены.")
            return
        
        await update.message.reply_text("🔜 **Ближайшие мероприятия:**")
        
        for event in events:
            message = self.formatter.format_event_message(event)
            await update.message.reply_text(message, parse_mode='Markdown')

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск мероприятий"""
        if not context.args:
            await update.message.reply_text("🔍 **Использование поиска:**\n/search <ключевые слова>\n\nПример: /search конференция студенты")
            return
        
        search_query = ' '.join(context.args)
        await self.perform_search(update, search_query)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений (поиск)"""
        search_query = update.message.text
        await self.perform_search(update, search_query)

    async def perform_search(self, update: Update, search_query: str):
        """Выполнить поиск мероприятий"""
        events = self.db.search_events(search_query)
        
        if not events:
            await update.message.reply_text(f"🔍 По запросу '{search_query}' ничего не найдено.")
            return
        
        if len(events) == 1:
            message = self.formatter.format_event_message(events[0])
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            message = f"🔍 **Найдено мероприятий: {len(events)}**\n\n"
            reply_markup = self.keyboards.create_search_results_keyboard(events)
            await update.message.reply_text(message, reply_markup=reply_markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline-кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("page_"):
            page = int(data.split("_")[1])
            await self.show_events_page_from_query(query, context, page)
        
        elif data.startswith("event_"):
            event_id = int(data.split("_")[1])
            await self.show_event_details(query, event_id)
        
        elif data == "back_to_list":
            await self.show_events_page_from_query(query, context, 0)

    async def show_events_page_from_query(self, query, context: ContextTypes.DEFAULT_TYPE, page: int):
        """Показать страницу мероприятий из callback query"""
        events_data = self.db.get_events_page(page, self.items_per_page)
        
        message = f"📋 **Мероприятия** (страница {page + 1} из {events_data['total_pages']})\n\n"
        reply_markup = self.keyboards.create_events_keyboard(
            events_data['events'], 
            page, 
            events_data['total_pages'],
            events_data['total_count']
        )
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def show_event_details(self, query, event_id: int):
        """Показать детальную информацию о мероприятии"""
        event = self.db.get_event_by_id(event_id)
        
        if not event:
            await query.edit_message_text("❌ Мероприятие не найдено.")
            return
        
        message = self.formatter.format_event_message(event)
        reply_markup = self.keyboards.create_event_details_keyboard()
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    def run(self):
        """Запуск бота"""
        self.application.run_polling()
