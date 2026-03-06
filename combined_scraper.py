#!/usr/bin/env python3
"""
Combined Real Estate Scraper
Запускает SReality + Bezrealitky сразу
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests
import time
import re
import os

# Импорты для Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Фильтры по умолчанию
FILTERS = {
    "area_min": 30,
    "area_max": None,
    "price_min": None,
    "price_max": 25000,  # для аренды
    "category_type_cb": 2,  # аренда
    "category_main_cb": 1,
    "region": None,
    "sort": "0",
}


def scrape_sreality(page: int = 1, limit: int = 50, filters: dict = None) -> list:
    """Скрапинг SReality.cz"""
    if filters is None:
        filters = FILTERS
    
    url = "https://www.sreality.cz/api/v2/estates"
    params = {
        "page": page,
        "limit": limit,
        "category_main_cb": filters.get("category_main_cb", 1),
        "category_type_cb": filters.get("category_type_cb", 2),
        "sort": filters.get("sort", "0"),
    }
    
    if filters.get("area_min"):
        params["area_min"] = filters["area_min"]
    if filters.get("area_max"):
        params["area_max"] = filters["area_max"]
    if filters.get("price_min"):
        params["price_min"] = filters["price_min"]
    if filters.get("price_max"):
        params["price_max"] = filters["price_max"]
    if filters.get("region"):
        params["region"] = filters["region"]
    
    # Исключаем spolubydlící
    params["category_sub_cb"] = "1,2,4,5,6,7,8,9,10,11,12,13,14,15,16"
    
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        estates = data.get("_embedded", {}).get("estates", [])
        results = []
        
        for e in estates:
            price = e.get("price", {})
            if isinstance(price, dict):
                price_value = price.get("value_raw") or price.get("value")
                currency = price.get("currency", "CZK")
            else:
                price_value = price
                currency = "CZK"
            
            name = e.get("name", "")
            area_match = re.search(r'(\d+)\s*m[²²]', name, re.IGNORECASE)
            area_value = int(area_match.group(1)) if area_match else None
            
            if price_value == 1:
                price_value = None
            
            locality = e.get("locality", {})
            locality_str = locality.get("value") if isinstance(locality, dict) else e.get("locality", "")
            
            links = e.get("links", [])
            href = links[0].get("href") if links else ""
            link = f"https://www.sreality.cz{href}" if href else ""
            
            estate_links = e.get("_links", {})
            images = estate_links.get("images", [])
            image_url = images[0].get("href", "") if images else ""
            
            results.append({
                "Название": name[:100] if name else "Без названия",
                "Цена": price_value,
                "Валюта": currency,
                "Площадь": area_value,
                "Ед.площади": "м²",
                "Локация": locality_str[:150] if locality_str else "",
                "Источник": "SReality",
                "Ссылка": link,
                "Фото": image_url,
                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        
        return results
        
    except Exception as e:
        print(f"   SReality error: {e}")
        return []


async def scrape_bezrealitky(page_num: int = 1, max_results: int = 30) -> list:
    """Скрапинг Bezrealitky.cz через Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("   ⚠️ Playwright не установлен")
        return []
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        url = f"https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt?page={page_num}"
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(3)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            links = await page.query_selector_all('a[href*="nabidka-"]')
            print(f"   Bezrealitky: найдено {len(links)} ссылок")
            
            seen_urls = set()
            
            for link_elem in links[:max_results * 2]:
                try:
                    href = await link_elem.get_attribute('href')
                    if not href or 'nabidka-' not in href:
                        continue
                    
                    url_full = href if href.startswith('http') else f"https://www.bezrealitky.cz{href}"
                    
                    if url_full in seen_urls:
                        continue
                    seen_urls.add(url_full)
                    
                    if len(results) >= max_results:
                        break
                    
                    try:
                        card = await link_elem.evaluate_handle('el => el.closest("article")')
                        card_text = await card.inner_text() if card else ""
                    except:
                        card_text = ""
                    
                    price_match = re.search(r'(\d[\d\s]*)\s*Kč', card_text)
                    price = None
                    if price_match:
                        price_clean = re.sub(r'[^\d]', '', price_match.group(1))
                        price = int(price_clean) if price_clean else None
                    
                    if not price:
                        continue
                    
                    area_match = re.search(r'(\d+)\s*m', card_text)
                    area = int(area_match.group(1)) if area_match else None
                    
                    location = ""
                    for line in reversed(card_text.split('\n')):
                        lower = line.lower()
                        if any(city in lower for city in ['praha', 'brno', 'ostrava', 'české', 'plzeň']):
                            location = line.strip()
                            break
                    
                    title = location if location else url_full.split('/')[-1][:50]
                    
                    image_url = ""
                    img = await link_elem.query_selector('img')
                    if img:
                        src = await img.get_attribute('src') or ""
                        if 'url=' in src:
                            from urllib.parse import unquote
                            url_match = re.search(r'url=([^&]+)', src)
                            if url_match:
                                image_url = unquote(url_match.group(1))
                    
                    results.append({
                        "Название": title[:100],
                        "Цена": price,
                        "Валюта": "CZK",
                        "Площадь": area,
                        "Ед.площади": "м²",
                        "Локация": location[:150],
                        "Источник": "Bezrealitky",
                        "Ссылка": url_full,
                        "Фото": image_url,
                        "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    
                except:
                    continue
            
            print(f"   Bezrealitky: собрано {len(results)} объявлений")
                    
        except Exception as e:
            print(f"   Bezrealitky error: {e}")
        
        await browser.close()
    
    return results


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Combined Real Estate Scraper")
    parser.add_argument("-p", "--pages", type=int, default=2, help="Страниц SReality")
    parser.add_argument("-b", "--bez-pages", type=int, default=2, help="Страниц Bezrealitky")
    parser.add_argument("-m", "--max", type=int, default=30, help="Макс. Bezrealitky")
    parser.add_argument("--area-min", type=int, default=30, help="Мин. площадь")
    parser.add_argument("--area-max", type=int, help="Макс. площадь")
    parser.add_argument("--price-max", type=int, default=25000, help="Макс. цена")
    parser.add_argument("--rent", action="store_true", default=True, help="Аренда")
    parser.add_argument("--sell", action="store_true", help="Продажа")
    args = parser.parse_args()
    
    # Настройка фильтров
    filters = FILTERS.copy()
    filters["area_min"] = args.area_min
    filters["area_max"] = args.area_max
    filters["price_max"] = args.price_max
    
    if args.sell:
        filters["category_type_cb"] = 1  # продажа
        filters["price_max"] = args.price_max if args.price_max != 25000 else 25000000
    else:
        filters["category_type_cb"] = 2  # аренда
    
    print("=" * 60)
    print("🏠 Combined Real Estate Scraper")
    print("=" * 60)
    print(f"📌 Фильтры: площадь {filters['area_min']}+ м², цена до {filters['price_max']} CZK")
    print(f"   Тип: {'Продажа' if args.sell else 'Аренда'}")
    print()
    
    all_results = []
    
    # SReality
    print("🟦 SReality...")
    for page in range(1, args.pages + 1):
        results = scrape_sreality(page, filters=filters)
        all_results.extend(results)
        print(f"   Страница {page}: +{len(results)}")
        time.sleep(1)
    
    # Bezrealitky
    if PLAYWRIGHT_AVAILABLE:
        print("\n🟧 Bezrealitky...")
        for page in range(1, args.bez_pages + 1):
            results = await scrape_bezrealitky(page, args.max)
            all_results.extend(results)
            await asyncio.sleep(1)
    else:
        print("\n🟧 Bezrealitky: Playwright не установлен")
    
    print(f"\n✅ Итого: {len(all_results)} объявлений")
    
    if all_results:
        df = pd.DataFrame(all_results)
        df = df.drop_duplicates(subset=['Ссылка'])
        
        # Цена за м²
        df["Цена за м²"] = (df["Цена"] / df["Площадь"]).round(0)
        df = df.sort_values("Цена", ascending=True, na_position="last")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Excel
        xlsx_path = OUTPUT_DIR / f"combined_{timestamp}.xlsx"
        df.to_excel(xlsx_path, index=False)
        
        # JSON для фронтенда
        json_path = OUTPUT_DIR / "combined_latest.json"
        df.to_json(json_path, orient="records", force_ascii=False, indent=2)
        
        print(f"\n📁 Сохранено:")
        print(f"   Excel: {xlsx_path}")
        print(f"   JSON: {json_path}")
        print(f"\n📊 Первые 10:")
        print(df[["Название", "Цена", "Площадь", "Локация", "Источник"]].head(10).to_string())
    
    return df


if __name__ == "__main__":
    asyncio.run(main())
