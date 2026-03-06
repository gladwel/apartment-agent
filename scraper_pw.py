#!/usr/bin/env python3
"""Scraper using Playwright - for Prague apartments"""
import json
import re
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

async def scrape_bezrealitky(max_pages=3):
    """Scrape Bezrealitky.cz - Prague only"""
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for page_num in range(1, max_pages + 1):
            print(f"🟧 Bezrealitky страница {page_num}/{max_pages}")
            
            # URL с фильтром Праги
            url = f"https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt/praha?page={page_num}"
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector("article", timeout=15000)
                await page.wait_for_timeout(2000)
                
                articles = await page.query_selector_all("article")
                print(f"   Найдено: {len(articles)} объявлений")
                
                for art in articles:
                    try:
                        text = await art.inner_text()
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        
                        # Цена
                        price = 0
                        for l in lines:
                            nums = re.findall(r'([\d\s]+)', l)
                            for n in nums:
                                n = n.replace('\xa0', '').strip()
                                if n.isdigit() and len(n) >= 4:
                                    if '€' in l:
                                        price = int(n) * 25
                                    elif 'Kč' in l:
                                        price = int(n)
                                    if price > 0:
                                        break
                            if price > 0:
                                break
                        
                        # Площадь
                        area = 0
                        for l in lines:
                            m = re.search(r'(\d+)\s*m', l)
                            if m:
                                area = int(m.group(1))
                                break
                        
                        # Адрес
                        address = ''
                        for l in lines:
                            if 'Praha' in l:
                                address = l
                                break
                        
                        # Ссылка
                        link_el = await art.query_selector("a")
                        link = await link_el.get_attribute("href") if link_el else ""
                        
                        # Фото
                        img_el = await art.query_selector("img")
                        photo = await img_el.get_attribute("src") if img_el else ""
                        
                        if price > 0 and price <= 40000 and area > 0:
                            results.append({
                                "Название": address or "Unknown",
                                "Цена": price,
                                "Площадь": area,
                                "Локация": address,
                                "Источник": "Bezrealitky",
                                "Ссылка": link,
                                "Фото": photo,
                                "Дата": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                    except Exception as e:
                        pass
            except Exception as e:
                print(f"   Ошибка: {e}")
            finally:
                await page.close()
        
        await browser.close()
    
    return results

async def main():
    print("=" * 50)
    print("🏠 Apartment Scraper (Playwright)")
    print("=" * 50)
    
    # Собираем
    results = await scrape_bezrealitky(max_pages=3)
    
    print(f"\n✅ Итого: {len(results)} квартир (Прага, до 40k)")
    
    # Сохранить
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    # Добавить ID
    for i, apt in enumerate(results):
        apt['_id'] = f'apt-{i}'
    
    # public
    with open(OUTPUT_DIR.parent / "public" / "combined_latest.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # output
    with open(OUTPUT_DIR / f"combined_{ts}.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"📁 Сохранено в public/combined_latest.json")

if __name__ == "__main__":
    asyncio.run(main())
