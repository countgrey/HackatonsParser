#!/usr/bin/env python3
# generate_sources.py
"""
Генератор sources.json для парсера мероприятий.
- Собирает организации (в т.ч. вузы) из Википедии (категории по России).
- Для каждой организации пытается взять официальный сайт и найти страницу новостей/мероприятий.
- Дополняет список агрегаторами хакатонов/мероприятий.
- Сохраняет sources.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse
import re

# Настройки HTTP
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EventSourceBot/1.0; +https://example.com)"
}
TIMEOUT = 10
SLEEP_BETWEEN = 0.5  # пауза между запросами (чтобы не нагружать)

# Категории Википедии для поиска организаций/университетов (можно расширить)
WIKI_CATEGORY_URLS = [
    "https://ru.wikipedia.org/wiki/Категория:Университеты_России",
    "https://ru.wikipedia.org/wiki/Категория:Высшие_учебные_заведения_России",
    "https://ru.wikipedia.org/wiki/Категория:Технические_высшие_учебные_заведения_России",
    "https://ru.wikipedia.org/wiki/Категория:Педагогические_высшие_учебные_завения_России",
    # Добавляй другие категории при необходимости
]

# Типичные пути, где могут быть новости/мероприятия
COMMON_PATHS = [
    "/news", "/novosti", "/events", "/events/", "/afisha", "/announcements",
    "/press", "/press-center", "/press-center/news", "/about/news", "/doc",
    "/news.php", "/news.html", "/index.php?do=cat&category=Новости"
]

# Ключевые слова для обнаружения страницы новостей/мероприятий
NEWS_KEYWORDS = [
    "новост", "мероприят", "конференц", "хакатон", "олимпиад", "фестиваль",
    "семинар", "мастер-класс", "вебинар", "конкурс", "соревновани"
]


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        # не печатаем много ошибок, чтобы лог не захламлялся
        return None


def find_wiki_pages_from_category(cat_url, limit=200):
    """
    Собирает ссылки на страницы статей из категории Википедии.
    Ограничение limit — максимум страниц, которые вернём.
    """
    results = []
    next_url = cat_url
    while next_url and len(results) < limit:
        html = fetch(next_url)
        time.sleep(SLEEP_BETWEEN)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        for li in soup.select(".mw-category-group li a"):
            href = li.get("href")
            title = li.get_text(strip=True)
            if href:
                full = "https://ru.wikipedia.org" + href
                results.append({"title": title, "wiki_url": full})
                if len(results) >= limit:
                    break
        # Пробуем найти ссылку "следующая страница"
        next_link = soup.select_one("a[title^='Категория:'][rel='next']")
        if next_link:
            next_url = "https://ru.wikipedia.org" + next_link.get("href")
        else:
            next_url = None
    return results


def extract_official_site_from_wiki(wiki_html):
    """
    По HTML страницы статьи Википедии пытаемся извлечь официальный сайт и город.
    Ищем в инфобоксе <table class="infobox">, в строке 'Веб-сайт' или similar.
    """
    soup = BeautifulSoup(wiki_html, "html.parser")
    info = soup.select_one(".infobox, .infobox_v3, table.infobox")
    site = None
    city = None
    if info:
        # ищем ссылку с атрибутом rel="nofollow" или просто любую внешнюю ссылку в инфобоксе
        a = info.find('a', href=True)
        if a and a['href'].startswith("http"):
            site = a['href']
        # попытка найти город: ищем строки инфобокса, где есть 'Город' или 'Расположение'
        for row in info.find_all(['tr', 'div']):
            txt = row.get_text(" ", strip=True).lower()
            if 'город' in txt or 'расположен' in txt or 'местонахожд' in txt:
                # достаём ближайшую ссылку или текст
                city_text = txt
                # извлечь название города (простейшая попытка)
                m = re.search(r'город[:\s]*([^\n,;]+)', city_text)
                if m:
                    city = m.group(1).strip().capitalize()
                else:
                    # fallback: берем первые слова
                    city = city_text.split()[0].capitalize()
                break
    # fallback: искать "Официальный сайт" в тексте
    if not site:
        outlinks = soup.select("a.external")
        for a in outlinks:
            href = a.get("href")
            if href and href.startswith("http"):
                site = href
                break
    return site, city


def probe_for_news_path(base_url):
    """
    Для домена base_url перебираем COMMON_PATHS и пытаемся найти подходящую страницу новостей.
    Возвращаем найденный URL или None.
    """
    parsed = urlparse(base_url)
    scheme = parsed.scheme if parsed.scheme else "https"
    netloc = parsed.netloc if parsed.netloc else parsed.path  # если передали bare domain
    if not netloc:
        return None

    root = f"{scheme}://{netloc}"
    candidates = []
    # если base_url уже выглядит как страница, добавим его как кандидат
    candidates.append(base_url)
    for p in COMMON_PATHS:
        candidates.append(urljoin(root, p))

    for url in candidates:
        html = fetch(url)
        time.sleep(SLEEP_BETWEEN)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()
        # проверяем наличие ключевых слов или селекторов блоков новостей
        kw_score = sum(1 for kw in NEWS_KEYWORDS if kw in text)
        has_news_blocks = bool(soup.select("article, .news-item, .news-list, .item, .post"))
        if kw_score >= 1 or has_news_blocks:
            # дополнительно проверим, что страница не просто главная страница без контента
            # и что она возвращает HTTP 200 (fetch это уже проверил)
            return url
    return None


def normalize_site(url):
    """Приводит URL к базовому виду (схема + домен)."""
    try:
        p = urlparse(url)
        if not p.scheme:
            url = "https://" + url
            p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
    except:
        return url


def build_sources(output_file="sources.json", limit_per_category=200):
    sources = []

    # 1) Сначала — агрегаторы и хакатон-ресурсы (статический список, можно расширить)
    aggregator_seeds = [
        {"name": "TimePad", "city": "онлайн", "audience": "студент", "news_url": "https://timepad.ru/"},
        {"name": "Hackathons.ru", "city": "онлайн", "audience": "студент", "news_url": "https://hackathons.ru/"},
        {"name": "Habr (поиск хакатонов)", "city": "онлайн", "audience": "студент", "news_url": "https://habr.com/ru/search/?q=хакатон"},
        {"name": "Devpost (международные хакатоны)", "city": "онлайн", "audience": "студент", "news_url": "https://devpost.com/"}
    ]
    sources.extend(aggregator_seeds)

    # 2) Сбор страниц из Википедии по категориям
    seen_sites = set()
    for cat in WIKI_CATEGORY_URLS:
        print("[WIKI] Обрабатываем категорию:", cat)
        pages = find_wiki_pages_from_category(cat, limit=limit_per_category)
        for p in pages:
            wiki_html = fetch(p["wiki_url"])
            time.sleep(SLEEP_BETWEEN)
            if not wiki_html:
                continue
            site, city = extract_official_site_from_wiki(wiki_html)
            if not site:
                continue
            site_norm = normalize_site(site)
            if site_norm in seen_sites:
                continue
            # пробуем найти страницу новостей
            news_page = probe_for_news_path(site_norm)
            print("  -> Найден сайт:", site_norm, " news:", news_page)
            src = {
                "name": p["title"],
                "city": city if city else "Не указано",
                "audience": "студент",
                "news_url": news_page if news_page else site_norm,
                "doc_urls": []
            }
            sources.append(src)
            seen_sites.add(site_norm)

    # 3) Уникализируем по news_url
    unique = []
    seen = set()
    for s in sources:
        key = s.get("news_url") or s.get("name")
        if key and key not in seen:
            unique.append(s)
            seen.add(key)

    # 4) Сохранение
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Сохранено {len(unique)} источников в {output_file}")
    return unique


if __name__ == "__main__":
    build_sources("sources.json")
