from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Все события", callback_data="all_events")],
        [InlineKeyboardButton("🔍 Поиск событий", callback_data="search_events")],
        [InlineKeyboardButton("🔄 Обновить данные", callback_data="update_data")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_events_type_keyboard():
    from database import get_event_types
    
    event_types = get_event_types()
    keyboard = []
    
    if not event_types:
        return get_back_keyboard()
    
    row = []
    for i, event_type in enumerate(event_types):
        row.append(InlineKeyboardButton(event_type, callback_data=f"type_{event_type}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("📋 Все события", callback_data="type_all")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(keyboard)
