from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class KeyboardManager:
    def create_events_keyboard(self, events, page, total_pages, total_count):
        """Создать клавиатуру для списка мероприятий"""
        keyboard = []
        for event in events:
            title = event['title'][:30] + "..." if len(event['title']) > 30 else event['title']
            date_str = f" ({event['date_start']})" if event['date_start'] else ""
            button_text = f"{title}{date_str}"
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"event_{event['id']}"
            )])
        
        # Кнопки пагинации
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page"))
        
        if (page + 1) * len(events) < total_count:
            pagination_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        return InlineKeyboardMarkup(keyboard)

    def create_search_results_keyboard(self, events):
        """Создать клавиатуру для результатов поиска"""
        keyboard = []
        for event in events:
            title = event['title'][:35] + "..." if len(event['title']) > 35 else event['title']
            button_text = f"{title}"
            if event['date_start']:
                button_text += f" ({event['date_start']})"
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"event_{event['id']}"
            )])
        
        return InlineKeyboardMarkup(keyboard)

    def create_event_details_keyboard(self):
        """Создать клавиатуру для деталей мероприятия"""
        keyboard = [[InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_list")]]
        return InlineKeyboardMarkup(keyboard)
