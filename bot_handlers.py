from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import asyncio
from database import get_events_by_type, get_event_types, search_events, get_stats, get_user, save_user, user_exists, delete_user
from keyboards import (
    get_main_keyboard, get_back_keyboard, get_events_type_keyboard, 
    get_role_keyboard, get_course_keyboard, get_university_keyboard, 
    get_faculty_keyboard, get_university_name, get_faculty_name,
    get_reset_confirmation_keyboard, get_university_short_name, get_faculty_short_name
)
from formatters import format_events_list, format_stats, format_event_types

# Состояния для ConversationHandler
ROLE, UNIVERSITY, FACULTY, COURSE = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем, зарегистрирован ли пользователь
    user_data = get_user(user.id)
    
    if not user_data:
        # Начинаем процесс регистрации
        await update.message.reply_html(
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот для отслеживания мероприятий ОГУ.\n"
            "Для начала давай настроим твой профиль, чтобы показывать тебе релевантные события.\n\n"
            "📝 <b>Выбери свою роль:</b>",
            reply_markup=get_role_keyboard()
        )
        return ROLE
    else:
        # Пользователь уже зарегистрирован
        context.user_data['user_profile'] = user_data
        
        # Получаем сокращенные названия для отображения
        university_short = get_university_short_name(user_data.get('university_code', '')) if user_data.get('university_code') else user_data.get('university', 'Не указан')
        faculty_short = get_faculty_short_name(user_data.get('faculty_code', '')) if user_data.get('faculty_code') else user_data.get('faculty', 'Не указан')
        
        await update.message.reply_html(
            f"👋 С возвращением, {user.first_name}!\n\n"
            f"📊 Твой профиль:\n"
            f"• Роль: {user_data['role']}\n"
            f"• Университет: {university_short}\n"
            f"• Факультет: {faculty_short}\n"
            f"• Курс: {user_data['course'] or 'Не указан'}\n\n"
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

async def register_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    role = query.data
    context.user_data['role'] = role
    
    await query.edit_message_text(
        "🎓 <b>Выберите ваш университет:</b>",
        parse_mode='HTML',
        reply_markup=get_university_keyboard()
    )
    return UNIVERSITY

async def register_university(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('uni_'):
        university_code = query.data[4:]  # Убираем префикс 'uni_'
        
        university_name = get_university_name(university_code)
        university_short = get_university_short_name(university_code)
        
        context.user_data['university'] = university_name
        context.user_data['university_short'] = university_short
        context.user_data['university_code'] = university_code
        
        # Получаем клавиатуру факультетов для выбранного университета
        faculty_keyboard = get_faculty_keyboard(university_code)
        
        # ВСЕГДА показываем выбор факультета
        await query.edit_message_text(
            f"🏛️ <b>Выберите ваш факультет ({university_short}):</b>",
            parse_mode='HTML',
            reply_markup=faculty_keyboard
        )
        return FACULTY

async def register_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('fac_'):
        faculty_code = query.data[4:]  # Убираем префикс 'fac_'
        university_code = context.user_data.get('university_code')
        
        # Обрабатываем случай, когда нет доступных факультетов
        if faculty_code == "no_faculty":
            context.user_data['faculty'] = "Не указан"
            context.user_data['faculty_short'] = "Не указан"
            context.user_data['faculty_code'] = None
            
            if context.user_data['role'] == 'student':
                await query.edit_message_text(
                    "📚 <b>Выберите ваш курс:</b>",
                    reply_markup=get_course_keyboard(),
                    parse_mode='HTML'
                )
                return COURSE
            else:
                return await complete_registration(update, context)
        else:
            faculty_name = get_faculty_name(faculty_code, university_code)
            faculty_short = get_faculty_short_name(faculty_code, university_code)
            
            context.user_data['faculty'] = faculty_name
            context.user_data['faculty_short'] = faculty_short
            context.user_data['faculty_code'] = faculty_code
            
            if context.user_data['role'] == 'student':
                await query.edit_message_text(
                    "📚 <b>Выберите ваш курс:</b>",
                    reply_markup=get_course_keyboard(),
                    parse_mode='HTML'
                )
                return COURSE
            else:
                return await complete_registration(update, context)

async def register_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    course = query.data
    # Преобразуем "aspirant" в специальное значение
    if course == "aspirant":
        context.user_data['course'] = "Аспирантура"
    else:
        context.user_data['course'] = int(course)
    
    return await complete_registration(update, context)

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    profile_data = context.user_data
    
    # Сохраняем пользователя
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': profile_data['role'],
        'university': profile_data['university'],
        'university_short': profile_data.get('university_short', profile_data['university']),
        'university_code': profile_data.get('university_code'),
        'faculty': profile_data.get('faculty', 'Не указан'),
        'faculty_short': profile_data.get('faculty_short', profile_data.get('faculty', 'Не указан')),
        'faculty_code': profile_data.get('faculty_code'),
        'course': profile_data.get('course')
    }
    
    save_user(user_data)
    
    if isinstance(update, Update) and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    # Формируем текст профиля с сокращениями
    profile_text = "✅ <b>Регистрация завершена!</b>\n\n📊 Ваш профиль:\n"
    profile_text += f"• Роль: {user_data['role']}\n"
    profile_text += f"• Университет: {user_data['university_short']}\n"
    
    if user_data.get('faculty_short') and user_data['faculty_short'] != 'Не указан':
        profile_text += f"• Факультет: {user_data['faculty_short']}\n"
    
    if user_data['role'] == 'student':
        profile_text += f"• Курс: {user_data.get('course', 'Не указан')}\n"
    
    profile_text += "\nТеперь я буду показывать вам события, релевантные вашему профилю."
    
    await message.reply_html(
        profile_text,
        reply_markup=get_main_keyboard()
    )
    
    context.user_data['user_profile'] = user_data
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "❌ Регистрация отменена.\n\n"
        "Вы всегда можете начать заново с помощью команды /start",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def reset_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для сброса профиля пользователя"""
    user = update.effective_user
    
    await update.message.reply_html(
        "🔄 <b>Сброс профиля</b>\n\n"
        "Вы уверены, что хотите сбросить свой профиль?\n"
        "Все ваши данные будут удалены, и вам придется пройти регистрацию заново.",
        reply_markup=get_reset_confirmation_keyboard()
    )

async def reset_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс профиля пользователя"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "confirm_reset":
        # Удаляем пользователя из базы данных
        success = delete_user(user.id)
        
        if success:
            await query.edit_message_text(
                "✅ <b>Профиль успешно сброшен!</b>\n\n"
                "Теперь вы можете пройти регистрацию заново с помощью команды /start",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ <b>Ошибка при сбросе профиля</b>\n\n"
                "Профиль не найден или уже был удален.",
                parse_mode='HTML'
            )
    else:
        # Отмена сброса
        await query.edit_message_text(
            "❌ <b>Сброс профиля отменен</b>\n\n"
            "Ваши данные сохранены.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/profile - Показать/изменить профиль\n"
        "/reset - Сбросить профиль\n"
        "/events - Показать последние события\n"
        "/search - Поиск событий\n"
        "/types - Показать типы событий\n"
        "/stats - Статистика\n"
        "/help - Эта справка\n\n"
        "🔍 <b>Примеры поиска:</b>\n"
        "• <code>/search хакатон</code>\n"
        "• <code>/search олимпиада программирование</code>\n"
        "• <code>/search конференция апрель</code>"
    )
    await update.message.reply_html(help_text, reply_markup=get_back_keyboard())

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        await update.message.reply_html(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Используем сокращенные названия для отображения
    university_display = user_data.get('university_short', user_data.get('university', 'Не указан'))
    faculty_display = user_data.get('faculty_short', user_data.get('faculty', 'Не указан'))
    
    profile_text = "👤 <b>Ваш профиль:</b>\n\n"
    profile_text += f"• Роль: {user_data['role']}\n"
    profile_text += f"• Университет: {university_display}\n"
    
    if faculty_display != 'Не указан':
        profile_text += f"• Факультет: {faculty_display}\n"
    
    if user_data['role'] == 'student':
        profile_text += f"• Курс: {user_data.get('course', 'Не указан')}\n\n"
    else:
        profile_text += "\n"
    
    profile_text += "Чтобы изменить профиль, используйте /reset для сброса и /start для новой регистрации."
    
    await update.message.reply_html(profile_text, reply_markup=get_back_keyboard())

async def show_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        await update.message.reply_html(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    event_types = get_event_types(user_data)
    
    if not event_types:
        await update.message.reply_html(
            "❌ В базе данных пока нет событий, релевантных вашему профилю.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await update.message.reply_html(
        "🎯 <b>Выберите тип событий:</b>",
        reply_markup=get_events_type_keyboard()
    )

async def show_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        await update.message.reply_html(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    event_types = get_event_types(user_data)
    types_text = format_event_types(event_types)
    await update.message.reply_html(types_text, reply_markup=get_back_keyboard())

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        await update.message.reply_html(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    stats = get_stats(user_data)
    stats_text = format_stats(stats)
    await update.message.reply_html(stats_text, reply_markup=get_back_keyboard())

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        await update.message.reply_html(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    if not context.args:
        await update.message.reply_html(
            "🔍 <b>Поиск событий</b>\n\n"
            "Введите поисковый запрос после команды:\n"
            "<code>/search хакатон</code>\n"
            "<code>/search олимпиада программирование</code>\n"
            "<code>/search конференция</code>",
            reply_markup=get_back_keyboard()
        )
        return
    
    search_query = " ".join(context.args)
    events_df = search_events(search_query, user_data=user_data)
    
    if events_df.empty:
        await update.message.reply_html(
            f"❌ По запросу '<b>{search_query}</b>' ничего не найдено",
            reply_markup=get_back_keyboard()
        )
        return
    
    message = f"🔍 <b>Результаты поиска по запросу:</b> '{search_query}'\n\n"
    message += format_events_list(events_df)
    
    await update.message.reply_html(message, reply_markup=get_back_keyboard())

# Обработчики callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    user_data = get_user(user.id)
    
    if not user_data and data not in ["confirm_reset", "cancel_reset"]:
        await query.edit_message_text(
            "❌ Вы еще не зарегистрированы.\n"
            "Используйте /start для регистрации.",
            reply_markup=get_back_keyboard()
        )
        return
    
    if data == "back_to_main":
        await query.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        return
    
    elif data == "all_events":
        events_df = get_events_by_type("all", user_data=user_data, limit=10)
        message = format_events_list(events_df)
        await query.edit_message_text(
            message, 
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    elif data == "search_events":
        await query.edit_message_text(
            "🔍 <b>Поиск событий</b>\n\n"
            "Используйте команду /search для поиска событий.\n"
            "Например: <code>/search хакатон</code>",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    elif data == "reset_profile":
        await query.edit_message_text(
            "🔄 <b>Сброс профиля</b>\n\n"
            "Вы уверены, что хотите сбросить свой профиль?\n"
            "Все ваши данные будут удалены, и вам придется пройти регистрацию заново.",
            parse_mode='HTML',
            reply_markup=get_reset_confirmation_keyboard()
        )
    
    elif data in ["confirm_reset", "cancel_reset"]:
        await reset_profile(update, context)
        return
    
    elif data == "stats":
        stats = get_stats(user_data)
        
        if stats['total_events'] == 0:
            await query.edit_message_text(
                "❌ В базе данных пока нет событий, релевантных вашему профилю",
                reply_markup=get_back_keyboard()
            )
            return
        
        stats_text = f"📊 <b>Статистика</b>\n\n"
        stats_text += f"Всего событий: <b>{stats['total_events']}</b>\n"
        stats_text += f"Типов событий: <b>{len(stats['type_stats'])}</b>"
        
        await query.edit_message_text(
            stats_text, 
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    elif data.startswith("type_"):
        event_type = data[5:]  
        if event_type == "all":
            events_df = get_events_by_type(user_data=user_data, limit=10)
            title = "Все события"
        else:
            events_df = get_events_by_type(event_type, user_data=user_data, limit=10)
            title = f"События типа: {event_type}"
        
        if events_df.empty:
            await query.edit_message_text(
                f"❌ События типа '<b>{event_type}</b>' не найдены", 
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            return
        
        message = f"🎯 <b>{title}</b>\n\n"
        message += format_events_list(events_df)
        
        await query.edit_message_text(
            message, 
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
