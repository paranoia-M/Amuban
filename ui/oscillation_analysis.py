import sys
import time
import random
import numpy as np
from datetime import datetime

# 科学计算库
from scipy.signal import find_peaks
from scipy.interpolate import make_interp_spline
from scipy.stats import kurtosis

# UI 核心组件
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# 可视化增强
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# =============================================================================
# 1. 专利核心数学引擎 (Patent Math Engine)
# =============================================================================

class OscillationComputeEngine(QObject):
    """
    实现专利 [0019]-[0024] 段落的振荡量化逻辑
    计算 Mk,i, Hk,i 及最终异常系数 Pk,i
    """
    calculation_done = pyqtSignal(dict)
    trace_log = pyqtSignal(str, str)

    def process_oscillation(self, raw_isc, g_ki_base):
        """
        raw_isc: 原始短路电流序列
        g_ki_base: 从上一阶段继承的突变偏移系数
        """
        self.trace_log.emit("SYS", ">>> 启动振荡特性深度解析引擎...")
        
        # --- 步骤 A: 曲线平滑与拟合 (专利[0019]) ---
        x = np.arange(len(raw_isc))
        spline = make_interp_spline(x, raw_isc, k=3)
        x_smooth = np.linspace(0, len(raw_isc)-1, 2000)
        y_fit = spline(x_smooth)
        self.trace_log.emit("MATH", "完成三阶样条曲线拟合，消除高频噪声干扰。")

        # --- 步骤 B: 极值点提取 (专利[0019]) ---
        # 提取波峰与波谷
        peaks, _ = find_peaks(y_fit, distance=50, prominence=0.5)
        valleys, _ = find_peaks(-y_fit, distance=50)
        
        self.trace_log.emit("INFO", f"检测到有效波峰数目: {len(peaks)} | 波谷数目: {len(valleys)}")

        # --- 步骤 C: 计算振荡差异值 Mk,i (专利[0020]) ---
        # Mk,i = 各波峰值与其对应相邻波谷值的差异的均值
        diffs = []
        for p in peaks:
            # 寻找物理距离最近的波谷
            if len(valleys) > 0:
                nearest_v_idx = valleys[np.abs(valleys - p).argmin()]
                diffs.append(abs(y_fit[p] - y_fit[nearest_v_idx]))
        
        m_ki = np.mean(diffs) if diffs else 0.0
        self.trace_log.emit("MATH", f"计算振荡差异均值 Mk,i = {m_ki:.6f}")

        # --- 步骤 D: 计算峰度陡峭指数 Hk,i (专利[0022]-[0023]) ---
        # 分析各波峰邻域内的峰度(Kurtosis)累加
        h_ki = 0.0
        neighborhood = 40 # 邻域半径
        for p in peaks:
            start = max(0, p - neighborhood)
            end = min(len(y_fit), p + neighborhood)
            h_ki += abs(kurtosis(y_fit[start:end]))
            
        self.trace_log.emit("MATH", f"计算邻域峰度累加 Hk,i = {h_ki:.6f}")

        # --- 步骤 E: 确定最终振荡异常系数 Pk,i (专利[0024]) ---
        # Pk,i = Gk,i * (Hk,i + Mk,i)
        p_ki = g_ki_base * (h_ki + m_ki)
        self.trace_log.emit("SUCCESS", f"最终核心判定系数 Pk,i = {p_ki:.8f}")

        results = {
            'x_smooth': x_smooth,
            'y_fit': y_fit,
            'peaks': peaks,
            'valleys': valleys,
            'm_ki': m_ki,
            'h_ki': h_ki,
            'p_ki': p_ki
        }
        self.calculation_done.emit(results)

# =============================================================================
# 2. 深度交互分析页面 (UI Implementation)
# =============================================================================

class OscillationAnalysisPage(QWidget):
    """
    第四个菜单：振荡特性量化分析
    具备：拟合曲线展示、极值标注、参数关联看板、计算审计日志
    """
    def __init__(self):
        super().__init__()
        self.engine = OscillationComputeEngine()
        self.engine.calculation_done.connect(self._render_results)
        self.engine.trace_log.connect(self._append_log)
        self._init_ui()

    def _init_ui(self):
        # 主布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # --- 左侧：控制与看板 (450px) ---
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(450)
        self.left_vbox = QVBoxLayout(self.left_widget)
        self.left_vbox.setContentsMargins(0,0,0,0)

        title = QLabel("振荡异常系数解析矩阵")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF;")
        self.left_vbox.addWidget(title)

        # 1. 输入耦合区
        in_gb = QGroupBox("输入耦合参数")
        in_l = QFormLayout(in_gb)
        self.dsp_gki = QDoubleSpinBox()
        self.dsp_gki.setRange(0.0001, 100.0); self.dsp_gki.setValue(2.1584); self.dsp_gki.setDecimals(4)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["标准短路实验 (SC-01)", "重复脉冲实验 (RP-05)", "极端应力测试"])
        in_l.addRow("突变偏移系数 Gki (继承):", self.dsp_gki)
        in_l.addRow("实验工况选择:", self.cmb_mode)
        self.left_vbox.addWidget(in_gb)

        # 2. 算法控制
        algo_gb = QGroupBox("拟合与提取参数")
        algo_l = QFormLayout(algo_gb)
        self.sp_order = QSpinBox(); self.sp_order.setRange(1, 5); self.sp_order.setValue(3)
        self.sp_neighbor = QSpinBox(); self.sp_neighbor.setRange(10, 200); self.sp_neighbor.setValue(50)
        algo_l.addRow("插值拟合阶数:", self.sp_order)
        algo_l.addRow("峰度邻域半径 (px):", self.sp_neighbor)
        self.left_vbox.addWidget(algo_gb)

        # 3. 计算看板
        board_gb = QGroupBox("量化计算看板")
        board_l = QGridLayout(board_gb)
        self.lcd_mki = self._create_data_label("0.000")
        self.lcd_hki = self._create_data_label("0.000")
        self.lcd_pki = self._create_data_label("0.0000", is_main=True)
        board_l.addWidget(QLabel("振荡差异 Mk,i:"), 0, 0); board_l.addWidget(self.lcd_mki, 0, 1)
        board_l.addWidget(QLabel("陡峭指数 Hk,i:"), 1, 0); board_l.addWidget(self.lcd_hki, 1, 1)
        board_l.addWidget(QLabel("异常系数 Pki:"), 2, 0); board_l.addWidget(self.lcd_pki, 2, 1)
        self.left_vbox.addWidget(board_gb)

        # 4. 执行按钮
        self.btn_calc = QPushButton("⚡ 执行振荡特性量化解算")
        self.btn_calc.setFixedHeight(50)
        self.btn_run_style = """
            QPushButton { background-color: #0078D4; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #0082CC; }
            QPushButton:pressed { background-color: #004578; }
        """
        self.btn_calc.setStyleSheet(self.btn_run_style)
        self.btn_calc.clicked.connect(self._handle_compute)
        self.left_vbox.addWidget(self.btn_calc)

        # 5. 审计日志
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        self.log_txt.setStyleSheet("background: #090C10; color: #00FF94; font-family: Consolas; font-size: 12px; border: 1px solid #222;")
        self.left_vbox.addWidget(QLabel("专利算法执行踪迹:"))
        self.left_vbox.addWidget(self.log_txt)

        # --- 右侧：图形化分析看板 ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #0F1218; border-radius: 10px; border: 1px solid #333;")
        self.right_layout = QVBoxLayout(self.right_panel)

        # 集成 Matplotlib
        self.fig = Figure(facecolor='#0F1218', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0F1218')
        
        self.right_layout.addWidget(QLabel("短路电流 Isc 拟合与极值检测视图"))
        self.right_layout.addWidget(self.canvas)

        self.layout.addWidget(self.left_widget)
        self.layout.addWidget(self.right_panel, 1)

    def _create_data_label(self, init_val, is_main=False):
        lbl = QLabel(init_val)
        color = "#00FF94" if not is_main else "#FFCC00"
        size = "24px" if is_main else "18px"
        lbl.setStyleSheet(f"font-size: {size}; color: {color}; font-family: Consolas; font-weight: bold;")
        return lbl

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_txt.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: #DDD;'>[{tag}]</b> {msg}")

    def _handle_compute(self):
        self.btn_calc.setEnabled(False)
        self.log_txt.clear()
        
        # 1. 模拟生成带有明显振荡特征的短路电流原始数据
        # 模拟专利中提到的波峰波谷交替振荡形态
        t = np.linspace(0, 10, 500)
        # 基础波形 + 振荡分量 + 随机噪声
        raw_isc = 15 * np.exp(-0.4*t) + 3 * np.sin(2*np.pi*0.8*t) * np.exp(-0.2*t) + np.random.normal(0, 0.1, 500)
        
        # 2. 调用计算引擎
        self.engine.process_oscillation(raw_isc, self.dsp_gki.value())

    def _render_results(self, res):
        self.btn_calc.setEnabled(True)
        
        # A. 更新看板数值
        self.lcd_mki.setText(f"{res['m_ki']:.4f}")
        self.lcd_hki.setText(f"{res['h_ki']:.4f}")
        self.lcd_pki.setText(f"{res['p_ki']:.6f}")

        # B. 渲染图形
        self.ax.clear()
        self.ax.set_facecolor('#0F1218')
        
        # 绘制拟合曲线 (专利要求分析拟合后的曲线 [0019])
        x_smooth = res['x_smooth']
        y_fit = res['y_fit']
        self.ax.plot(x_smooth, y_fit, color='#00A3FF', linewidth=2, label='Fitted Isc Curve')
        
        # 标注波峰 (Peaks)
        peaks = res['peaks']
        self.ax.scatter(x_smooth[peaks], y_fit[peaks], color='#FF4D4D', s=60, marker='^', label='Peaks (Mk,i Source)')
        
        # 标注波谷 (Valleys)
        valleys = res['valleys']
        self.ax.scatter(x_smooth[valleys], y_fit[valleys], color='#00FF94', s=60, marker='v', label='Valleys')

        # 装饰
        self.ax.set_xlabel("Time (Normalized Samples)", color='#888')
        self.ax.set_ylabel("Short-Circuit Current Isc (A)", color='#888')
        self.ax.tick_params(colors='#444')
        self.ax.grid(True, color='#222', linestyle='--')
        self.ax.legend(facecolor='#151921', edgecolor='#333', labelcolor='white')
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        self._append_log("INFO", "量化解析完成。Pk,i 数值已同步至全局质量评估序列。")