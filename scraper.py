#!/usr/bin/env python3
"""
Real Estate Scraper - SReality + Bezrealitky
Сбор объявлений о недвижимости в Чехии
"""

import requests
import pandas as pd
import time
import json
import os
import re
from datetime import datetime
from pathlib import Path

# Конфигурация
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}


def scrape_sreality(page: int = 1, limit: int = 50) -> list:
    """
    Скрапинг SReality.cz через их API v2
    category_main_cb: 1=квартиры, 2=дома, 3=участки
    category_sub_cb: 1=продажа, 2=аренда
    """
    url = "https://www.sreality.cz/api/v2/estates"
    params = {
        "page": page,
        "limit": limit,
        "category_main_cb": 1,  # Квартиры
        "category_type_cb": 1,  # Продажа (не аренда!)
        "sort": "0",            # Сортировка по дате
    }
    
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        estates = data.get("_embedded", {}).get("estates", [])
        results = []
        
        for e in estates:
            # Цена - может быть int или dict
            price = e.get("price", {})
            if isinstance(price, dict):
                price_value = price.get("value_raw") or price.get("value")
                currency = price.get("currency", "CZK")
            else:
                price_value = price
                currency = "CZK"
            
            # Площадь - парсим из названия (напр. "2+kk 58 m2")
            name = e.get("name", "")
            area_match = re.search(r'(\d+)\s*m[²²]', name, re.IGNORECASE)
            if area_match:
                area_value = int(area_match.group(1))
                area_unit = "м²"
            else:
                area_value = None
                area_unit = "м²"
            
            # Цена = 1 означает "договорная"
            if price_value == 1:
                price_value = None
            
            # Локация
            locality = e.get("locality", {})
            locality_str = locality.get("value") if isinstance(locality, dict) else e.get("locality", "")
            
            # Название
            if not name:
                # Собираем из полей
                name_parts = []
                if e.get("type"):
                    name_parts.append(e.get("type"))
                if e.get("state"):
                    name_parts.append(e.get("state"))
                name = " ".join(name_parts) if name_parts else "Без названия"
            
            # Ссылка
            links = e.get("links", [])
            href = links[0].get("href") if links else ""
            link = f"https://www.sreality.cz{href}" if href else ""
            
            # Изображение - берём из _links
            image_url = ""
            estate_links = e.get("_links", {})
            images = estate_links.get("images", [])
            if images:
                image_url = images[0].get("href", "")
            
            results.append({
                "Название": name,
                "Цена": price_value,
                "Валюта": currency,
                "Площадь": area_value,
                "Ед.площади": area_unit,
                "Локация": locality_str,
                "Источник": "SReality",
                "Ссылка": link,
                "Фото": image_url,
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        
        return results
        
    except requests.RequestException as e:
        print(f"SReality error on page {page}: {e}")
        return []


def get_bezrealitky_api_key() -> str | None:
    """
    Получение API ключа Bezrealitky из переменной окружения
    export BEZREALITKY_API_KEY="твой_ключ"
    """
    return os.environ.get("BEZREALITKY_API_KEY")


def scrape_bezrealitky(page: int = 1, limit: int = 50) -> list:
    """
    Скрапинг Bezrealitky.cz через API
    Требует X-Api-Key
    """
    api_key = get_bezrealitky_api_key()
    
    if not api_key:
        print("⚠️ Bezrealitky: API key не найден (BEZREALITKY_API_KEY)")
        print("   Попробуем без ключа (ограниченный функционал)...")
        # Пробуем без ключа - может работать для базовых запросов
        headers_no_key = HEADERS.copy()
        headers_no_key["Accept"] = "text/html"
        # Fallback на парсинг HTML (упрощённо)
        return scrape_bezrealitky_html(page, limit)
    
    url = "https://api.bezrealitky.cz/v2/offers"
    params = {
        "page": page,
        "limit": limit,
        "offer_type": "sell",
        "property_type": "apartment"
    }
    
    headers = HEADERS.copy()
    headers["X-Api-Key"] = api_key
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        offers = data.get("offers", [])
        results = []
        
        for o in offers:
            # Цена
            price = o.get("price", {})
            price_value = price.get("amount") if isinstance(price, dict) else price
            
            # Площадь
            area = o.get("area", {})
            area_value = area.get("value") if isinstance(area, dict) else area
            
            # Адрес
            address = o.get("address", {})
            address_str = ""
            if isinstance(address, dict):
                address_str = ", ".join(filter(None, [
                    address.get("street"),
                    address.get("city"),
                    address.get("region")
                ]))
            else:
                address_str = str(address)
            
            results.append({
                "Название": o.get("title", "Без названия"),
                "Цена": price_value,
                "Валюта": "CZK",
                "Площадь": area_value,
                "Ед.площади": "м²",
                "Локация": address_str,
                "Источник": "Bezrealitky",
                "Ссылка": o.get("url", ""),
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        
        return results
        
    except requests.RequestException as e:
        print(f"Bezrealitky error: {e}")
        return []


def scrape_bezrealitky_html(page: int = 1, limit: int = 50) -> list:
    """
    Fallback: парсинг HTML страницы Bezrealitky без API ключа
    """
    url = f"https://www.bezrealitky.cz/sreality/najem?page={page}"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        
        # Простой парсинг через регулярки (упрощённо)
        import re
        
        # Ищем данные в HTML
        # Это упрощённая версия - для продажи нужно поменять URL
        results = []
        
        # П试e pattern для карточек
        pattern = r'<article[^>]*data-id="(\d+)"[^>]*>.*?<a href="([^"]+)"[^>]*>(?:.*?<span class="[^"]*price[^"]*">([^<]+)</span>)?'
        # Упрощённо - просто возвращаем заглушку
        
        print("   HTML parsing для Bezrealitky требует более сложного парсера")
        return []
        
    except Exception as e:
        print(f"Bezrealitky HTML error: {e}")
        return []


def scrape_all(pages: int = 3) -> pd.DataFrame:
    """
    Сбор данных со всех источников
    """
    all_properties = []
    
    print("🟦 Скрапинг SReality...")
    for page in range(1, pages + 1):
        print(f"   Страница {page}/{pages}...")
        results = scrape_sreality(page)
        all_properties.extend(results)
        print(f"   +{len(results)} объявлений")
        time.sleep(1)  # Rate limiting
    
    print(f"\n🟧 Скрапинг Bezrealitky...")
    results = scrape_bezrealitky(page=1)
    all_properties.extend(results)
    print(f"   +{len(results)} объявлений")
    
    # Создаём DataFrame
    df = pd.DataFrame(all_properties)
    
    # Форматирование
    if not df.empty:
        # Сортировка по цене
        df = df.sort_values("Цена", ascending=True, na_position="last")
        
        # Добавляем цену за м²
        df["Цена за м²"] = (df["Цена"] / df["Площадь"]).round(0)
    
    return df


def save_results(df: pd.DataFrame, fmt: str = "xlsx") -> Path:
    """
    Сохранение результатов
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"byty_{timestamp}"
    
    if fmt == "xlsx":
        filepath = OUTPUT_DIR / f"{filename}.xlsx"
        df.to_excel(filepath, index=False)
    elif fmt == "csv":
        filepath = OUTPUT_DIR / f"{filename}.csv"
        df.to_csv(filepath, index=False)
    elif fmt == "both":
        xlsx_path = OUTPUT_DIR / f"{filename}.xlsx"
        csv_path = OUTPUT_DIR / f"{filename}.csv"
        df.to_excel(xlsx_path, index=False)
        df.to_csv(csv_path, index=False)
        return xlsx_path
    
    # Также сохраняем latest.json для фронтенда
    latest_json = OUTPUT_DIR / "byty_latest.json"
    df.to_json(latest_json, orient="records", force_ascii=False, indent=2)
    
    return filepath


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Скрапер чешской недвижимости")
    parser.add_argument("-p", "--pages", type=int, default=3, help="Количество страниц SReality")
    parser.add_argument("-o", "--output", choices=["xlsx", "csv", "both"], default="xlsx", help="Формат вывода")
    parser.add_argument("--open", action="store_true", help="Открыть результат после завершения")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🏠 Real Estate Scraper - Чехия")
    print("=" * 50)
    
    df = scrape_all(pages=args.pages)
    
    if df.empty:
        print("\n❌ Нет данных!")
        return
    
    filepath = save_results(df, args.output)
    
    print(f"\n✅ Готово! Собрано {len(df)} объявлений")
    print(f"📁 Сохранено: {filepath}")
    print(f"\n📊 Первые 5 записей:")
    print(df.head().to_string())
    
    if args.open:
        os.startfile(filepath) if os.name == "nt" else os.system(f"open {filepath}")


if __name__ == "__main__":
    main()
