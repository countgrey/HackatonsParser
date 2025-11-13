import os
from enum import Enum
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, 
    MessageHandler, filters, ConversationHandler
)
from .database import DatabaseManager
from .keyboards import KeyboardManager
from .utils import MessageFormatter

# Состояния диалога
class ProfileStates(Enum):
    ROLE = 1
    UNIVERSITY = 2

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
        
        # Создаем таблицу пользователей при инициализации
        self.db.create_users_table()
        
        self.application = Application.builder().token(self.bot_token).build()
        self.setup_handlers()

    def get_main_menu_keyboard(self):
        """Создает главное меню с reply-клавиатурой"""
        keyboard = [
            [KeyboardButton("📅 Мероприятия"), KeyboardButton("🎯 Сегодня")],
            [KeyboardButton("🔜 Ближайшие"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("👤 Мой профиль")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_back_to_menu_keyboard(self):
        """Создает клавиатуру с одной кнопкой 'Главное меню'"""
        keyboard = [[KeyboardButton("🏠 Главное меню")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # ConversationHandler для сбора профиля
        profile_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('profile', self.start_profile)],
            states={
                ProfileStates.ROLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_role)
                ],
                ProfileStates.UNIVERSITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_university)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_profile)],
        )

        self.application.add_handler(profile_conv_handler)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("events", self.events_command))
        self.application.add_handler(CommandHandler("today", self.today_events_command))
        self.application.add_handler(CommandHandler("upcoming", self.upcoming_events_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("myprofile", self.show_profile))
        self.application.add_handler(CommandHandler("menu", self.show_main_menu))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработчик для главного меню (должен быть перед общим обработчиком текста)
        self.application.add_handler(MessageHandler(
            filters.Text([
                "📅 Мероприятия", "🎯 Сегодня", "🔜 Ближайшие", 
                "🔍 Поиск", "📊 Статистика", "👤 Мой профиль", "ℹ️ Помощь",
                "🏠 Главное меню"  # Добавляем обработку новой кнопки
            ]), 
            self.handle_main_menu
        ))
        
        # Общий обработчик текста (для поиска)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий кнопок главного меню"""
        text = update.message.text
        
        if text == "📅 Мероприятия":
            await self.events_command(update, context)
        elif text == "🎯 Сегодня":
            await self.today_events_command(update, context)
        elif text == "🔜 Ближайшие":
            await self.upcoming_events_command(update, context)
        elif text == "🔍 Поиск":
            await update.message.reply_text(
                "🔍 Введите ключевые слова для поиска:",
                reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру для ввода текста
            )
        elif text == "📊 Статистика":
            await self.stats_command(update, context)
        elif text == "👤 Мой профиль":
            await self.show_profile(update, context)
        elif text == "ℹ️ Помощь":
            await self.help_command(update, context)
        elif text == "🏠 Главное меню":
            await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню"""
        reply_markup = self.get_main_menu_keyboard()
        await update.message.reply_text(
            "🏠 **Главное меню**\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start с проверкой профиля"""
        user = update.message.from_user
        
        # Проверяем, есть ли профиль пользователя
        existing_user = self.db.get_user(user.id)
        
        if existing_user:
            welcome_text = f"""
👋 С возвращением, {user.first_name}!

Ваш профиль уже настроен. Можете продолжить поиск мероприятий.
            """
            # Показываем главное меню
            reply_markup = self.get_main_menu_keyboard()
        else:
            welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для поиска мероприятий из образовательных учреждений Оренбурга.

📝 Для персонализации рекомендаций давайте настроим ваш профиль.
Введите /profile чтобы начать настройку.
            """
            # Без клавиатуры, предлагаем настроить профиль
            reply_markup = None
        
        welcome_text += """
📋 Доступные команды:
/events - Все мероприятия
/today - Мероприятия сегодня
/upcoming - Ближайшие мероприятия  
/search - Поиск мероприятий
/myprofile - Показать мой профиль
/profile - Изменить профиль
/stats - Статистика базы
/help - Помощь
/menu - Показать главное меню
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    # PROFILE MANAGEMENT HANDLERS

    async def start_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начинает процесс настройки профиля"""
        user = update.message.from_user
        
        # Создаем клавиатуру с вариантами ролей
        role_keyboard = [
            [KeyboardButton("🎓 Студент"), KeyboardButton("👨‍🏫 Преподаватель")],
            [KeyboardButton("🔬 Научный сотрудник"), KeyboardButton("🎯 Абитуриент")],
            [KeyboardButton("👨‍💼 Сотрудник"), KeyboardButton("❔ Другое")]
        ]
        reply_markup = ReplyKeyboardMarkup(role_keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "👤 **Давайте настроим ваш профиль**\n\n"
            "❓ **Кто вы?** Выберите вариант ниже или напишите свой:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ProfileStates.ROLE

    async def get_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получает роль пользователя и запрашивает вуз"""
        role = update.message.text
        context.user_data['role'] = role
        
        # Создаем клавиатуру с популярными вузами Оренбурга
        university_keyboard = [
            [KeyboardButton("🏛️ Оренбургский государственный университет")],
            [KeyboardButton("🌾 Оренбургский государственный аграрный университет")],
            [KeyboardButton("⚕️ Оренбургский государственный медицинский университет")],
            [KeyboardButton("📚 Оренбургский государственный педагогический университет")],
            [KeyboardButton("🎭 Оренбургский государственный институт искусств")],
            [KeyboardButton("🏫 Другой вуз")]
        ]
        reply_markup = ReplyKeyboardMarkup(university_keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"✅ **Роль сохранена:** {role}\n\n"
            "🏫 **Из какого вы вуза?** Выберите вариант ниже или напишите свой:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ProfileStates.UNIVERSITY

    async def get_university(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получает вуз пользователя и сохраняет профиль"""
        university = update.message.text
        user = update.message.from_user
        
        # Сохраняем данные пользователя
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': context.user_data.get('role'),
            'university': university
        }
        
        self.db.save_user(user_data)
        
        # Показываем главное меню вместо удаления клавиатуры
        reply_markup = self.get_main_menu_keyboard()
        
        await update.message.reply_text(
            f"🎉 **Профиль успешно сохранен!**\n\n"
            f"👤 **Роль:** {context.user_data.get('role')}\n"
            f"🏫 **Вуз:** {university}\n\n"
            f"Теперь вы можете использовать все функции бота!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Очищаем временные данные
        context.user_data.clear()
        
        return ConversationHandler.END

    async def cancel_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменяет настройку профиля"""
        await update.message.reply_text(
            "❌ Настройка профиля отменена.\n"
            "Вы можете настроить профиль позже с помощью команды /profile",
            reply_markup=ReplyKeyboardRemove()
        )
        
        context.user_data.clear()
        return ConversationHandler.END

    async def show_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает текущий профиль пользователя"""
        user = update.message.from_user
        user_profile = self.db.get_user(user.id)
        
        if not user_profile:
            await update.message.reply_text(
                "📝 Профиль не настроен. Введите /profile чтобы настроить профиль."
            )
            return
        
        profile_text = self.formatter.format_user_profile(user_profile)
        await update.message.reply_text(profile_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 **Помощь по командам:**

/start - Начать работу с ботом
/profile - Настроить или изменить профиль
/myprofile - Показать мой профиль
/menu - Показать главное меню

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

📱 **Главное меню:**
Используйте кнопки меню для быстрого доступа к функциям!
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
            # Показываем инструкцию по использованию поиска с клавиатурой "Главное меню"
            reply_markup = self.get_back_to_menu_keyboard()
            await update.message.reply_text(
                "🔍 **Использование поиска:**\n/search <ключевые слова>\n\nПример: /search конференция студенты",
                reply_markup=reply_markup
            )
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
        
        # Создаем клавиатуру для возврата в меню
        menu_keyboard = self.get_back_to_menu_keyboard()
        
        if not events:
            await update.message.reply_text(
                f"🔍 По запросу '{search_query}' ничего не найдено.",
                reply_markup=menu_keyboard
            )
            return
        
        if len(events) == 1:
            message = self.formatter.format_event_message(events[0])
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=menu_keyboard
            )
        else:
            message = f"🔍 **Найдено мероприятий: {len(events)}**\n\n"
            reply_markup = self.keyboards.create_search_results_keyboard(events)
            await update.message.reply_text(message, reply_markup=reply_markup)
            
            # Также показываем кнопку "Главное меню" для удобства
            await update.message.reply_text(
                "Вы можете вернуться в главное меню:",
                reply_markup=menu_keyboard
            )

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
