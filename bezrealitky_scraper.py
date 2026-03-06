#!/usr/bin/env python3
"""
Bezrealitky Scraper via Playwright
Скрапинг Bezrealitky.cz через browser automation
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def scrape_bezrealitky(page_num: int = 1, max_results: int = 50) -> list:
    """
    Скрапинг Bezrealitky.cz через Playwright
    """
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        url = f"https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt?page={page_num}"
        print(f"   Загрузка: {url}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(3)
            
            # Скроллим для загрузки
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Ищем все карточки объявлений
            # Используем селектор по ссылкам с nabidka-
            links = await page.query_selector_all('a[href*="nabidka-"]')
            print(f"   Найдено ссылок: {len(links)}")
            
            seen_urls = set()
            
            for link_elem in links[:max_results * 2]:  # берем больше чтобы отфильтровать
                try:
                    href = await link_elem.get_attribute('href')
                    if not href or 'nabidka-' not in href:
                        continue
                    
                    url_full = href if href.startswith('http') else f"https://www.bezrealitky.cz{href}"
                    
                    # Пропускаем дубликаты
                    if url_full in seen_urls:
                        continue
                    seen_urls.add(url_full)
                    
                    if len(results) >= max_results:
                        break
                    
                    # Получаем текст из родительского контейнера
                    parent = await link_elem.evaluate_handle('el => el.closest("article") || el.closest("div")')
                    if parent:
                        card_text = await parent.inner_text()
                    else:
                        card_text = ""
                    
                    lines = [l.strip() for l in card_text.split('\n') if l.strip()]
                    
                    # Цена
                    price_match = re.search(r'(\d[\d\s]*)\s*Kč', card_text)
                    price = None
                    if price_match:
                        price_clean = re.sub(r'[^\d]', '', price_match.group(1))
                        price = int(price_clean) if price_clean else None
                    
                    if not price:
                        continue
                    
                    # Площадь
                    area_match = re.search(r'(\d+)\s*m', card_text)
                    area = int(area_match.group(1)) if area_match else None
                    
                    # Локация - ищем строку с городом
                    location = ""
                    for line in reversed(lines):
                        lower = line.lower()
                        if any(city in lower for city in ['praha', 'brno', 'ostrava', 'české', 'plzeň']):
                            location = line
                            break
                    
                    # Название - используем локацию как название
                    title = location if location else url_full.split('/')[-1][:50]
                    
                    # Фото
                    image_url = ""
                    img = await link_elem.query_selector('img') if link_elem else None
                    if img:
                        src = await img.get_attribute('src') or ""
                        if 'url=' in src:
                            from urllib.parse import unquote
                            url_match = re.search(r'url=([^&]+)', src)
                            if url_match:
                                image_url = unquote(url_match.group(1))
                    
                    results.append({
                        "Название": title,
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
                    
                except Exception as e:
                    continue
            
            print(f"   Собрано: {len(results)} объявлений")
                    
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        await browser.close()
    
    return results


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Bezrealitky Scraper")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Количество страниц")
    parser.add_argument("-m", "--max", type=int, default=50, help="Макс. результатов")
    args = parser.parse_args()
    
    print("=" * 50)
    print("🟧 Bezrealitky Scraper (Playwright)")
    print("=" * 50)
    
    all_results = []
    for page in range(1, args.pages + 1):
        print(f"\n📄 Страница {page}/{args.pages}")
        results = await scrape_bezrealitky(page, args.max)
        all_results.extend(results)
        await asyncio.sleep(1)
    
    print(f"\n✅ Всего: {len(all_results)} объявлений")
    
    if all_results:
        import pandas as pd
        df = pd.DataFrame(all_results)
        df["Цена за м²"] = (df["Цена"] / df["Площадь"]).round(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filepath = OUTPUT_DIR / f"bezrealitky_{timestamp}.xlsx"
        df.to_excel(filepath, index=False)
        
        json_path = OUTPUT_DIR / "bezrealitky_latest.json"
        df.to_json(json_path, orient="records", force_ascii=False, indent=2)
        
        print(f"📁 Сохранено: {filepath}")
        print(df.head().to_string())
    
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
