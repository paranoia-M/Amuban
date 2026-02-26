import sqlite3

class TestDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("igbt_data.sqlite", check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS igbt_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temp REAL, gki REAL, pki REAL, wi REAL, conclusion TEXT
        )""")
        self.conn.commit()

    def insert_result(self, temp, gki, pki, wi, conclusion):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO igbt_results (temp, gki, pki, wi, conclusion) VALUES (?,?,?,?,?)",
                    (temp, gki, pki, wi, conclusion))
        self.conn.commit()

    def fetch_records(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM igbt_results ORDER BY id DESC")
        return cur.fetchall()