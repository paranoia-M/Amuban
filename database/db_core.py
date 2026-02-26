import sqlite3

class DataManager:
    def __init__(self, db_name="igbt_test.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS test_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            batch_id TEXT,
                            temp REAL,
                            g_ki REAL,
                            p_ki REAL,
                            w_i REAL,
                            status TEXT)''')
        self.conn.commit()

    def add_record(self, batch, temp, g, p, w):
        cursor = self.conn.cursor()
        status = "正常" if w > 0.75 else "故障待查" # 专利[0121]阈值逻辑
        cursor.execute("INSERT INTO test_records (batch_id, temp, g_ki, p_ki, w_i, status) VALUES (?,?,?,?,?,?)",
                       (batch, temp, g, p, w, status))
        self.conn.commit()

    def fetch_all(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM test_records ORDER BY id DESC")
        return cursor.fetchall()