import sys
import math
import time
import numpy as np
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# =============================================================================
# 1. 专利核心数学引擎：多维特征融合与归一化分级
# =============================================================================

class QualityEvaluationEngine(QThread):
    """
    专利[0113]-[0121] 综合质量评估解算引擎
    生成 Ti, Ui 并计算 Wi，最终执行归一化
    """
    result_ready = pyqtSignal(dict)
    log_sig = pyqtSignal(str, str)

    def __init__(self, num_devices):
        super().__init__()
        self.num_devices = num_devices
        self._abort = False

    def run(self):
        self.log_sig.emit("SYS", ">>> 启动综合质量分级评定引擎 (Quality Grading Engine)...")
        time.sleep(0.5)

        # 1. 仿真获取前序模块的解算结果 (Ti 和 Ui)
        # 正常器件 Ti较高，Ui也较高；缺陷器件双低或单低
        t_scores = []
        u_scores =[]
        
        self.log_sig.emit("DATA", "正在聚合前序模块数据：提取趋势显著性 T_i 与 一致性 U_i...")
        for i in range(self.num_devices):
            if self._abort: return
            
            # 设定 15% 概率为潜在故障器件
            if np.random.rand() < 0.15:
                t_val = np.random.uniform(0.1, 0.5)
                u_val = np.random.uniform(0.2, 0.6)
                self.log_sig.emit("WARN", f"[Device_{i:02d}] 发现前序特征衰退：Ti={t_val:.2f}, Ui={u_val:.2f}")
            else:
                t_val = np.random.uniform(0.7, 1.5)
                u_val = np.random.uniform(0.8, 0.99)
                
            t_scores.append(t_val)
            u_scores.append(u_val)
            time.sleep(0.02)

        t_scores = np.array(t_scores)
        u_scores = np.array(u_scores)

        # 2. 计算质量评估系数 Wi = Ti * Ui (专利[0114])
        w_scores = t_scores * u_scores
        self.log_sig.emit("MATH", "执行专利融合公式: W_i = T_i × U_i 计算完毕。")

        # 3. 执行归一化处理 (专利[0120]-[0121])
        # Min-Max 归一化映射到 [0, 1] 区间
        w_min, w_max = np.min(w_scores), np.max(w_scores)
        if w_max == w_min:
            w_norm = np.ones_like(w_scores)
        else:
            w_norm = (w_scores - w_min) / (w_max - w_min)
            
        self.log_sig.emit("MATH", "已完成 W_i 的全局空间归一化处理。")
        self.log_sig.emit("SUCCESS", "质量评估特征空间构建完成，准备执行阈值切割。")

        payload = {
            't_scores': t_scores,
            'u_scores': u_scores,
            'w_scores': w_scores,
            'w_norm': w_norm
        }
        self.result_ready.emit(payload)

# =============================================================================
# 2. 独创控件：高拟真工业级环形仪表盘 (Analog Gauge Widget)
# =============================================================================

class IndustrialGauge(QWidget):
    """
    纯手写底层渲染的工业仪表盘
    支持物理弹道平滑过渡动画 (Ease-Out)
    用于实时展示批次“综合良率”
    """
    def __init__(self):
        super().__init__()
        self.setMinimumSize(250, 250)
        self.value = 0.0
        self.target_value = 0.0
        self.threshold = 75.0 # 对应专利 0.75 阈值
        
        # 动画引擎
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate_tick)
        self.anim_timer.start(16) # 60 FPS

    def set_value(self, val):
        self.target_value = max(0.0, min(100.0, val))

    def set_threshold(self, th):
        self.threshold = th * 100
        self.update()

    def _animate_tick(self):
        # 阻尼插值实现平滑指针动画
        diff = self.target_value - self.value
        if abs(diff) > 0.05:
            self.value += diff * 0.1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        side = min(rect.width(), rect.height()) - 20
        center = rect.center()
        
        # 坐标系平移到中心
        painter.translate(center)
        
        # 1. 绘制仪表盘背景底座
        painter.setPen(Qt.PenStyle.NoPen)
        bg_gradient = QRadialGradient(0, 0, side/2)
        bg_gradient.setColorAt(0.0, QColor(25, 30, 40))
        bg_gradient.setColorAt(0.9, QColor(10, 15, 20))
        bg_gradient.setColorAt(1.0, QColor(40, 50, 60))
        painter.setBrush(bg_gradient)
        painter.drawEllipse(QPointF(0, 0), side/2, side/2)

        # 2. 绘制阈值色带 (红黄绿)
        start_angle = 210  # 左下角
        span_angle = -240  # 顺时针扫过240度
        
        pen_thick = side * 0.08
        arc_rect = QRectF(-side/2 + 20, -side/2 + 20, side - 40, side - 40)
        
        # 红色段 (0 -> threshold)
        red_span = span_angle * (self.threshold / 100.0)
        painter.setPen(QPen(QColor(255, 77, 77, 200), pen_thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.drawArc(arc_rect, start_angle * 16, int(red_span * 16))
        
        # 绿色段 (threshold -> 100)
        green_span = span_angle - red_span
        green_start = start_angle + red_span
        painter.setPen(QPen(QColor(0, 255, 148, 200), pen_thick, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.drawArc(arc_rect, int(green_start * 16), int(green_span * 16))

        # 3. 绘制刻度线
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        for i in range(11):
            angle = math.radians(start_angle + span_angle * (i / 10.0))
            r_in = side/2 - 40 if i % 5 == 0 else side/2 - 30
            r_out = side/2 - 20
            painter.drawLine(QPointF(r_in * math.cos(angle), -r_in * math.sin(angle)),
                             QPointF(r_out * math.cos(angle), -r_out * math.sin(angle)))

        # 4. 绘制数值文本
        painter.setPen(QColor(0, 163, 255))
        painter.setFont(QFont("Consolas", int(side*0.15), QFont.Weight.Bold))
        painter.drawText(QRectF(-side/2, side/4, side, side/4), Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}%")
        
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Segoe UI", int(side*0.06)))
        painter.drawText(QRectF(-side/2, side/4 + 25, side, side/4), Qt.AlignmentFlag.AlignCenter, "BATCH YIELD RATE")

        # 5. 绘制动态指针 (Needle)
        painter.save()
        current_angle = start_angle + span_angle * (self.value / 100.0)
        painter.rotate(-current_angle) # Qt 的 rotate 是顺时针，数学需要调整
        
        needle_path = QPainterPath()
        needle_path.moveTo(5, 0)
        needle_path.lineTo(-5, 0)
        needle_path.lineTo(0, side/2 - 45)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 140, 0))
        painter.drawPath(needle_path)
        
        # 指针中心轴承
        painter.setBrush(QColor(40, 45, 50))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(QPointF(0, 0), 10, 10)
        painter.restore()

# =============================================================================
# 3. 3D 气泡散点渲染图 (3D Bubble Chart Canvas)
# =============================================================================

class Bubble3DCanvas(QWidget):
    """三维评估空间：X(Ti), Y(Ui), Z(Wi_norm)"""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.fig = Figure(facecolor='#151921', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#151921')
        self._init_style()

    def _init_style(self):
        self.ax.xaxis.set_pane_color((0.1, 0.12, 0.15, 1.0))
        self.ax.yaxis.set_pane_color((0.1, 0.12, 0.15, 1.0))
        self.ax.zaxis.set_pane_color((0.1, 0.12, 0.15, 1.0))
        self.ax.tick_params(colors='#888', labelsize=8)
        self.ax.set_xlabel('Trend Ti', color='#888')
        self.ax.set_ylabel('Consistency Ui', color='#888')
        self.ax.set_zlabel('Norm Wi', color='#888')

    def render_3d(self, data, threshold):
        self.ax.clear()
        self._init_style()
        
        t = data['t_scores']
        u = data['u_scores']
        w = data['w_norm']
        
        # 根据阈值判定颜色 (绿=Pass, 红=Fail)
        colors =['#00FF94' if val >= threshold else '#FF4D4D' for val in w]
        # 气泡大小与质量评分成正比
        sizes = 100 + (w * 300)
        
        scatter = self.ax.scatter(t, u, w, c=colors, s=sizes, alpha=0.7, edgecolors='white', linewidth=0.5)
        
        # 绘制专利阈值切分平面 (Z = threshold)
        xx, yy = np.meshgrid(np.linspace(min(t), max(t), 2), np.linspace(min(u), max(u), 2))
        zz = np.ones_like(xx) * threshold
        self.ax.plot_surface(xx, yy, zz, color='#FFCC00', alpha=0.2)
        
        self.ax.set_title(f"3D Quality Assessment Space (Threshold Cut: {threshold:.2f})", color='white', pad=20)
        self.fig.tight_layout()
        self.canvas.draw()

# =============================================================================
# 4. 主控页面统筹整合 (Quality Evaluator Page)
# =============================================================================

class QualityEvaluationPage(QWidget):
    """
    第十个菜单：质量分级评定 (Wi)
    集成底层手绘仪表、3D 图表、动态阈值切片及排序矩阵
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self.cached_data = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ---------------------------------------------------------
        # 左侧：配置、仪表盘与审计监控 (400px)
        # ---------------------------------------------------------
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(400)
        self.left_panel.setStyleSheet("background-color: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        self.left_layout = QVBoxLayout(self.left_panel)

        title = QLabel("质量分级评定")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF; border: none;")
        self.left_layout.addWidget(title)
        
        info = QLabel("执行归一化与排故逻辑判定")
        info.setStyleSheet("color: #8B949E; font-size: 11px; border: none;")
        self.left_layout.addWidget(info)

        # A. 算法参数
        cfg_gb = QGroupBox("评定边界条件")
        cfg_l = QFormLayout(cfg_gb)
        self.sp_dev = QSpinBox(); self.sp_dev.setRange(10, 100); self.sp_dev.setValue(30)
        cfg_l.addRow("载入聚合批次规模 (N):", self.sp_dev)
        self.left_layout.addWidget(cfg_gb)

        # B. 良率仪表盘
        gauge_gb = QGroupBox("批次健康度监控")
        gauge_l = QVBoxLayout(gauge_gb)
        self.gauge = IndustrialGauge()
        gauge_l.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        self.left_layout.addWidget(gauge_gb)

        # C. 执行与进度
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10); self.pbar.setTextVisible(False)
        self.left_layout.addWidget(self.pbar)

        self.btn_run = QPushButton("⚡ 聚合全特征并执行分级评估")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { background: #0078D4; color: white; font-weight: bold; font-size: 15px; border-radius: 4px;}
            QPushButton:hover { background: #0086F0; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.btn_run.clicked.connect(self._execute_evaluation)
        self.left_layout.addWidget(self.btn_run)

        # D. 审计控制台
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #090C10; color: #00FF94; font-family: Consolas; font-size: 11px; border: 1px solid #222;")
        self.left_layout.addWidget(QLabel("多维特征聚合推演踪迹:")); self.left_layout.addWidget(self.console)

        # ---------------------------------------------------------
        # 右侧：上下分割 (3D 图表 + 评估矩阵矩阵)
        # ---------------------------------------------------------
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部：3D 动态交互空间与阈值滑块
        self.chart_container = QWidget()
        chart_l = QVBoxLayout(self.chart_container)
        chart_l.setContentsMargins(0,0,0,0)
        
        # 动态阈值控制器 (核心交互)
        ctrl_bar = QWidget()
        ctrl_bar.setStyleSheet("background: #1A1F26; border-radius: 6px; padding: 5px;")
        ctrl_l = QHBoxLayout(ctrl_bar)
        ctrl_l.addWidget(QLabel("动态熔断阈值切割点:"))
        
        self.sl_threshold = QSlider(Qt.Orientation.Horizontal)
        self.sl_threshold.setRange(0, 100); self.sl_threshold.setValue(75) # 默认 0.75
        self.lbl_th_val = QLabel("0.75")
        self.lbl_th_val.setStyleSheet("color: #FFCC00; font-weight: bold; font-size: 14px;")
        
        self.sl_threshold.valueChanged.connect(self._on_threshold_changed)
        
        ctrl_l.addWidget(self.sl_threshold); ctrl_l.addWidget(self.lbl_th_val)
        chart_l.addWidget(ctrl_bar)
        
        # 3D 渲染器
        self.bubble_3d = Bubble3DCanvas()
        chart_l.addWidget(self.bubble_3d)
        self.right_splitter.addWidget(self.chart_container)
        
        # 下半部：评估分类矩阵
        self.table_box = QGroupBox("归一化分级判定矩阵")
        table_l = QVBoxLayout(self.table_box)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["器件 ID", "趋势 Ti", "一致性 Ui", "评估分 Wi", "归一化 Norm", "状态评估结论"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #0D1117; color: #EEE; gridline-color: #30363D; border: 1px solid #30363D; }
            QTableWidget::item { padding: 5px; }
        """)
        table_l.addWidget(self.table)
        self.right_splitter.addWidget(self.table_box)
        
        self.right_splitter.setStretchFactor(0, 6)
        self.right_splitter.setStretchFactor(1, 4)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_splitter, 1)

    # --- 交互与业务逻辑 ---

    def _execute_evaluation(self):
        self.btn_run.setEnabled(False)
        self.console.clear()
        self.pbar.setRange(0, 0) # 跑马灯加载模式
        
        self.engine = QualityEvaluationEngine(self.sp_dev.value())
        self.engine.log_sig.connect(self._append_log)
        self.engine.result_ready.connect(self._on_evaluation_complete)
        self.engine.start()

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00A3FF" if tag == "MATH" else ("#FF8C00" if tag == "WARN" else "#00FF94")
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: {color};'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _on_evaluation_complete(self, data):
        self.btn_run.setEnabled(True)
        self.pbar.setRange(0, 100); self.pbar.setValue(100)
        self.cached_data = data
        
        # 触发全盘重新渲染
        self._on_threshold_changed(self.sl_threshold.value())

    def _on_threshold_changed(self, val):
        """当滑块改变时，实时重算所有器件的及格状态，并产生多图联动"""
        threshold = val / 100.0
        self.lbl_th_val.setText(f"{threshold:.2f}")
        self.gauge.set_threshold(threshold)
        
        if not self.cached_data: return
        
        n = self.sp_dev.value()
        w_norm = self.cached_data['w_norm']
        t_scores = self.cached_data['t_scores']
        u_scores = self.cached_data['u_scores']
        w_scores = self.cached_data['w_scores']
        
        # 1. 刷新 3D 图表 (重新着色与切割)
        self.bubble_3d.render_3d(self.cached_data, threshold)
        
        # 2. 刷新判定矩阵表格 (实时着色)
        self.table.setRowCount(n)
        pass_count = 0
        for i in range(n):
            self.table.setItem(i, 0, QTableWidgetItem(f"Device_{i:02d}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{t_scores[i]:.3f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{u_scores[i]:.3f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{w_scores[i]:.3f}"))
            
            norm_val = w_norm[i]
            norm_item = QTableWidgetItem(f"{norm_val:.4f}")
            norm_item.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.table.setItem(i, 4, norm_item)
            
            # 专利[0121] 核心判定逻辑
            if norm_val >= threshold:
                status = "PASS (生产正常)"
                color = QColor('#00FF94')
                pass_count += 1
            else:
                status = "FAIL (存在生产故障)"
                color = QColor('#FF4D4D')
                
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(color))
            norm_item.setForeground(QBrush(color))
            self.table.setItem(i, 5, status_item)

        # 3. 计算并驱动左侧仪表盘动画
        yield_rate = (pass_count / n) * 100.0
        self.gauge.set_value(yield_rate)
        self._append_log("UI", f"阈值切片已重置为 {threshold:.2f}。当前批次动态良率计算为: {yield_rate:.1f}%")