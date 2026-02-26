import numpy as np
from scipy.signal import find_peaks
from scipy import stats
from sklearn.cluster import KMeans

class IGBTCoreEngine:
    """
    专利核心逻辑实现类：严禁随意修改参数映射
    """
    
    @staticmethod
    def mutation_analysis(triplet_data):
        """
        逻辑4 & 5：三元组聚类分析与突变偏移 (G_ki)
        triplet_data: (短路电流, 饱和电压, 门极电流) 的 N*3 矩阵
        """
        # 专利[0007]：对三元组聚类得到两个簇
        kmeans = KMeans(n_clusters=2, n_init=10).fit(triplet_data)
        centers = kmeans.cluster_centers_
        
        # A_ki: 簇间差异均值
        a_ki = np.linalg.norm(centers[0] - centers[1])
        # F_ki: 综合差异系数 (此处为专利逻辑简化实现，实际需对比多器件)
        f_ki = np.std(triplet_data, axis=0).mean()
        
        g_ki = a_ki * f_ki
        return g_ki, kmeans.labels_

    @staticmethod
    def oscillation_quantification(current_series, g_ki):
        """
        逻辑7：振荡异常量化 (P_ki)
        专利[0024]：Pk,i = Gk,i × (Hk,i + Mk,i)
        """
        # 提取波峰波谷
        peaks, _ = find_peaks(current_series, distance=5)
        valleys, _ = find_peaks(-current_series, distance=5)
        
        # M_ki: 波峰波谷差异均值
        m_ki = 0
        if len(peaks) > 0 and len(valleys) > 0:
            m_ki = np.mean([np.abs(current_series[p] - current_series[valleys[np.abs(valleys-p).argmin()]]) for p in peaks])
        
        # H_ki: 峰度陡峭指数 (专利逻辑：峰域内分布情况)
        h_ki = stats.kurtosis(current_series)
        
        p_ki = g_ki * (h_ki + m_ki)
        return p_ki

    @staticmethod
    def quality_evaluation(p_ki_sequence):
        """
        逻辑10：质量分级评定 (Wi)
        专利[0030]：Wi = Ti × Ui
        """
        # Ti: 趋势显著性 (Mann-Kendall 检验)
        # 此处使用统计趋势代表显著性
        slope, _, _, p_value, _ = stats.linregress(range(len(p_ki_sequence)), p_ki_sequence)
        t_i = abs(slope) / (p_value + 1e-6)
        
        # Ui: 振荡一致性 (此处逻辑为序列稳定度)
        u_i = 1.0 / (np.std(p_ki_sequence) + 1e-6)
        
        w_i = t_i * u_i
        return w_i