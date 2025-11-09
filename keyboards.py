from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import json

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Все события", callback_data="all_events")],
        [InlineKeyboardButton("🔍 Поиск событий", callback_data="search_events")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔄 Сбросить профиль", callback_data="reset_profile")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_events_type_keyboard():
    from database import get_event_types
    
    # Без пользовательских данных, показываем все типы
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

def get_role_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎓 Студент", callback_data="student")],
        [InlineKeyboardButton("👨‍🏫 Преподаватель", callback_data="teacher")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_reset_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Да, сбросить", callback_data="confirm_reset")],
        [InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_reset")],
    ]
    return InlineKeyboardMarkup(keyboard)

def load_universities_from_sources():
    """Загружает университеты из sources.json"""
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            sources = json.load(f)
        
        universities = {}
        for source in sources:
            name = source['name']
            # Создаем код из названия (первые буквы слов)
            code = ''.join(word[0].lower() for word in name.split() if word[0].isalpha())
            universities[code] = name
        
        return universities
    except Exception as e:
        print(f"Ошибка загрузки universities: {e}")
        # Возвращаем стандартный список в случае ошибки
        return {
            "osu": "ОГУ",
            "ogau": "ОГАУ", 
            "orgmu": "ОрГМУ",
            "ospu": "ОГПУ",
            "osi": "ОГИИ",
            "ormc": "ООМК",
            "ogk": "ОГК"
        }

def get_university_keyboard():
    universities = load_universities_from_sources()
    
    # Словарь официальных сокращений
    university_short_names = {
        "osu": "ОГУ",
        "ogau": "ОГАУ", 
        "orgmu": "ОрГМУ",
        "ospu": "ОГПУ",
        "osi": "ОГИИ",
        "ormc": "ООМК",
        "ogk": "ОГК"
    }
    
    keyboard = []
    row = []
    for code, name in universities.items():
        # Используем официальные сокращения
        short_name = university_short_names.get(code, name)
        
        row.append(InlineKeyboardButton(short_name, callback_data=f"uni_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def get_faculty_keyboard(university_code=None):
    """Возвращает клавиатуру с факультетами для выбранного университета"""
    
    # Факультеты ОГУ
    osu_faculties = {
        "asf": "АСФ",
        "aki": "АКИ", 
        "imit": "ИМИТ",
        "imep": "ИМЭП",
        "inozem": "ИНоЗем",
        "inpo": "ИНПО",
        "ion": "ИОН",
        "iro": "ИРО",
        "iees": "ИЭЭС",
        "iyak": "ИЯК",
        "tf": "ТФ",
        "fop": "ФОП",
        "fpig": "ФПИГ",
        "fpbi": "ФПБИ",
        "fizf": "ФизФ",
        "hbf": "ХБФ",
        "yuf": "ЮФ"
    }
    
    # Факультеты медицинского университета
    orgmu_faculties = {
        "med": "ЛФ",
        "ped": "ПФ", 
        "stom": "СТФ",
        "farm": "ФармФ",
        "nurse": "ФСД"
    }
    
    # Факультеты аграрного университета
    ogau_faculties = {
        "agro": "АФ",
        "vet": "ВФ",
        "zoo": "ЗФ", 
        "soil": "ПФ",
        "eco": "ЭФ"
    }
    
    # Факультеты педагогического университета
    ospu_faculties = {
        "preschool": "ФДО",
        "primary": "ФНО",
        "phil": "ФФ",
        "hist": "ИФ",
        "math": "ФМ",
        "sport": "ФФК"
    }
    
    # Факультеты института искусств
    osi_faculties = {
        "music": "ФМИ",
        "theater": "ФТИ",
        "folk": "ФНК",
        "dance": "ФХ",
        "visual": "ФИИ"
    }
    
    # Факультеты медицинского колледжа
    ormc_faculties = {
        "nurse": "СД",
        "med": "ЛД",
        "farm": "Фарм",
        "prophylaxis": "МП"
    }
    
    # Факультеты государственного колледжа
    ogk_faculties = {
        "tech": "ТО",
        "programming": "ОП",
        "econom": "ЭО",
        "design": "ДО"
    }
    
    # Определяем факультеты по коду университета
    faculties_map = {
        "osu": osu_faculties,
        "orgmu": orgmu_faculties,
        "ogau": ogau_faculties,
        "ospu": ospu_faculties,
        "osi": osi_faculties,
        "ormc": ormc_faculties,
        "ogk": ogk_faculties
    }
    
    # Получаем факультеты для выбранного университета
    faculties = faculties_map.get(university_code, {})
    
    # ВСЕГДА возвращаем клавиатуру, даже если она пустая
    keyboard = []
    row = []
    for code, short_name in faculties.items():
        row.append(InlineKeyboardButton(short_name, callback_data=f"fac_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Если нет факультетов, добавляем сообщение об этом
    if not keyboard:
        keyboard.append([InlineKeyboardButton("❌ Нет доступных факультетов", callback_data="no_faculty")])
    
    return InlineKeyboardMarkup(keyboard)

def get_course_keyboard():
    keyboard = []
    row = []
    for i in range(1, 7):  # Курсы 1-6
        row.append(InlineKeyboardButton(str(i), callback_data=str(i)))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку для аспирантуры
    keyboard.append([InlineKeyboardButton("Аспирантура", callback_data="aspirant")])
    
    return InlineKeyboardMarkup(keyboard)

# Словари для преобразования кодов в полные названия
UNIVERSITIES = load_universities_from_sources()

# Словарь полных названий факультетов
FACULTIES_FULL = {
    # ОГУ факультеты
    "asf": "Архитектурно-строительный факультет",
    "aki": "Аэрокосмический институт", 
    "imit": "Институт математики и информационных технологий",
    "imep": "Институт менеджмента, экономики и предпринимательства",
    "inozem": "Институт наук о Земле",
    "inpo": "Институт непрерывного профессионального образования ОГУ",
    "ion": "Институт общественных наук",
    "iro": "Институт развития образования",
    "iees": "Институт энергетики, электроники и связи",
    "iyak": "Институт языков и культур",
    "tf": "Транспортный факультет",
    "fop": "Факультет общественных профессий",
    "fpig": "Факультет подготовки иностранных граждан",
    "fpbi": "Факультет прикладной биотехнологии и инженерии",
    "fizf": "Физический факультет",
    "hbf": "Химико-биологический факультет",
    "yuf": "Юридический факультет",
    
    # Медицинские факультеты
    "med": "Лечебный факультет",
    "ped": "Педиатрический факультет", 
    "stom": "Стоматологический факультет",
    "farm": "Фармацевтический факультет",
    "nurse": "Факультет сестринского дела",
    
    # Аграрные факультеты
    "agro": "Агрономический факультет",
    "vet": "Ветеринарный факультет",
    "zoo": "Зоотехнический факультет", 
    "soil": "Почвоведческий факультет",
    "eco": "Экологический факультет",
    
    # Педагогические факультеты
    "preschool": "Факультет дошкольного образования",
    "primary": "Факультет начального образования",
    "phil": "Филологический факультет",
    "hist": "Исторический факультет",
    "math": "Факультет математики",
    "sport": "Факультет физической культуры",
    
    # Факультеты искусств
    "music": "Факультет музыкального искусства",
    "theater": "Факультет театрального искусства",
    "folk": "Факультет народной культуры",
    "dance": "Факультет хореографии",
    "visual": "Факультет изобразительного искусства",
    
    # Факультеты медицинского колледжа
    "nurse": "Сестринское дело",
    "med": "Лечебное дело",
    "farm": "Фармация",
    "prophylaxis": "Медико-профилактическое дело",
    
    # Факультеты государственного колледжа
    "tech": "Техническое отделение",
    "programming": "Отделение программирования",
    "econom": "Экономическое отделение",
    "design": "Отделение дизайна"
}

# Словарь сокращений факультетов
FACULTIES_SHORT = {
    # ОГУ факультеты
    "asf": "АСФ",
    "aki": "АКИ", 
    "imit": "ИМИТ",
    "imep": "ИМЭП",
    "inozem": "ИНоЗем",
    "inpo": "ИНПО",
    "ion": "ИОН",
    "iro": "ИРО",
    "iees": "ИЭЭС",
    "iyak": "ИЯК",
    "tf": "ТФ",
    "fop": "ФОП",
    "fpig": "ФПИГ",
    "fpbi": "ФПБИ",
    "fizf": "ФизФ",
    "hbf": "ХБФ",
    "yuf": "ЮФ",
    
    # Медицинские факультеты
    "med": "ЛФ",
    "ped": "ПФ", 
    "stom": "СТФ",
    "farm": "ФармФ",
    "nurse": "ФСД",
    
    # Аграрные факультеты
    "agro": "АФ",
    "vet": "ВФ",
    "zoo": "ЗФ", 
    "soil": "ПФ",
    "eco": "ЭФ",
    
    # Педагогические факультеты
    "preschool": "ФДО",
    "primary": "ФНО",
    "phil": "ФФ",
    "hist": "ИФ",
    "math": "ФМ",
    "sport": "ФФК",
    
    # Факультеты искусств
    "music": "ФМИ",
    "theater": "ФТИ",
    "folk": "ФНК",
    "dance": "ФХ",
    "visual": "ФИИ",
    
    # Факультеты медицинского колледжа
    "nurse": "СД",
    "med": "ЛД",
    "farm": "Фарм",
    "prophylaxis": "МП",
    
    # Факультеты государственного колледжа
    "tech": "ТО",
    "programming": "ОП",
    "econom": "ЭО",
    "design": "ДО"
}

def get_university_name(code):
    """Получить полное название университета по коду"""
    return UNIVERSITIES.get(code, code)

def get_university_short_name(code):
    """Получить сокращенное название университета по коду"""
    short_names = {
        "osu": "ОГУ",
        "ogau": "ОГАУ", 
        "orgmu": "ОрГМУ",
        "ospu": "ОГПУ",
        "osi": "ОГИИ",
        "ormc": "ООМК",
        "ogk": "ОГК"
    }
    return short_names.get(code, code)

def get_faculty_name(code, university_code=None):
    """Получить полное название факультета по коду"""
    return FACULTIES_FULL.get(code, code)

def get_faculty_short_name(code, university_code=None):
    """Получить сокращенное название факультета по коду"""
    return FACULTIES_SHORT.get(code, code)
