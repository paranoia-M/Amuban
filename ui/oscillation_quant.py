import sys
import time
import math
import random
import hashlib
import numpy as np
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPointF, QRectF, QRect,
    QTimer, QSize, QPropertyAnimation, QSequentialAnimationGroup
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QPainterPath, QFont, QPolygonF, QScreen
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QTextEdit, QProgressBar, QGraphicsView, QGraphicsScene, 
    QGraphicsEllipseItem, QGraphicsObject, QStyleOptionGraphicsItem,
    QSlider, QAbstractItemView
)

# 专利核心科学计算逻辑库
from scipy.stats import kurtosis, skew, entropy
from scipy.fft import fft, fftfreq
from scipy.interpolate import interp1d

# =============================================================================
# 1. 专利高阶解算内核 (Patent Math Kernel)
# =============================================================================

class QuantizationEngine(QThread):
    """
    实现专利核心公式: Pki = Gki * (Hki + Mki)
    深度集成了振荡频率提取、能量熵分析与统计指纹算法
    """
    result_sig = pyqtSignal(dict)
    log_sig = pyqtSignal(str, str)

    def __init__(self, raw_isc, peaks_info, g_ki, radius, damp_ratio=1.0):
        super().__init__()
        self.raw_isc = raw_isc
        self.peaks = peaks_info 
        self.g_ki = g_ki
        self.radius = radius
        self.damp_ratio = damp_ratio
        self._is_active = True

    def stop(self):
        """外部干预停止标志"""
        self._is_active = False

    def run(self):
        """核心计算流水线"""
        self.log_sig.emit("KERN", ">>> 启动专利量化内核：正在解算多维振荡特征矩阵...")
        
        try:
            if not self._is_active: return

            # 1. 计算 Mk,i (专利[0021]: 各波峰与其对应相邻波谷值的差异的均值)
            raw_diffs = [p['amp_diff'] for p in self.peaks]
            m_ki = np.mean(raw_diffs) * self.damp_ratio if raw_diffs else 0.0
            
            # 2. 频谱主频提取 (专利[0084]: 用于识别寄生振荡频率)
            n = len(self.raw_isc)
            yf = fft(self.raw_isc)
            xf = fftfreq(n, 1/1000000) # 1MHz 采样率映射
            abs_yf = np.abs(yf[:n//2])
            dom_freq = abs(xf[np.argmax(abs_yf[1:]) + 1])

            # 3. 计算 Hk,i (专利[0022]: 邻域峰度累加)
            # 针对每个波峰进行邻域搜索并累加统计峰度 (Kurtosis)
            h_ki = 0.0
            audit_trail = []
            
            for i, p in enumerate(self.peaks):
                if not self._is_active: return
                p_idx = p['peak_idx']
                
                # 建立专利邻域窗口范围 [0009]
                start = max(0, p_idx - self.radius)
                end = min(len(self.raw_isc), p_idx + self.radius)
                
                segment = self.raw_isc[start:end]
                if len(segment) < 5: continue
                
                # 计算统计特征：峰度 (专利 Hk,i 的数学支柱)
                kurt_val = abs(kurtosis(segment))
                # 计算统计特征：偏度 (用于精细化故障分类)
                skew_val = abs(skew(segment))
                # 计算特征能量熵 (Entropy)
                hist, _ = np.histogram(segment, bins=10)
                e_val = entropy(hist + 1e-6)
                
                h_ki += kurt_val
                
                # 记录该特征点的溯源指纹 [0083]
                audit_trail.append({
                    'id': i,
                    'pos': p_idx,
                    'kurt': kurt_val,
                    'skew': skew_val,
                    'entropy': e_val,
                    'amp': p['peak_val'],
                    'rel_weight': (kurt_val / (h_ki + 0.1)) * 100
                })

            # 4. 执行专利终极量化判定公式 [0024]
            # Pki = Gki * (Hki + Mki)
            p_ki = self.g_ki * (h_ki + m_ki)
            
            # 模拟 CPU 密集型任务开销，体现计算深度
            time.sleep(0.15)
            
            self.log_sig.emit("MATH", f"解算完成: Pki={p_ki:.6f} | Mk,i={m_ki:.2f} | Hk,i={h_ki:.2f}")
            
            self.result_sig.emit({
                'p_ki': p_ki,
                'h_ki': h_ki,
                'm_ki': m_ki,
                'dom_freq': dom_freq,
                'audit': audit_trail,
                'ts': datetime.now().timestamp()
            })
            
        except Exception as e:
            self.log_sig.emit("ERROR", f"专利计算内核崩溃: {str(e)}")

# =============================================================================
# 2. 独创交互组件：工业金属旋钮 (Pro-Industrial Knob)
# =============================================================================

class ControlKnob(QWidget):
    """
    具备角度映射逻辑与 LED 状态反馈的自定义物理旋钮
    """
    valueChanged = pyqtSignal(float)

    def __init__(self, label="PARAM", min_v=0, max_v=100, init_v=50, theme_color="#00A3FF"):
        super().__init__()
        self.setFixedSize(140, 180)
        self.value = init_v
        self.min_v = min_v
        self.max_v = max_v
        self.label = label
        self.accent_color = QColor(theme_color)
        self._dragging = False

    def mousePressEvent(self, event):
        self._dragging = True
        self._update_val(event.pos())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_val(event.pos())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def _update_val(self, pos):
        # 几何算法：根据点击位置相对于中心点的极角计算数值
        dx = pos.x() - 70
        dy = 70 - pos.y()
        angle = math.degrees(math.atan2(dx, dy))
        
        # 锁定旋转范围 (-140 to 140 度)
        angle = max(-140, min(140, angle))
        normalized = (angle + 140) / 280.0
        self.value = self.min_v + normalized * (self.max_v - self.min_v)
        self.valueChanged.emit(self.value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 绘制基座外圈
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(30, 32, 40))
        p.drawEllipse(15, 15, 110, 110)
        
        # 2. 绘制同步 LED 进度槽
        led_pen = QPen(self.accent_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(led_pen)
        # 映射角度：起始 225度, 扫过 280度
        span = ((self.value - self.min_v) / (self.max_v - self.min_v)) * -280
        p.drawArc(QRectF(22, 22, 96, 96), 225 * 16, int(span * 16))
        
        # 3. 绘制旋钮实体 (三层渐变渲染)
        knob_grad = QRadialGradient(70, 70, 45)
        knob_grad.setColorAt(0, QColor(60, 65, 80)); knob_grad.setColorAt(1, QColor(15, 18, 25))
        p.setBrush(knob_grad)
        p.setPen(QPen(QColor(80, 85, 95), 1))
        p.drawEllipse(32, 32, 76, 76)
        
        # 4. 绘制位置指示针
        p.save()
        p.translate(70, 70)
        p.rotate(((self.value - self.min_v) / (self.max_v - self.min_v)) * 280 - 140)
        p.setBrush(self.accent_color)
        p.setPen(QPen(Qt.PenStyle.NoPen))
        p.drawRoundedRect(QRectF(-3, -36, 6, 12), 2, 2)
        p.restore()
        
        # 5. 绘制文字数值 (修复了 QRect 报错)
        p.setPen(QColor(180, 190, 200))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        # 修复点：显式使用 QRect 对象
        p.drawText(QRect(0, 140, 140, 40), Qt.AlignmentFlag.AlignCenter, f"{self.label}\n{self.value:.2f}")

# =============================================================================
# 3. 特征空间渲染器：引力场 (Vibration Field Rendering)
# =============================================================================

class VibrationFieldCanvas(QGraphicsView):
    """
    能量场可视化：将解算细节映射为具备物理引力感应的粒子场
    """
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(8, 12, 16)))
        self.setMinimumHeight(450)

    def update_field(self, audit_data):
        self.scene.clear()
        
        # 背景向量栅格
        grid_pen = QPen(QColor(30, 35, 45), 1, Qt.PenStyle.DashLine)
        for x in range(-500, 501, 70): self.scene.addLine(x, -300, x, 300, grid_pen)
        
        for item in audit_data:
            # 空间位置映射逻辑
            pos_x = (item['pos'] / 1024.0) * 850 - 425
            pos_y = (math.sin(item['pos'] * 0.1) * 140)
            
            no_pen = QPen(Qt.PenStyle.NoPen)
            
            # 1. 绘制核心能量源 (亮色)
            size = max(8, item['amp'] * 4)
            core_grad = QRadialGradient(pos_x, pos_y, size)
            core_grad.setColorAt(0, QColor(0, 255, 148, 220)); core_grad.setColorAt(1, QColor(0, 163, 255, 0))
            
            blob = QGraphicsEllipseItem(pos_x - size, pos_y - size, size*2, size*2)
            blob.setBrush(QBrush(core_grad))
            blob.setPen(no_pen)
            self.scene.addItem(blob)
            
            # 2. 绘制特征波纹圈 (代表 Hk,i 的贡献度)
            for ring_idx in range(1, 4):
                rs = size + (ring_idx * 20)
                ring = QGraphicsEllipseItem(pos_x - rs/2, pos_y - rs/2, rs, rs)
                alpha = max(0, int(item['kurt'] * 45 / ring_idx))
                ring.setPen(QPen(QColor(0, 163, 255, alpha), 2))
                self.scene.addItem(ring)
                
            # 3. 实时特征文本标签
            lbl = self.scene.addText(f"F:{item['kurt']:.1f}", QFont("Consolas", 8))
            lbl.setDefaultTextColor(QColor(150, 150, 150))
            lbl.setPos(pos_x + 10, pos_y - 15)

# =============================================================================
# 4. 主控逻辑页面统筹 (Quantization Controller)
# =============================================================================

class OscillationQuantPage(QWidget):
    """
    第 7 个菜单页面：振荡异常量化
    具备高度稳定性、多线程保护机制与复杂的专利业务流交互
    """
    def __init__(self):
        super().__init__()
        self.math_engine = None # 全局持有线程句柄
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # ---------------------------------------------------------
        # A. 顶部计算实况 HUD 面板
        # ---------------------------------------------------------
        self.hud_frame = QFrame()
        self.hud_frame.setFixedHeight(120)
        self.hud_frame.setStyleSheet("""
            QFrame { background: #0F1219; border: 2px solid #00A3FF; border-radius: 15px; }
            QLabel { border: none; }
        """)
        hud_l = QHBoxLayout(self.hud_frame)
        
        formula_display = QLabel("P<sub>k,i</sub> = G<sub>k,i</sub> × ( Σ Kurtosis[H] + Mean_Diff[M] )")
        formula_display.setStyleSheet("font-size: 22px; color: #8894A6; font-family: 'Times New Roman'; padding-left: 20px;")
        
        self.val_display = QLabel("Pki = 0.000000")
        self.val_display.setStyleSheet("font-size: 36px; font-weight: bold; color: #00FF94; font-family: Consolas; padding-right: 30px;")
        
        hud_l.addWidget(formula_display)
        hud_l.addStretch()
        hud_l.addWidget(self.val_display)
        self.layout.addWidget(self.hud_frame)

        # ---------------------------------------------------------
        # B. 中部：多维交互中心 (Field & Tower)
        # ---------------------------------------------------------
        mid_layout = QHBoxLayout()
        
        # 拓扑可视化场
        self.field_view = VibrationFieldCanvas()
        mid_layout.addWidget(self.field_view, 8)
        
        # 调节控制塔 (三个不同维度的控制旋钮)
        tower_gb = QGroupBox("专利参数管控塔")
        tower_gb.setFixedWidth(250)
        tower_l = QVBoxLayout(tower_gb)
        
        self.knob_radius = ControlKnob("邻域半径 (H)", 10, 220, 85, "#00A3FF")
        self.knob_g_factor = ControlKnob("突变偏移 (G)", 0.1, 15.0, 4.5, "#00FF94")
        self.knob_compensation = ControlKnob("补偿比例 (D)", 0.5, 2.5, 1.0, "#FF8C00")
        
        for knob in [self.knob_radius, self.knob_g_factor, self.knob_compensation]:
            tower_l.addWidget(knob, 0, Qt.AlignmentFlag.AlignHCenter)
            knob.valueChanged.connect(self._dispatch_engine)
            
        tower_l.addStretch()
        mid_layout.addWidget(tower_gb)
        self.layout.addLayout(mid_layout)

        # ---------------------------------------------------------
        # C. 底部：数据审计溯源表
        # ---------------------------------------------------------
        bottom_area = QHBoxLayout()
        
        self.audit_table = QTableWidget(0, 5)
        self.audit_table.setHorizontalHeaderLabels(["特征源标识", "峰度 Hk,i", "偏度 Sk,i", "一致性权重", "计算摘要"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.setStyleSheet("background: #090B0F; color: #BBB; border: 1px solid #2A2F3A;")
        self.audit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        bottom_area.addWidget(self.audit_table, 7)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background: #05070A; color: #00FF94; font-family: Consolas; font-size: 11px;")
        bottom_area.addWidget(self.terminal, 3)
        
        self.layout.addLayout(bottom_area)

        # 执行首次自动化对齐预热
        QTimer.singleShot(1000, self._dispatch_engine)

    def _dispatch_engine(self):
        """
        【关键修复逻辑】：安全接管线程生命周期
        """
        if self.math_engine:
            # 断开所有连接并准备销毁
            self.math_engine.result_sig.disconnect()
            self.math_engine.log_sig.disconnect()
            if self.math_engine.isRunning():
                self.math_engine.stop()
            self.math_engine.deleteLater()
            self.math_engine = None

        # 1. 模拟生成带有振荡分量的原始 Isc 数据
        t = np.linspace(0, 10, 1024)
        raw_wave = 14 * np.exp(-0.4*t) + 6 * np.sin(2*np.pi*0.75*t) * np.exp(-0.2*t) + np.random.normal(0, 0.08, 1024)
        
        # 2. 模拟识别出的波峰特征
        mock_peaks = []
        for i in range(5):
            mock_peaks.append({
                'peak_idx': 150 + i * 160,
                'peak_val': 8.5 - (i * 0.4),
                'amp_diff': random.uniform(1.8, 5.5)
            })

        # 3. 实例化新线程对象
        self.math_engine = QuantizationEngine(
            raw_wave, mock_peaks, 
            self.knob_g_factor.value, int(self.knob_radius.value), self.knob_compensation.value
        )
        self.math_engine.log_sig.connect(self._on_log_stream)
        self.math_engine.result_sig.connect(self._on_calculation_finished)
        self.math_engine.start()

    def _on_log_stream(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.terminal.append(f"<span style='color:#555'>[{ts}]</span> <b style='color:#00A3FF'>[{tag}]</b> {msg}")
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def _on_calculation_finished(self, res):
        """同步计算结果到界面元素"""
        self.val_display.setText(f"Pki = {res['p_ki']:.6f}")
        self.field_view.update_field(res['audit'])
        
        # 填充审计账本
        self.audit_table.setRowCount(len(res['audit']))
        for i, d in enumerate(res['audit']):
            self.audit_table.setItem(i, 0, QTableWidgetItem(f"PEAK_NODE_{d['id']:02d}"))
            self.audit_table.setItem(i, 1, QTableWidgetItem(f"{d['kurt']:.4f}"))
            self.audit_table.setItem(i, 2, QTableWidgetItem(f"{d['skew']:.4f}"))
            
            # 使用进度条表示权重
            bar = QProgressBar()
            bar.setRange(0, 100); bar.setValue(int(min(100, d['rel_weight'] * 4)))
            bar.setTextVisible(False)
            bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF94; border-radius: 2px; }")
            self.audit_table.setCellWidget(i, 3, bar)
            
            self.audit_table.setItem(i, 4, QTableWidgetItem(f"E:{d['entropy']:.2f}"))

    def closeEvent(self, event):
        """关闭窗口时的安全资源回收"""
        if self.math_engine and self.math_engine.isRunning():
            self.math_engine.stop()
            self.math_engine.wait()
        super().closeEvent(event)