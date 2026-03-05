#!/usr/bin/env python3
"""
Bezrealitky Browser Scraper
Использует browser automation для скрапинга Bezrealitky
Требует attached Chrome tab с открытым Bezrealitky
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# For browser-based scraping
# This would require Playwright/Selenium

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def scrape_bezrealitky_browser():
    """
    Скрапинг через браузер - требует ручного запуска
    1. Открой bezrealitky.cz в Chrome
    2. Примени фильтры (продажа квартир, Прага)
    3. Запусти этот скрипт
    
    Или используй API ключ:
    export BEZREALITKY_API_KEY="твой_ключ"
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Bezrealitky Browser Scraper                                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Способ 1 - API ключ (рекомендуется):                        ║
║  1. Зайди на bezrealitky.cz                                 ║
║  2. Открой DevTools (F12) → Network                         ║
║  3. Найди запрос к api.bezrealitky.cz                       ║
║  4. Скопируй заголовок X-Api-Key                            ║
║  5. export BEZREALITKY_API_KEY="скопированный_ключ"         ║
║  6. python3 scraper.py                                       ║
║                                                              ║
║  Способ 2 - Альтернативные источники:                        ║
║  - SReality.cz (уже работает) ✅                            ║
║  - Reality.idnes.cz (требует настройки)                      ║
║  - Koupě.cz (требует настройки)                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    scrape_bezrealitky_browser()
