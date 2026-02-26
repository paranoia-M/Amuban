import sys
import time
import math
import random
import hashlib
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPointF, QRectF, QRect,
    QTimer, QSize, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, 
    QLinearGradient, QPainterPath, QFont, QPolygonF
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QTextEdit, QProgressBar, QGraphicsView, QGraphicsScene, 
    QGraphicsEllipseItem, QGraphicsObject, QStyleOptionGraphicsItem,
    QSlider, QAbstractItemView, QGraphicsLineItem
)

# 核心科学计算逻辑
from scipy.stats import kurtosis, skew
from scipy.fft import fft, fftfreq

# =============================================================================
# 1. 专利高阶量化引擎 (Advanced Logic Engine)
# =============================================================================

class QuantizationEngine(QThread):
    """
    实现专利核心公式: Pki = Gki * (Hki + Mki)
    深度生命周期管理版：支持安全打断与内存自清理
    """
    result_sig = pyqtSignal(dict)
    log_sig = pyqtSignal(str, str)

    def __init__(self, raw_isc, peaks_info, g_ki, radius, compensator=1.0):
        super().__init__()
        self.raw_isc = raw_isc
        self.peaks = peaks_info 
        self.g_ki = g_ki
        self.radius = radius
        self.compensator = compensator
        self._is_active = True

    def stop_logic(self):
        """线程内部循环的安全退出标志"""
        self._is_active = False

    def run(self):
        """核心计算流水线"""
        try:
            self.log_sig.emit("KERN", ">>> 启动专利特征向量解算引擎...")
            
            # 1. 计算 Mk,i (专利[0021]: 振荡幅值均值)
            raw_diffs = [p['amp_diff'] for p in self.peaks]
            m_ki = np.mean(raw_diffs) * self.compensator if raw_diffs else 0.0
            
            # 2. 频域主成分识别 (专利描述 [0084])
            n_pts = len(self.raw_isc)
            yf = fft(self.raw_isc)
            xf = fftfreq(n_pts, 1/1000000)
            abs_yf = np.abs(yf[:n_pts//2])
            dom_freq = abs(xf[np.argmax(abs_yf[1:]) + 1])

            # 3. 计算 Hk,i (专利[0022]: 邻域峰度累加)
            h_ki = 0.0
            feature_nodes = []
            
            for i, p in enumerate(self.peaks):
                if not self._is_active: return
                p_idx = p['peak_idx']
                
                # 专利定义的邻域窗口逻辑 [0009]
                win_start = max(0, p_idx - self.radius)
                win_end = min(len(self.raw_isc), p_idx + self.radius)
                
                seg_data = self.raw_isc[win_start:win_end]
                if len(seg_data) < 5: continue
                
                # 计算峰度 Hk,i 核心判据
                k_val = abs(kurtosis(seg_data))
                # 辅助偏度计算
                s_val = abs(skew(seg_data))
                
                h_ki += k_val
                
                # 计算算法摘要指纹
                f_hash = hashlib.md5(f"{p_idx}{k_val}".encode()).hexdigest()[:6].upper()
                
                # 【修复核心】：确保键名与 UI 渲染代码中的 'weight' 一致
                feature_nodes.append({
                    'id': i,
                    'pos': p_idx,
                    'kurt': k_val,
                    'skew': s_val,
                    'amp': p['peak_val'],
                    'hash': f_hash,
                    'weight': (k_val * p['peak_val']) / (m_ki + 0.1)
                })

            # 4. 执行专利终极判定公式 [0024]
            # Pki = Gki * (Hki + Mki)
            p_ki = self.g_ki * (h_ki + m_ki)
            
            # 体现计算深度的模拟延迟
            time.sleep(0.12)
            
            if not self._is_active: return
            
            self.log_sig.emit("MATH", f"解算完成: Pki={p_ki:.6f}")
            self.result_sig.emit({
                'p_ki': p_ki,
                'h_ki': h_ki,
                'm_ki': m_ki,
                'freq': dom_freq,
                'nodes': feature_nodes
            })
            
        except Exception as e:
            self.log_sig.emit("ERR", f"内核运行时异常: {str(e)}")

# =============================================================================
# 2. 交互组件：金属触感工业旋钮 (Precision Dial)
# =============================================================================

class IndustrialDial(QWidget):
    """
    具备旋转角度检测与状态反馈的深度自定义拨盘
    """
    valueChanged = pyqtSignal(float)

    def __init__(self, label="PARAM", min_v=0, max_v=100, init_v=50, color="#00A3FF"):
        super().__init__()
        self.setFixedSize(160, 180)
        self.value = init_v
        self.min_v = min_v
        self.max_v = max_v
        self.label = label
        self.theme_color = QColor(color)
        self._is_dragging = False

    def mousePressEvent(self, event):
        self._is_dragging = True
        self._update_from_mouse(event.pos())

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._update_from_mouse(event.pos())

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

    def _update_from_mouse(self, pos):
        dx = pos.x() - 80
        dy = 70 - pos.y()
        angle = math.degrees(math.atan2(dx, dy))
        angle = max(-135, min(135, angle))
        norm_val = (angle + 135) / 270.0
        self.value = self.min_v + norm_val * (self.max_v - self.min_v)
        self.valueChanged.emit(self.value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 底盘背景
        p.setPen(QPen(Qt.PenStyle.NoPen))
        p.setBrush(QColor(20, 22, 28))
        p.drawEllipse(20, 10, 120, 120)
        
        # 2. LED 进度弧
        p.setPen(QPen(self.theme_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        span_angle = ((self.value - self.min_v) / (self.max_v - self.min_v)) * -270
        p.drawArc(QRectF(28, 18, 104, 104), 225 * 16, int(span_angle * 16))
        
        # 3. 旋钮核心
        grad = QRadialGradient(80, 70, 45)
        grad.setColorAt(0, QColor(70, 75, 85)); grad.setColorAt(1, QColor(10, 12, 18))
        p.setBrush(grad)
        p.setPen(QPen(QColor(100, 100, 100, 150), 1))
        p.drawEllipse(40, 30, 80, 80)
        
        # 4. 指示位标
        p.save()
        p.translate(80, 70)
        p.rotate(((self.value - self.min_v) / (self.max_v - self.min_v)) * 270 - 135)
        p.setBrush(self.theme_color)
        p.setPen(QPen(Qt.PenStyle.NoPen)) 
        p.drawRoundedRect(QRectF(-4, -38, 8, 18), 2, 2)
        p.restore()
        
        # 5. 标签数值
        p.setPen(QColor(200, 200, 200))
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(QRectF(0, 140, 160, 40), Qt.AlignmentFlag.AlignCenter, f"{self.label}\n{self.value:.2f}")

# =============================================================================
# 3. 专利拓扑可视化：能量场 (Energy Field Canvas)
# =============================================================================

class EnergySpaceView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(8, 10, 14)))
        self.setMinimumHeight(450)

    def redraw_field(self, nodes):
        self.scene.clear()
        pen_grid = QPen(QColor(30, 35, 45), 1, Qt.PenStyle.DashLine)
        for i in range(-500, 501, 80): self.scene.addLine(i, -300, i, 300, pen_grid)
        
        no_pen = QPen(Qt.PenStyle.NoPen) 

        for n in nodes:
            x = (n['pos'] / 1024) * 850 - 425
            y = (math.sin(n['pos'] * 0.08) * 140)
            
            size = max(10, n['amp'] * 4.5)
            grad = QRadialGradient(x, y, size)
            grad.setColorAt(0, QColor(0, 255, 148, 220)); grad.setColorAt(1, QColor(0, 163, 255, 0))
            
            core = QGraphicsEllipseItem(x - size, y - size, size*2, size*2)
            core.setBrush(QBrush(grad)); core.setPen(no_pen)
            self.scene.addItem(core)
            
            for i in range(1, 4):
                rs = size + (i * 20)
                ring = QGraphicsEllipseItem(x - rs/2, y - rs/2, rs, rs)
                ring.setPen(QPen(QColor(0, 163, 255, int(150/i)), 2))
                self.scene.addItem(ring)
                
            txt = self.scene.addText(f"NODE:{n['hash']}", QFont("Consolas", 8))
            txt.setDefaultTextColor(QColor(150, 150, 150))
            txt.setPos(x + 10, y - 20)

# =============================================================================
# 4. 主控模块 (Quantization Page Controller)
# =============================================================================

class OscillationQuantPage(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = None
        
        # 防抖动定时器，防止高频触发导致崩溃
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._run_calculation_pipeline)
        
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)

        # HUD 动态看板
        self.hud = QFrame()
        self.hud.setFixedHeight(120)
        self.hud.setStyleSheet("background: #0D1117; border: 2px solid #00A3FF; border-radius: 15px;")
        hud_l = QHBoxLayout(self.hud)
        formula = QLabel("专利解算模型: P<sub>k,i</sub> = G<sub>k,i</sub> (Σ Hk,i + Mk,i )")
        formula.setStyleSheet("font-size: 22px; color: #888; font-family: 'Times New Roman'; padding-left: 20px;")
        self.pki_lbl = QLabel("Pki = 0.000000")
        self.pki_lbl.setStyleSheet("font-size: 38px; font-weight: bold; color: #00FF94; font-family: Consolas; padding-right: 30px;")
        hud_l.addWidget(formula); hud_l.addStretch(); hud_l.addWidget(self.pki_lbl)
        self.layout.addWidget(self.hud)

        mid_layout = QHBoxLayout()
        self.field_view = EnergySpaceView()
        mid_layout.addWidget(self.field_view, 8)
        
        # 控制塔
        tower = QGroupBox("算法管控控制台")
        tower.setFixedWidth(260)
        tower_l = QVBoxLayout(tower)
        self.dial_r = IndustrialDial("邻域半径(H)", 10, 250, 75, "#00A3FF")
        self.dial_g = IndustrialDial("突变增益(G)", 0.1, 15.0, 4.5, "#00FF94")
        self.dial_c = IndustrialDial("补偿系数(C)", 0.5, 3.0, 1.1, "#FF8C00")
        
        for d in [self.dial_r, self.dial_g, self.dial_c]:
            tower_l.addWidget(d, 0, Qt.AlignmentFlag.AlignHCenter)
            d.valueChanged.connect(lambda: self.debounce_timer.start(50))
            
        tower_l.addStretch()
        mid_layout.addWidget(tower)
        self.layout.addLayout(mid_layout)

        # 底部审计层
        bottom_area = QHBoxLayout()
        self.audit_table = QTableWidget(0, 5)
        self.audit_table.setHorizontalHeaderLabels(["特征簇", "算法摘要", "峰度值(H)", "幅值(M)", "能量权重"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.setStyleSheet("background: #090B0F; color: #BBB; border: 1px solid #333;")
        bottom_area.addWidget(self.audit_table, 7)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background: #05070A; color: #00FF94; font-family: Consolas; font-size: 11px;")
        bottom_area.addWidget(self.terminal, 3)
        self.layout.addLayout(bottom_area)

        QTimer.singleShot(1000, self._run_calculation_pipeline)

    def _run_calculation_pipeline(self):
        """同步生命周期，安全重启线程"""
        if self.engine:
            self.engine.result_sig.disconnect()
            self.engine.log_sig.disconnect()
            if self.engine.isRunning():
                self.engine.stop_logic()
                self.engine.quit()
                self.engine.wait() 
            self.engine.deleteLater()
            self.engine = None

        t = np.linspace(0, 10, 1024)
        raw_wave = 15 * np.exp(-0.35*t) + 6 * np.sin(2*np.pi*0.75*t) * np.exp(-0.2*t) + np.random.normal(0, 0.08, 1024)
        
        mock_peaks = []
        for i in range(5):
            px = 120 + i*170
            mock_peaks.append({'peak_idx': px, 'peak_val': 8.5 - (i*0.4), 'amp_diff': random.uniform(2.0, 5.5)})

        self.engine = QuantizationEngine(
            raw_wave, mock_peaks, 
            self.dial_g.value, int(self.dial_r.value), self.dial_c.value
        )
        self.engine.log_sig.connect(self._on_log_trace)
        self.engine.result_sig.connect(self._on_calculation_finished)
        self.engine.start()

    def _on_log_trace(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.terminal.append(f"<span style='color:#555'>[{ts}]</span> <b style='color:#00A3FF'>[{tag}]</b> {msg}")
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def _on_calculation_finished(self, res):
        """
        同步结果到 UI (修复了 KeyError: 'weight')
        """
        self.pki_lbl.setText(f"Pki = {res['p_ki']:.6f}")
        self.field_view.redraw_field(res['nodes'])
        
        self.audit_table.setRowCount(len(res['nodes']))
        for i, n in enumerate(res['nodes']):
            self.audit_table.setItem(i, 0, QTableWidgetItem(f"Peak_Set_{i:02d}"))
            self.audit_table.setItem(i, 1, QTableWidgetItem(n['hash']))
            self.audit_table.setItem(i, 2, QTableWidgetItem(f"{n['kurt']:.4f}"))
            self.audit_table.setItem(i, 3, QTableWidgetItem(f"{n['amp']:.2f} A"))
            
            # 使用正确同步的键名 'weight'
            bar = QProgressBar()
            bar.setRange(0, 100); bar.setValue(int(min(100, n['weight'] * 12)))
            bar.setTextVisible(False)
            bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF94; border-radius: 2px; }")
            self.audit_table.setCellWidget(i, 4, bar)

    def closeEvent(self, event):
        if self.engine and self.engine.isRunning():
            self.engine.stop_logic(); self.engine.quit(); self.engine.wait()
        super().closeEvent(event)