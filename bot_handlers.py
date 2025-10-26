from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from database import get_events_by_type, get_event_types, search_events, get_stats
from parser_utils import run_parser
from keyboards import get_main_keyboard, get_back_keyboard, get_events_type_keyboard
from formatters import format_events_list, format_stats, format_event_types

# --- Команды бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.reply_html(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для отслеживания мероприятий ОГУ.\n"
        "Я могу показать вам актуальные события: хакатоны, олимпиады, конференции и многое другое!\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу с ботом\n"
        "/events - Показать последние события\n"
        "/search - Поиск событий\n"
        "/types - Показать типы событий\n"
        "/update - Обновить данные (запустить парсер)\n"
        "/stats - Статистика\n"
        "/help - Эта справка\n\n"
        "🔍 <b>Примеры поиска:</b>\n"
        "• <code>/search хакатон</code>\n"
        "• <code>/search олимпиада программирование</code>\n"
        "• <code>/search конференция апрель</code>"
    )
    await update.message.reply_html(help_text, reply_markup=get_back_keyboard())

async def show_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_types = get_event_types()
    
    if not event_types:
        await update.message.reply_html(
            "❌ В базе данных пока нет событий.\n"
            "Используйте /update для обновления данных.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await update.message.reply_html(
        "🎯 <b>Выберите тип событий:</b>",
        reply_markup=get_events_type_keyboard()
    )

async def show_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_types = get_event_types()
    types_text = format_event_types(event_types)
    await update.message.reply_html(types_text, reply_markup=get_back_keyboard())

async def update_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Без кнопки "Назад" во время процесса обновления
    message = await update.message.reply_text(
        "🔄 Запускаю парсер... Это может занять несколько минут..."
    )
    
    success, output = run_parser()
    
    if success:
        if len(output) > 1000:
            output = output[:1000] + "..."
        
        result_message = await message.edit_text(
            f"✅ <b>Данные успешно обновлены!</b>\n\n"
            f"<code>{output}</code>",
            parse_mode='HTML'
        )
    else:
        result_message = await message.edit_text(
            f"❌ <b>Ошибка при обновлении данных:</b>\n\n"
            f"<code>{output}</code>",
            parse_mode='HTML'
        )
    
    # Пауза 3 секунды перед возвратом в главное меню
    await asyncio.sleep(3)
    
    # Автоматический возврат в главное меню
    await result_message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    stats_text = format_stats(stats)
    await update.message.reply_html(stats_text, reply_markup=get_back_keyboard())

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    events_df = search_events(search_query)
    
    if events_df.empty:
        await update.message.reply_html(
            f"❌ По запросу '<b>{search_query}</b>' ничего не найдено",
            reply_markup=get_back_keyboard()
        )
        return
    
    message = f"🔍 <b>Результаты поиска по запросу:</b> '{search_query}'\n\n"
    message += format_events_list(events_df)
    
    await update.message.reply_html(message, reply_markup=get_back_keyboard())

# --- Обработчики callback ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main":
        # Возврат в главное меню
        await query.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        return
    
    elif data == "all_events":
        events_df = get_events_by_type("all", limit=10)
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
    
    elif data == "update_data":
        # Без кнопки "Назад" во время процесса обновления
        await query.edit_message_text(
            "🔄 Запускаю парсер...",
            reply_markup=None  # Убираем все кнопки
        )
        
        success, output = run_parser()
        
        if success:
            result_message = await query.edit_message_text(
                f"✅ <b>Данные успешно обновлены!</b>",
                parse_mode='HTML'
            )
        else:
            result_message = await query.edit_message_text(
                f"❌ <b>Ошибка при обновлении данных</b>",
                parse_mode='HTML'
            )
        
        # Пауза 3 секунды перед возвратом в главное меню
        await asyncio.sleep(3)
        
        # Автоматический возврат в главное меню
        await result_message.edit_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    
    elif data == "stats":
        stats = get_stats()
        
        if stats['total_events'] == 0:
            await query.edit_message_text(
                "❌ В базе данных пока нет событий",
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
            events_df = get_events_by_type(limit=10)
            title = "Все события"
        else:
            events_df = get_events_by_type(event_type, limit=10)
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
