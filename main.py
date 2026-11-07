import time
import requests
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import threading

app = FastAPI(title="Wingo Cloud Predictor & Database")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
DB_NAME = "wingo_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            issue TEXT PRIMARY KEY,
            number INTEGER,
            size TEXT,
            color TEXT,
            time_recorded TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def fetch_and_store_loop():
    while True:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(f"{API_URL}?ts={int(time.time() * 1000)}", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("list", []) or data.get("list", [])
                if items:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    for row in items:
                        issue = str(row.get('issue', row.get('period', '')))
                        number = int(row.get('number', 0))
                        size = str(row.get('size', ''))
                        color = str(row.get('color', ''))
                        time_str = str(row.get('time', time.strftime('%Y-%m-%d %H:%M:%S')))
                        if issue:
                            try:
                                cursor.execute('INSERT INTO game_history (issue, number, size, color, time_recorded) VALUES (?, ?, ?, ?, ?)', 
                                               (issue, number, size, color, time_str))
                            except sqlite3.IntegrityError:
                                pass
                    conn.commit()
                    conn.close()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(20)

threading.Thread(target=fetch_and_store_loop, daemon=True).start()

@app.get("/api/history")
def get_history(limit: int = 50):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM game_history ORDER BY CAST(issue AS INTEGER) DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return {"total": len(rows), "data": [dict(r) for r in rows]}
