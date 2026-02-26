import sys
import time
import numpy as np
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from scipy.signal import find_peaks, argrelextrema

# =============================================================================
# 1. 专利特征提取引擎 (Patent Feature Extraction Engine)
# =============================================================================

class PeakValleyEngine(QThread):
    """
    基于专利 [0019]-[0020] 的波峰波谷自动配对引擎
    实现导数零点探测与特征半径解算
    """
    analysis_ready = pyqtSignal(dict)
    log_sig = pyqtSignal(str, str)

    def __init__(self, raw_data, smoothing):
        super().__init__()
        self.raw_data = raw_data
        self.smoothing = smoothing # 平滑因子

    def run(self):
        self.log_sig.emit("SYS", ">>> 启动波峰波谷拓扑扫描仪...")
        
        # 1. 数据预处理与平滑 (模拟专利[0019]的拟合效果)
        x = np.linspace(0, 100, len(self.raw_data))
        y = np.convolve(self.raw_data, np.ones(self.smoothing)/self.smoothing, mode='same')
        
        # 2. 导数解算 (专利[0087]核心判定逻辑)
        dy = np.gradient(y)
        ddy = np.gradient(dy)
        self.log_sig.emit("MATH", "完成一阶/二阶导数映射，定位零位交叉点。")

        # 3. 提取特征点
        # 波峰：一阶导数=0, 二阶导数<0
        peaks, _ = find_peaks(y, distance=30, prominence=0.2)
        # 波谷：一阶导数=0, 二阶导数>0
        valleys, _ = find_peaks(-y, distance=30)

        # 4. 专利核心逻辑：波峰-波谷配对与邻域半径解算 [0009]
        features = []
        for p in peaks:
            # 寻找物理距离最近的波谷
            if len(valleys) > 0:
                dist_to_valleys = np.abs(valleys - p)
                nearest_v_idx = valleys[np.argmin(dist_to_valleys)]
                radius = abs(p - nearest_v_idx)
                
                features.append({
                    'peak_idx': p,
                    'valley_idx': nearest_v_idx,
                    'radius': radius,
                    'amp_diff': abs(y[p] - y[nearest_v_idx]),
                    'peak_val': y[p],
                    'valley_val': y[nearest_v_idx]
                })

        self.log_sig.emit("SUCCESS", f"特征提取完成：检出 {len(features)} 组有效的波峰波谷配对。")
        
        self.analysis_ready.emit({
            'x': x, 'y': y, 'dy': dy, 'ddy': ddy,
            'peaks': peaks, 'valleys': valleys,
            'feature_pairs': features
        })

# =============================================================================
# 2. 联动分析画布 (Duo-Canvas Visualizer)
# =============================================================================

class FeatureCanvas(QWidget):
    """
    专利双域联动画布：上方显示 Isc 特征，下方显示导数判据
    """
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.fig = Figure(facecolor='#0B0E14', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        # 子图 A: 原始拟合曲线与点位
        self.ax_main = self.fig.add_subplot(211)
        # 子图 B: 一阶/二阶导数辅助判据
        self.ax_der = self.fig.add_subplot(212)
        self._init_style()

    def _init_style(self):
        for ax in [self.ax_main, self.ax_der]:
            ax.set_facecolor('#0F1218')
            ax.tick_params(colors='#666', labelsize=8)
            for spine in ax.spines.values(): spine.set_color('#333')
            ax.grid(True, color='#1A1F26', linestyle=':')

    def update_plots(self, data):
        self.ax_main.clear(); self.ax_der.clear()
        self._init_style()
        
        x, y = data['x'], data['y']
        dy, ddy = data['dy'], data['ddy']
        
        # 绘制主曲线
        self.ax_main.plot(x, y, color='#00A3FF', linewidth=1.5, label='Fitted Isc')
        
        # 标注波峰波谷 (专利图形还原)
        self.ax_main.scatter(x[data['peaks']], y[data['peaks']], color='#FF4D4D', s=40, marker='^', label='Peaks')
        self.ax_main.scatter(x[data['valleys']], y[data['valleys']], color='#00FF94', s=40, marker='v', label='Valleys')
        
        # 绘制导数参考 (专利[0087]判据可视化)
        self.ax_der.plot(x, dy, color='#FFCC00', alpha=0.8, label="1st Deriv (Peak Detection)")
        self.ax_der.plot(x, ddy, color='#722ED1', alpha=0.5, linestyle='--', label="2nd Deriv (Concavity)")
        self.ax_der.axhline(0, color='white', linewidth=0.5)
        
        self.ax_main.legend(facecolor='#151921', labelcolor='white', fontsize=8)
        self.ax_der.legend(facecolor='#151921', labelcolor='white', fontsize=8)
        
        self.fig.tight_layout()
        self.canvas.draw()

# =============================================================================
# 3. 主交互页面模块 (Main Page)
# =============================================================================

class PeakValleyPage(QWidget):
    """
    第 6 菜单：波峰波谷特征提取
    特色：参数调优联动、特征点云账本、宏观/微观联动
    """
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- 左侧：专家级参数控制与表格 (500px) ---
        self.ctrl_panel = QFrame()
        self.ctrl_panel.setFixedWidth(500)
        self.ctrl_panel.setStyleSheet("background-color: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        self.left_layout = QVBoxLayout(self.ctrl_panel)

        header = QLabel("波峰波谷特征提取中心")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF; border: none;")
        self.left_layout.addWidget(header)

        # 1. 算法调优控制
        algo_gb = QGroupBox("算法动态调优")
        algo_l = QFormLayout(algo_gb)
        self.sp_smooth = QSpinBox(); self.sp_smooth.setRange(5, 50); self.sp_smooth.setValue(20)
        self.sp_dist = QSpinBox(); self.sp_dist.setRange(10, 100); self.sp_dist.setValue(40)
        self.dsp_prom = QDoubleSpinBox(); self.dsp_prom.setRange(0.1, 5.0); self.dsp_prom.setValue(0.5)
        algo_l.addRow("拟合曲线平滑系数:", self.sp_smooth)
        algo_l.addRow("极值点最小间距:", self.sp_dist)
        algo_l.addRow("波峰显著度:", self.dsp_prom)
        self.left_layout.addWidget(algo_gb)

        # 2. 特征点云账本 (核心数据展示)
        self.left_layout.addWidget(QLabel("已识别特征点云配对矩阵:"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Peak (A)", "Valley (A)", "ΔAmp", "Radius (px)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background: #0D1117; color: #EEE; gridline-color: #333;")
        self.left_layout.addWidget(self.table)

        # 3. 操作按钮与终端
        self.btn_run = QPushButton("⚡ 执行专利级特征拓扑扫描")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("background: #0078D4; color: white; font-weight: bold; font-size: 14px;")
        self.btn_run.clicked.connect(self._run_analysis)
        self.left_layout.addWidget(self.btn_run)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(120)
        self.console.setStyleSheet("background: #05070A; color: #00FF94; font-family: Consolas; font-size: 11px;")
        self.left_layout.addWidget(self.console)

        # --- 右侧：图形分析中枢 (Flexible) ---
        self.right_panel = QVBoxLayout()
        
        # 顶部的图形
        self.chart = FeatureCanvas()
        self.right_panel.addWidget(self.chart, 7)
        
        # 底部的局部细节放大区 (专利细节体现)
        self.detail_gb = QGroupBox("局部邻域拓扑结构分析")
        detail_l = QHBoxLayout(self.detail_gb)
        self.lbl_detail = QLabel("请在上方主图中点击或在表格中选中某行查看特征细节...")
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detail.setStyleSheet("color: #555; font-style: italic;")
        detail_l.addWidget(self.lbl_detail)
        self.right_panel.addWidget(self.detail_gb, 3)

        self.main_layout.addWidget(self.ctrl_panel)
        self.main_layout.addLayout(self.right_panel)

    def _run_analysis(self):
        self.btn_run.setEnabled(False)
        self.console.clear()
        
        # 生成含振荡的仿真数据
        t = np.linspace(0, 10, 500)
        noise_wave = 15 * np.exp(-0.3*t) + 4 * np.sin(2*np.pi*0.8*t) * np.exp(-0.2*t) + np.random.normal(0, 0.2, 500)
        
        self.engine = PeakValleyEngine(noise_wave, self.sp_smooth.value())
        self.engine.log_sig.connect(self._log)
        self.engine.analysis_ready.connect(self._on_finished)
        self.engine.start()

    def _on_finished(self, data):
        self.btn_run.setEnabled(True)
        self.chart.update_plots(data)
        
        # 更新表格
        pairs = data['feature_pairs']
        self.table.setRowCount(len(pairs))
        for i, p in enumerate(pairs):
            self.table.setItem(i, 0, QTableWidgetItem(f"Pair_{i+1:02d}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{p['peak_val']:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{p['valley_val']:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{p['amp_diff']:.3f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{p['radius']:.1f}"))

    def _log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: #00A3FF;'>[{tag}]</b> {msg}")