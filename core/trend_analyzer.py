import numpy as np
from scipy import stats

class IGBTStatistics:
    """
    专利算法实现：趋势显著性 T_i 与 振荡一致性 U_i
    """
    @staticmethod
    def mann_kendall_test(data):
        """实现专利中提到的Mann-Kendall趋势检验"""
        n = len(data)
        s = 0
        for i in range(n - 1):
            for j in range(i + 1, n):
                s += np.sign(data[j] - data[i])
        
        # 计算趋势特征绝对值 (专利逻辑)
        unique_x = np.unique(data)
        g = len(unique_x)
        if n == g:
            var_s = (n * (n - 1) * (2 * n + 5)) / 18
        else:
            # 处理重复值的情况
            tp = np.array([len(np.where(data == x)[0]) for x in unique_x])
            var_s = (n * (n - 1) * (2 * n + 5) - np.sum(tp * (tp - 1) * (2 * tp + 5))) / 18
        
        if s > 0: z = (s - 1) / np.sqrt(var_s)
        elif s < 0: z = (s + 1) / np.sqrt(var_s)
        else: z = 0
        return abs(z)

    @staticmethod
    def calculate_quality_index(trend_sig, consistency_mean):
        """计算 Wi = Ti * Ui"""
        return trend_sig * consistency_mean