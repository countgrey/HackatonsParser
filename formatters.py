def format_events_list(events_df):
    if events_df.empty:
        return "❌ События не найдены"
    
    message = "📅 <b>Найденные события:</b>\n\n"
    for idx, event in events_df.iterrows():
        title = event['title'] or "Без названия"
        date = event['date'] or "Дата не указана"
        event_type = event['detected_type'] or "Не определен"
        
        message += f"{idx + 1}. <b>{title}</b>\n"
        message += f"   📅 {date} | 🏷️ {event_type}\n"
        message += f"   🔗 <a href='{event['link']}'>Подробнее</a>\n\n"
    
    return message

def format_stats(stats):
    if stats['total_events'] == 0:
        return "❌ В базе данных пока нет событий"
    
    stats_text = f"📈 <b>Статистика событий:</b>\n\n"
    stats_text += f"📊 Всего событий: <b>{stats['total_events']}</b>\n"
    
    if stats['last_update']:
        stats_text += f"📅 Последнее обновление: <b>{stats['last_update']}</b>\n\n"
    else:
        stats_text += "\n"
    
    stats_text += "<b>Распределение по типам:</b>\n"
    
    for _, row in stats['type_stats'].iterrows():
        stats_text += f"• {row['detected_type']}: <b>{row['count']}</b>\n"
    
    return stats_text

def format_event_types(event_types):
    if not event_types:
        return "❌ В базе данных пока нет событий"
    
    types_text = "📊 <b>Доступные типы событий:</b>\n\n" + "\n".join(
        f"• {event_type}" for event_type in event_types
    )
    
    return types_text
