import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class CurveFittingPage(QWidget):
    """
    第三个菜单：曲线拟合引擎
    逻辑核心：基于专利 [0086] 的多项式拟合与导数分析
    """
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # --- 左侧：交互控制面板 ---
        self.ctrl_panel = QWidget()
        self.ctrl_panel.setFixedWidth(400)
        self.ctrl_layout = QVBoxLayout(self.ctrl_panel)

        title = QLabel("曲线拟合与导数分析引擎")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF;")
        self.ctrl_layout.addWidget(title)

        # 1. 拟合参数设置
        fit_gb = QGroupBox("拟合算法配置")
        fit_l = QFormLayout(fit_gb)
        self.spin_order = QSpinBox()
        self.spin_order.setRange(2, 12); self.spin_order.setValue(6)
        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["Least-Squares (最小二乘)", "RANSAC (鲁棒拟合)", "Spline (样条插值)"])
        fit_l.addRow("拟合多项式阶数:", self.spin_order)
        fit_l.addRow("核心算法策略:", self.cmb_method)
        self.ctrl_layout.addWidget(fit_gb)

        # 2. 特征提取逻辑 (专利 [0087]-[0088])
        feature_gb = QGroupBox("导数特征提取 (Derivative Analysis)")
        feat_l = QVBoxLayout(feature_gb)
        self.chk_first_der = QCheckBox("计算一阶导数 (探测变化率)")
        self.chk_second_der = QCheckBox("计算二阶导数 (探测拐点)")
        self.chk_auto_peak = QCheckBox("自动锁定拟合曲线极值点")
        self.chk_first_der.setChecked(True)
        feat_l.addWidget(self.chk_first_der); feat_l.addWidget(self.chk_second_der); feat_l.addWidget(self.chk_auto_peak)
        self.ctrl_layout.addWidget(feature_gb)

        # 3. 拟合结果看板
        self.res_gb = QGroupBox("拟合质量评价 (Goodness of Fit)")
        res_l = QFormLayout(self.res_gb)
        self.lbl_rmse = QLabel("0.0000"); self.lbl_r2 = QLabel("0.0000")
        res_l.addRow("RMSE (均方根误差):", self.lbl_rmse)
        res_l.addRow("R² (确定系数):", self.lbl_r2)
        self.ctrl_layout.addWidget(self.res_gb)

        self.btn_run_fit = QPushButton("⚡ 执行专利级多项式拟合分析")
        self.btn_run_fit.setFixedHeight(50)
        self.btn_run_fit.setStyleSheet("background-color: #0078D4; font-weight: bold;")
        self.btn_run_fit.clicked.connect(self._execute_fit)
        self.ctrl_layout.addWidget(self.btn_run_fit)
        self.ctrl_layout.addStretch()

        # --- 右侧：多维图表分析区 ---
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        
        # 使用 Matplotlib 进行三层画布展示
        self.figure, (self.ax1, self.ax2) = plt.subplots(2, 1, facecolor='#0B0E14')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.chart_layout.addWidget(self.canvas)

        self.main_layout.addWidget(self.ctrl_panel)
        self.main_layout.addWidget(self.chart_container, 1)

    def _execute_fit(self):
        """
        核心拟合算法逻辑实现
        """
        # 1. 模拟生成原始含噪声的短路电流数据
        x = np.linspace(0, 10, 100)
        y_pure = 20 * np.exp(-0.5 * x) * np.sin(x) + 10
        y_noise = y_pure + np.random.normal(0, 0.8, 100)

        # 2. 执行多项式拟合 (专利 [0086])
        order = self.spin_order.value()
        coeffs = np.polyfit(x, y_noise, order)
        poly_func = np.poly1d(coeffs)
        y_fit = poly_func(x)

        # 3. 计算导数 (专利 [0087])
        first_der = np.polyder(poly_func, 1)
        second_der = np.polyder(poly_func, 2)

        # 4. 绘图更新
        self.ax1.clear(); self.ax2.clear()
        self.ax1.set_facecolor('#10141B'); self.ax2.set_facecolor('#10141B')
        
        self.ax1.scatter(x, y_noise, color='#555555', s=10, label='Original Data')
        self.ax1.plot(x, y_fit, color='#00A3FF', linewidth=2, label=f'Fit (Order {order})')
        self.ax1.set_title("Short-Circuit Current Polynomial Fitting", color='white')
        self.ax1.legend()

        self.ax2.plot(x, first_der(x), color='#00FF94', label='1st Derivative')
        if self.chk_second_der.isChecked():
            self.ax2.plot(x, second_der(x), color='#FF8C00', label='2nd Derivative')
        self.ax2.set_title("Derivative Characteristic Analysis", color='white')
        self.ax2.legend()

        # 刷新画布
        self.figure.tight_layout()
        self.canvas.draw()

        # 5. 更新质量指标指标
        self.lbl_rmse.setText(f"{np.sqrt(np.mean((y_noise-y_fit)**2)):.4f}")
        self.lbl_r2.setText(f"{1 - (np.sum((y_noise-y_fit)**2) / np.sum((y_noise-np.mean(y_noise))**2)):.4f}")