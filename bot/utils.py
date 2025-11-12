import json

class MessageFormatter:
    def format_event_message(self, event):
        """Форматирование информации о мероприятии для отправки"""
        # Обработка audience (может быть строкой JSON или просто строкой)
        audience = event['audience']
        if audience and audience.startswith('['):
            try:
                audience_list = json.loads(audience)
                audience = ', '.join(audience_list) if audience_list else "Не указана"
            except:
                audience = str(audience)
        
        # Форматирование дат
        date_start = event['date_start'] or "Не указана"
        date_end = event['date_end'] or "Не указана"
        reg_end = event['reg_end'] or "Не указана"
        
        # Определение эмодзи для типа мероприятия
        type_emoji = {
            'Конференция': '🎤',
            'Семинар': '💡', 
            'Хакатон': '💻',
            'Конкурс': '🏆',
            'Олимпиада': '🧠',
            'Выставка': '🖼️',
            'Форум': '👥'
        }.get(event['type'], '📅')
        
        message = f"""
{type_emoji} **{event['title']}**

🏷️ **Тип:** {event['type']}
🏙️ **Город:** {event['city']}
👥 **Аудитория:** {audience}
🏢 **Организатор:** {event['organizer']}

📅 **Даты проведения:** {date_start} - {date_end}
⏰ **Регистрация до:** {reg_end}
{'👥 **Требуется команда**' if event['team_required'] else '✅ **Индивидуальное участие**'}

🔗 **Ссылка:** {event['link']}
        """
        
        return message
