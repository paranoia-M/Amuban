import numpy as np
import sqlite3
from scipy import stats
from scipy.signal import find_peaks
from sklearn.cluster import KMeans

class PatentEngine:
    @staticmethod
    def calculate_gki(data_3d):
        """专利[0015]: Gki = Aki * Fki"""
        if len(data_3d) < 10: return 0.0
        km = KMeans(n_clusters=2, n_init='auto').fit(data_3d)
        centers = km.cluster_centers_
        a_ki = np.linalg.norm(centers[0] - centers[1])
        f_ki = np.mean(np.std(data_3d, axis=0))
        return float(a_ki * f_ki)

class DataCenter:
    def __init__(self):
        self.conn = sqlite3.connect("igbt_sys.db", check_same_thread=False)
        self.conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, msg TEXT, ts DATETIME)")

    def log_event(self, msg):
        self.conn.execute("INSERT INTO logs (msg, ts) VALUES (?, datetime('now'))", (msg,))
        self.conn.commit()