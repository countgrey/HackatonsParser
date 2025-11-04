# main.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin
import sqlite3
import json
from datetime import datetime

# --- Настройки ---
OUTPUT_CSV = "osu_events.csv"
DB_NAME = "osu_events.db"
TABLE_NAME = "events"

KEYWORDS = [
    "хакатон", "hackathon", "олимпиада", "конференция", "семинар",
    "мастер-класс", "вебинар", "соревнование", "конкурс", "лекторий"
]

EXCLUDE_PHRASES = [
    "вошла в число победителей",
    "победитель",
    "награждён",
    "лауреат",
    "занял",
    "победила",
    "вручение",
    "призёр"
]

# --- HTTP сессия ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=frozenset(['GET', 'POST'])
)
adapter = HTTPAdapter(max_retries=retries)
session.mount('https://', adapter)
session.mount('http://', adapter)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# --- HTTP ---
def fetch(url):
    try:
        resp = session.get(url, headers=HEADERS, verify=False, timeout=12)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] Не удалось загрузить {url}: {e}")
        return None

def extract_text_or_none(el):
    return el.get_text(strip=True) if el else ""

# --- Парсинг ---
def parse_news_list(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    selectors = [
        "article", ".news-item", ".news-list .item", ".news", ".item", ".post", ".newsRow"
    ]
    for sel in selectors:
        found = soup.select(sel)
        if found:
            candidates.extend(found)

    if not candidates:
        main = soup.find('main') or soup.find('div', id='content') or soup
        links = main.find_all('a', href=True)
        for a in links:
            candidates.append(a)

    events = []
    seen_links = set()

    for node in candidates:
        title = ""
        link = ""
        date = ""
        description = ""

        a = None
        for tag in ("h1","h2","h3","h4","a"):
            a = node.find(tag) if hasattr(node, "find") else None
            if a and a.name == "a" or (a and a.get_text(strip=True)):
                break
            a = None

        if not a and getattr(node, "name", "") == "a":
            a = node

        if a:
            title = extract_text_or_none(a)
            raw_href = a.get("href", "")
            link = urljoin(base_url, raw_href)
        else:
            a2 = node.find('a', href=True) if hasattr(node, "find") else None
            if a2:
                title = extract_text_or_none(a2)
                link = urljoin(base_url, a2.get('href', ''))

        time_tag = node.find('time') if hasattr(node, "find") else None
        if time_tag:
            date = extract_text_or_none(time_tag)
        else:
            for cls in ("date","news-date","item-date","entry-date"):
                date_el = node.find(attrs={"class": lambda x: x and cls in x}) if hasattr(node, "find") else None
                if date_el:
                    date = extract_text_or_none(date_el)
                    break

        desc = None
        for cls in ("description","intro","lead","anons","text"):
            desc = node.find(attrs={"class": lambda x: x and cls in x}) if hasattr(node, "find") else None
            if desc:
                description = extract_text_or_none(desc)
                break
        if not description:
            p = node.find('p') if hasattr(node, "find") else None
            description = extract_text_or_none(p)

        if not title and hasattr(node, "get_text"):
            title = extract_text_or_none(node)

        if link in seen_links or (not title and not link):
            continue
        seen_links.add(link)

        events.append({
            "title": title,
            "date": date,
            "link": link,
            "description": description
        })

    return events

def parse_docs(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    events = []
    links = soup.find_all('a', href=True)
    for a in links:
        title = extract_text_or_none(a)
        link = urljoin(base_url, a['href'])
        if any(kw.lower() in title.lower() for kw in KEYWORDS):
            events.append({
                "title": title,
                "date": "",
                "link": link,
                "description": ""
            })
    return events

# --- Фильтрация ---
def is_relevant(event):
    text = " ".join([event.get("title",""), event.get("description","")]).lower()
    for phrase in EXCLUDE_PHRASES:
        if phrase.lower() in text:
            return False
    for kw in KEYWORDS:
        if kw.lower() in text:
            return True
    return False

def enrich_and_filter(events, city=None, audience="студент"):
    out = []
    for e in events:
        ttype = None
        text = " ".join([e.get("title",""), e.get("description","")]).lower()
        for kw in KEYWORDS:
            if kw.lower() in text:
                ttype = kw
                break
        e["detected_type"] = ttype if ttype else ""
        e["city"] = city if city else "онлайн"
        e["audience"] = audience
        e["date_start"] = ""
        e["date_end"] = ""
        e["reg_start"] = ""
        e["reg_end"] = ""
        e["team_required"] = 0
        e["organizer"] = ""
        e["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if is_relevant(e):
            out.append(e)
    return out

# --- SQLite ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            city TEXT,
            audience TEXT,
            type TEXT,
            description TEXT,
            date_start TEXT,
            date_end TEXT,
            reg_start TEXT,
            reg_end TEXT,
            team_required INTEGER,
            organizer TEXT,
            link TEXT UNIQUE,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def upgrade_db_schema():
    """Добавляет недостающие столбцы, если таблица уже существует"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    existing_cols = [r[1] for r in cursor.fetchall()]

    new_cols = {
        "city": "TEXT",
        "audience": "TEXT",
        "type": "TEXT",
        "date_start": "TEXT",
        "date_end": "TEXT",
        "reg_start": "TEXT",
        "reg_end": "TEXT",
        "team_required": "INTEGER",
        "organizer": "TEXT",
        "created_at": "TEXT"
    }

    for col, col_type in new_cols.items():
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col} {col_type}")
                print(f"[DB] Добавлен столбец {col}")
            except sqlite3.Error as e:
                print(f"[DB ERROR] Не удалось добавить столбец {col}: {e}")

    conn.commit()
    conn.close()

def save_events_to_db(events):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for e in events:
        try:
            cursor.execute(f"""
                INSERT OR IGNORE INTO {TABLE_NAME}
                (title, city, audience, type, description, date_start, date_end, reg_start, reg_end,
                 team_required, organizer, link, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e.get('title'), e.get('city'), e.get('audience'), e.get('detected_type'),
                e.get('description'), e.get('date_start'), e.get('date_end'),
                e.get('reg_start'), e.get('reg_end'), e.get('team_required'),
                e.get('organizer'), e.get('link'), e.get('created_at')
            ))
        except sqlite3.Error as ex:
            print(f"[ERROR] Не удалось сохранить событие {e['title']}: {ex}")
    conn.commit()
    conn.close()

# --- Загрузка источников ---
def load_sources(file_path="sources.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sources = json.load(f)
        return sources
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить sources.json: {e}")
        return []

# --- Main ---
def main():
    all_events = []
    sources = load_sources("sources.json")
    if not sources:
        print("[ERROR] Нет источников для парсинга")
        return

    init_db()
    upgrade_db_schema()

    for src in sources:
        print(f"[*] Парсим университет: {src['name']}")
        city = src.get("city", "онлайн")
        audience = src.get("audience", "студент")

        news_url = src.get("news_url")
        if news_url:
            html = fetch(news_url)
            if html:
                events = parse_news_list(html, base_url=news_url)
                all_events.extend(enrich_and_filter(events, city=city, audience=audience))

        for doc_url in src.get("doc_urls", []):
            html = fetch(doc_url)
            if html:
                events = parse_docs(html, base_url=doc_url)
                all_events.extend(enrich_and_filter(events, city=city, audience=audience))

    print(f"[*] Всего найдено событий: {len(all_events)}")
    if all_events:
        df = pd.DataFrame(all_events)
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
        save_events_to_db(all_events)
        print(f"[*] События сохранены в CSV и базу данных {DB_NAME}")
        print(df[["title","city","audience","detected_type","link"]].to_string(index=False))
    else:
        print("[*] Нет релевантных событий по ключевым словам")

if __name__ == "__main__":
    main()
