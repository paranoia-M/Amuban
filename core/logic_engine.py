import numpy as np
from scipy.signal import find_peaks
from scipy import stats
from sklearn.cluster import KMeans

class IGBTMathEngine:
    """专利 CN 119270019 B 核心算法实现"""
    
    @staticmethod
    def calculate_gki(triplet_data):
        """逻辑4-5: 三元组聚类与突变差异系数 G_ki"""
        # 专利[0007]: 对(短路电流,饱和电压,门极电流)聚类
        km = KMeans(n_clusters=2, n_init='auto').fit(triplet_data)
        centers = km.cluster_centers_
        # 专利[0015]: Gki = Aki * Fki
        a_ki = np.linalg.norm(centers[0] - centers[1])
        f_ki = np.mean(np.std(triplet_data, axis=0))
        return float(a_ki * f_ki)

    @staticmethod
    def calculate_pki(current_series, gki):
        """逻辑6-7: 波峰提取与振荡异常系数 P_ki"""
        peaks, _ = find_peaks(current_series, distance=10)
        valleys, _ = find_peaks(-current_series, distance=10)
        # 专利[0024]: Pki = Gki * (Hki + Mki)
        # Mki: 波峰波谷差异均值
        m_ki = np.mean([np.abs(current_series[p] - current_series[valleys[np.abs(valleys-p).argmin()]]) for p in peaks]) if len(peaks)>0 else 0
        # Hki: 峰度陡峭指数
        h_ki = stats.kurtosis(current_series)
        return float(gki * (h_ki + m_ki))

    @staticmethod
    def calculate_wi(pki_list):
        """逻辑8-10: 趋势显著性 Ti 与 质量评估 Wi"""
        # 专利[0105]: Mann-Kendall 趋势检验
        n = len(pki_list)
        if n < 2: return 0.5
        s = 0
        for i in range(n-1):
            for j in range(i+1, n):
                s += np.sign(pki_list[j] - pki_list[i])
        t_i = abs(s) / (n*(n-1)/2) # 简化版趋势显著性
        # Ui: 振荡一致性 (变异系数倒数)
        u_i = 1.0 / (np.std(pki_list) + 0.1)
        return float(t_i * u_i)