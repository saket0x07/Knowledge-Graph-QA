import sqlite3
import os
from datetime import datetime
from threading import Lock

DB_PATH = "app.db"
db_lock = Lock()

def init_sqlite_db():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_size_mb REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

def log_ingestion_start(filename: str, file_size_mb: float):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # If it exists, update it to processing, else insert new
        cursor.execute("SELECT id FROM ingestion_history WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE ingestion_history 
                SET status = 'Processing', timestamp = CURRENT_TIMESTAMP, file_size_mb = ?
                WHERE filename = ?
            """, (file_size_mb, filename))
        else:
            cursor.execute("""
                INSERT INTO ingestion_history (filename, file_size_mb, status, timestamp)
                VALUES (?, ?, 'Processing', CURRENT_TIMESTAMP)
            """, (filename, file_size_mb))
        conn.commit()
        conn.close()

def update_ingestion_status(filename: str, status: str):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ingestion_history 
            SET status = ?, timestamp = CURRENT_TIMESTAMP
            WHERE filename = ?
        """, (status, filename))
        conn.commit()
        conn.close()

def get_ingestion_history():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, file_size_mb, status, timestamp 
            FROM ingestion_history 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
