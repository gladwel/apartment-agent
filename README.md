# Real Estate Scraper 🏠

Сбор объявлений о недвижимости с SReality.cz и Bezrealitky.cz в Excel.

## Установка

```bash
cd real-estate-scraper
pip3 install -r requirements.txt
```

## Использование

```bash
# Скрапинг 3 страниц (дефолт)
python3 scraper.py

# Скрапинг 5 страниц
python3 scraper.py -p 5

# Сохранить в CSV
python3 scraper.py -o csv

# Сохранить в оба формата
python3 scraper.py -o both

# Открыть файл после завершения
python3 scraper.py --open
```

## Bezrealitky API

Для полного функционала Bezrealitky нужен API ключ:

```bash
export BEZREALITKY_API_KEY="твой_ключ"
python3 scraper.py
```

Ключ можно получить через dev tools браузера на bezrealitky.cz (запросы к API).

## Фильтры

Скрипт собирает:
- **SReality**: квартиры на продажу (category_main_cb=1, category_type_cb=1)
- **Bezrealitky**: (требуется API ключ)

Добавить фильтры в `scrape_sreality()`:
```python
params = {
    # ...
    "region": 14,        # Praha
    "price_min": 5000000,
    "price_max": 15000000,
}
```

## Output

Результаты в `output/byty_YYYYMMDD_HHMM.xlsx`:
| Колонка | Описание |
|---------|----------|
| Название | Тип квартиры и площадь |
| Цена | Цена в CZK |
| Площадь | м² |
| Локация | Район, город |
| Источник | SReality / Bezrealitky |
| Цена за м² | Цена за квадратный метр |
| Ссылка | Ссылка на объявление |

## Cron (автоматизация)

```bash
# Запускать каждый день в 9:00
crontab -e
0 9 * * * cd /root/.openclaw/workspace/real-estate-scraper && python3 scraper.py -p 5 -o xlsx
```
