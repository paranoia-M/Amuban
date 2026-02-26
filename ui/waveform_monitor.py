import time
import random
import csv
import numpy as np
from datetime import datetime
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

# 核心算法库
from scipy.signal import find_peaks
from scipy import stats

# =============================================================================
# 1. 增强型数据流模拟引擎
# =============================================================================

class WaveformStreamer(QThread):
    """
    高频数据仿真引擎
    模拟专利中的 Isc 短路电流与 Vce 动态响应
    """
    data_packet_sig = pyqtSignal(dict)
    anomaly_sig = pyqtSignal(str, float)

    def __init__(self):
        super().__init__()
        self._active = True
        self.phase = 0.0

    def run(self):
        while self._active:
            # 生成 1024 点采样切片
            t = np.linspace(self.phase, self.phase + 0.001, 1024)
            
            # 模拟短路电流特征波形 (专利描述 [0084])
            # 基础指数衰减 + 5kHz 寄生振荡 + 15kHz 高频毛刺
            base = 30 * np.exp(-400 * t) 
            osc = 6 * np.sin(2 * np.pi * 6000 * t) * np.exp(-200 * t)
            noise = np.random.normal(0, 0.3, 1024)
            isc = base + osc + noise
            
            # 模拟 Vce 电压
            vce = 600 + 45 * np.sin(2 * np.pi * 6000 * t + 0.8) * np.exp(-350 * t)
            
            # 构建数据包
            packet = {
                't': t,
                'isc': isc,
                'vce': vce,
                'ts': datetime.now().strftime("%H:%M:%S.%f")[:-3]
            }

            # 专利逻辑：异常检测一阶导数突变
            if np.max(np.abs(np.diff(isc))) > 15.0:
                self.anomaly_sig.emit("关键路径信号畸变率超限", np.max(isc))

            self.data_packet_sig.emit(packet)
            self.phase += 0.001
            time.sleep(0.04) # 25Hz 刷新

    def stop(self):
        self._active = False

# =============================================================================
# 2. 交互式数字示波器组件
# =============================================================================

class InteractiveDSOCanvas(QWidget):
    """
    基于 QPainter 的高性能绘图组件
    支持双游标交互测量与专利特征点标注
    """
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(450)
        self.setMouseTracking(True)
        
        # 数据缓存
        self.isc = np.array([])
        self.vce = np.array([])
        self.peaks = []
        
        # 游标 A/B 位置 (点索引)
        self.cur_a = 150
        self.cur_b = 850
        self.drag_target = None

    def update_data(self, isc, vce):
        self.isc = isc
        self.vce = vce
        # 专利逻辑：特征峰位提取 [0009]
        p, _ = find_peaks(self.isc, height=5, distance=40)
        self.peaks = p
        self.update()

    def mousePressEvent(self, event):
        x = event.pos().x()
        w = self.width()
        pos_a = (self.cur_a / 1024) * w
        pos_b = (self.cur_b / 1024) * w
        
        if abs(x - pos_a) < 15: self.drag_target = 'A'
        elif abs(x - pos_b) < 15: self.drag_target = 'B'

    def mouseMoveEvent(self, event):
        if self.drag_target:
            idx = int((event.pos().x() / self.width()) * 1024)
            idx = max(0, min(1023, idx))
            if self.drag_target == 'A': self.cur_a = idx
            else: self.cur_b = idx
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        
        # 1. 工业背景与网格
        painter.fillRect(r, QColor(10, 12, 16))
        painter.setPen(QPen(QColor(35, 40, 48), 1, Qt.PenStyle.DotLine))
        dx, dy = r.width()/10, r.height()/8
        for i in range(1, 10): painter.drawLine(int(i*dx), 0, int(i*dx), r.height())
        for i in range(1, 8): painter.drawLine(0, int(i*dy), r.width(), int(i*dy))

        if self.isc.size == 0: return

        # 2. 绘制波形 (荧光绿)
        painter.setPen(QPen(QColor(0, 255, 148), 2))
        path = QPainterPath()
        sx = r.width() / 1024
        for i, val in enumerate(self.isc):
            px = i * sx
            py = r.height() - (val * 7) - 160
            if i == 0: path.moveTo(px, py)
            else: path.lineTo(px, py)
        painter.drawPath(path)

        # 3. 标注峰值特征点
        painter.setBrush(QColor(255, 60, 60))
        for p_idx in self.peaks:
            px = p_idx * sx
            py = r.height() - (self.isc[p_idx] * 7) - 160
            painter.drawEllipse(QPointF(px, py), 4, 4)

        # 4. 测量游标渲染
        painter.setPen(QPen(QColor(255, 200, 0), 1))
        ax, bx = self.cur_a * sx, self.cur_b * sx
        painter.drawLine(int(ax), 0, int(ax), r.height())
        painter.drawLine(int(bx), 0, int(bx), r.height())
        
        # 测量结果气泡 (专利参数测量演示)
        painter.setBrush(QColor(0, 80, 150, 180))
        painter.drawRect(int(ax), 20, 140, 45)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(int(ax)+8, 40, f"dt: {abs(self.cur_b-self.cur_a)} ns")
        painter.drawText(int(ax)+8, 58, f"dI: {abs(self.isc[self.cur_b]-self.isc[self.cur_a]):.2f} A")

# =============================================================================
# 3. 主监控看板
# =============================================================================

class WaveformMonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.streamer = WaveformStreamer()
        self.streamer.data_packet_sig.connect(self._on_data)
        self.streamer.anomaly_sig.connect(self._on_alarm)
        
        self.cached_packet = None
        self._init_ui()
        self.streamer.start()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(20)

        # --- 左侧：核心分析视图 ---
        self.left_col = QVBoxLayout()
        
        # A. DSO 示波器
        self.dso_box = QGroupBox("多通道同步特征监测仪表盘")
        self.dso_layout = QVBoxLayout(self.dso_box)
        self.canvas = InteractiveDSOCanvas()
        self.dso_layout.addWidget(self.canvas)
        self.left_col.addWidget(self.dso_box, 7)

        # B. 频域/统计分布视图 (专利[0093]逻辑)
        self.dist_box = QGroupBox("信号统计分布与频域分析")
        self.dist_layout = QHBoxLayout(self.dist_box)
        self.bars = []
        for _ in range(12):
            b = QProgressBar(); b.setOrientation(Qt.Orientation.Vertical)
            b.setFixedWidth(20); b.setTextVisible(False)
            b.setStyleSheet("QProgressBar::chunk { background: #722ED1; }")
            self.bars.append(b); self.dist_layout.addWidget(b)
        self.left_col.addWidget(self.dist_box, 3)

        self.main_layout.addLayout(self.left_col, 3)

        # --- 右侧：量化看板 ---
        self.right_container = QWidget()
        self.right_container.setFixedWidth(380)
        self.right_col = QVBoxLayout(self.right_container)
        self.right_col.setContentsMargins(0, 0, 0, 0)

        # 1. 物理看板
        self.stat_box = QGroupBox("专利核心物理指标量化")
        self.stat_layout = QFormLayout(self.stat_box)
        self.lbl_peak = self._create_lcd("0.00", "A")
        self.lbl_mk = self._create_lcd("0.000", "")
        self.lbl_skew = self._create_lcd("0.00", "")
        self.stat_layout.addRow("Isc 最大峰值:", self.lbl_peak)
        self.stat_layout.addRow("振荡差异 Mk,i:", self.lbl_mk)
        self.stat_layout.addRow("信号偏度 (Skew):", self.lbl_skew)
        self.right_col.addWidget(self.stat_box)

        # 2. 异常日志
        self.log_box = QGroupBox("系统事件实时追踪")
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("background: #090C10; color: #FF4D4D; font-family: Consolas;")
        log_l = QVBoxLayout(self.log_box); log_l.addWidget(self.log_list)
        self.right_col.addWidget(self.log_box)

        # 3. 增强型控制中心 (重点修改：按钮颜色与导出)
        self.ctrl_box = QGroupBox("显示与数据控制中心")
        ctrl_l = QVBoxLayout(self.ctrl_box)
        
        self.btn_freeze = QPushButton("❄ 冻结当前帧 (Freeze)")
        self.btn_freeze.setCheckable(True)
        self.btn_freeze.setFixedHeight(45)
        # 优化按钮样式：使用琥珀橙代表激活态
        self.btn_freeze.setStyleSheet("""
            QPushButton { background-color: #2D2D2D; border: 1px solid #444; border-radius: 4px; color: #AAA; }
            QPushButton:hover { background-color: #3D3D3D; }
            QPushButton:checked { background-color: #FF8C00; color: white; border: 1px solid #FFA500; font-weight: bold; }
        """)
        
        self.btn_export = QPushButton("📤 导出测试特征数据 (.csv)")
        self.btn_export.setFixedHeight(45)
        # 优化按钮样式：使用专业蓝
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #005A9E; border: none; border-radius: 4px; color: white; font-weight: bold; }
            QPushButton:hover { background-color: #0078D4; }
            QPushButton:pressed { background-color: #004578; }
        """)
        self.btn_export.clicked.connect(self._on_export)
        
        ctrl_l.addWidget(self.btn_freeze); ctrl_l.addWidget(self.btn_export)
        self.right_col.addWidget(self.ctrl_box)
        
        self.right_col.addStretch()
        self.main_layout.addWidget(self.right_container)

    def _create_lcd(self, val, unit):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        v = QLabel(val); v.setStyleSheet("font-size: 24px; color: #00FF94; font-family: Consolas; font-weight: bold;")
        u = QLabel(unit); u.setStyleSheet("color: #666;")
        l.addWidget(v); l.addWidget(u); w.v = v
        return w

    def _on_data(self, packet):
        if self.btn_freeze.isChecked(): return
        self.cached_packet = packet
        
        # 1. 更新绘图
        self.canvas.update_data(packet['isc'], packet['vce'])
        
        # 2. 计算专利逻辑：峰度与 Mk,i [0024]
        isc = packet['isc']
        self.lbl_peak.v.setText(f"{np.max(isc):.2f}")
        self.lbl_skew.v.setText(f"{stats.skew(isc):.2f}")
        
        p, _ = find_peaks(isc, height=5)
        if len(p) > 1:
            mk = np.std(isc[p])
            self.lbl_mk.v.setText(f"{mk:.3f}")
        
        # 3. 模拟频谱条更新
        for b in self.bars: b.setValue(random.randint(10, 95))

    def _on_alarm(self, msg, val):
        self.log_list.insertItem(0, f"[{datetime.now().strftime('%H:%M:%S')}] {msg} -> {val:.2f}A")
        if self.log_list.count() > 50: self.log_list.takeItem(50)

    def _on_export(self):
        """实现真实的 CSV 导出逻辑"""
        if not self.cached_packet:
            QMessageBox.warning(self, "导出失败", "当前无有效数据缓存。")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "导出特征数据", f"IGBT_Test_{int(time.time())}.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Index", "Timestamp", "Short_Circuit_Current(A)", "Collector_Voltage(V)"])
                    isc = self.cached_packet['isc']
                    vce = self.cached_packet['vce']
                    ts = self.cached_packet['ts']
                    for i in range(len(isc)):
                        writer.writerow([i, ts, f"{isc[i]:.4f}", f"{vce[i]:.4f}"])
                
                QMessageBox.information(self, "导出成功", f"数据已成功保存至:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "导出异常", f"文件写入失败: {str(e)}")

    def closeEvent(self, event):
        self.streamer.stop(); self.streamer.wait()
        super().closeEvent(event)