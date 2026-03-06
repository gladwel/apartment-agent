#!/usr/bin/env python3
"""SQLite DB для квартир"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "apartments.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS apartments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        price REAL,
        area INTEGER,
        location TEXT,
        source TEXT,
        link TEXT,
        photo TEXT,
        date TEXT,
        price_per_m2 REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def import_from_json(json_path=None):
    if json_path is None:
        json_path = Path(__file__).parent / "public" / "combined_latest.json"
    
    if not Path(json_path).exists():
        print(f"Файл не найден: {json_path}")
        return 0
    
    with open(json_path) as f:
        data = json.load(f)
    
    conn = get_db()
    c = conn.cursor()
    
    # Очистим старые данные
    c.execute("DELETE FROM apartments")
    
    for apt in data:
        c.execute('''INSERT INTO apartments 
            (title, price, area, location, source, link, photo, date, price_per_m2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (apt.get('Название'), apt.get('Цена'), apt.get('Площадь'), apt.get('Локация'),
             apt.get('Источник'), apt.get('Ссылка'), apt.get('Фото'), apt.get('Дата'), apt.get('Цена за м²')))
    
    conn.commit()
    count = len(data)
    conn.close()
    return count

def get_all(filters=None):
    conn = get_db()
    c = conn.cursor()
    
    query = "SELECT * FROM apartments WHERE 1=1"
    params = []
    
    if filters:
        if filters.get('min_price'):
            query += " AND price >= ?"
            params.append(filters['min_price'])
        if filters.get('max_price'):
            query += " AND price <= ?"
            params.append(filters['max_price'])
        if filters.get('min_area'):
            query += " AND area >= ?"
            params.append(filters['min_area'])
        if filters.get('max_area'):
            query += " AND area <= ?"
            params.append(filters['max_area'])
        if filters.get('location'):
            query += " AND location LIKE ?"
            params.append(f"%{filters['location']}%")
    
    query += " ORDER BY price ASC"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_by_id(apt_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM apartments WHERE id = ?", (apt_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total, MIN(price) as min_price, MAX(price) as max_price, AVG(price) as avg_price FROM apartments")
    row = c.fetchone()
    conn.close()
    return dict(row)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "import":
            count = import_from_json()
            print(f"Импортировано {count} квартир")
        elif sys.argv[1] == "stats":
            print(stats())
        else:
            print(get_all())
    else:
        print("Usage: python3 db.py import|stats")
