#создание бд
import sqlite3
import threading

class Database:
    def __init__(self, db_path="forelka.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._create_tables()

    def _create_tables(self):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()

    def set(self, key, value):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))
            self.conn.commit()

    def get(self, key, default=None):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def close(self):
        self.conn.close()
