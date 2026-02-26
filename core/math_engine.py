import numpy as np

class IGBTMathEngine:
    @staticmethod
    def run_cluster_analysis(data_3d):
        """逻辑4-5: 三元组聚类 G_ki 解算"""
        from sklearn.cluster import KMeans # 延迟导入
        model = KMeans(n_clusters=2, n_init='auto').fit(data_3d)
        centers = model.cluster_centers_
        # Aki: 质心欧氏距离; Fki: 数据离散度
        a_ki = np.linalg.norm(centers[0] - centers[1])
        f_ki = np.mean(np.std(data_3d, axis=0))
        return float(a_ki * f_ki), model.labels_

    @staticmethod
    def run_oscillation_calc(waveform, gki):
        """逻辑7: 振荡异常 P_ki 核心公式"""
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(waveform, height=0.5)
        # 专利[0024]: 峰度 + 波峰均值差异
        h_ki = float(np.mean(waveform[peaks])) if len(peaks) > 0 else 0
        m_ki = float(np.std(waveform))
        return gki * (h_ki + m_ki)

    @staticmethod
    def run_trend_test(pki_series):
        """逻辑8: Mann-Kendall 趋势显著性检测"""
        n = len(pki_series)
        if n < 2: return 0.0
        s = 0
        for i in range(n-1):
            for j in range(i+1, n):
                s += np.sign(pki_series[j] - pki_series[i])
        return s / (n * (n-1) / 2)