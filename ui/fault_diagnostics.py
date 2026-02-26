import sys
import time
import math
import random
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

# =============================================================================
# 1. 专利核心故障诊断引擎 (Expert Diagnostic System)
# =============================================================================

class DiagnosticExpertEngine(QThread):
    """
    基于专利[0035] 与 [0083] 的生产故障诊断专家系统
    将数学系数映射到物理故障模式 (如键合线脱落、焊料疲劳)
    """
    scan_tick = pyqtSignal(float)          # 扫描仪 X 坐标进度
    chip_diagnosed = pyqtSignal(int, dict) # 某个芯片诊断出结果
    log_sig = pyqtSignal(str, str)
    finished_sig = pyqtSignal(dict)

    def __init__(self, chip_count, threshold):
        super().__init__()
        self.chip_count = chip_count
        self.threshold = threshold # 专利[0121] 归一化判断阈值
        self._abort = False

    def run(self):
        self.log_sig.emit("SYS", ">>> 启动激光无损探伤与数字孪生诊断序列...")
        time.sleep(0.5)
        
        results = {}
        # 模拟激光扫描线从左到右 (X: 0 -> 1000)
        for x_pos in range(0, 1000, 15):
            if self._abort: return
            self.scan_tick.emit(x_pos)
            
            # 当扫描线经过特定区域时，触发芯片诊断 (模拟空间映射)
            chip_idx = int((x_pos / 1000) * self.chip_count)
            if chip_idx not in results and chip_idx < self.chip_count:
                # 生成专利算法系数
                w_norm = random.uniform(0.5, 1.0)
                p_ki = random.uniform(0.1, 5.0)
                
                # 专利[0035]: Wi < 阈值 -> 生产故障
                is_faulty = w_norm < self.threshold
                fault_type = "正常 (Normal)"
                if is_faulty:
                    # 专利[0083]: 键合线不良导致短路电流严重振荡 (P_ki 激增)
                    if p_ki > 3.5: fault_type = "严重故障: 键合线脱落 (Bond Wire Liftoff)"
                    elif p_ki > 2.0: fault_type = "一般故障: DBC 焊料层疲劳 (Solder Fatigue)"
                    else: fault_type = "轻微故障: 栅极氧化层退化 (Gate Oxide Degradation)"
                
                report = {
                    'w_norm': w_norm,
                    'p_ki': p_ki,
                    'is_faulty': is_faulty,
                    'fault_type': fault_type
                }
                results[chip_idx] = report
                self.chip_diagnosed.emit(chip_idx, report)
                
                if is_faulty:
                    self.log_sig.emit("ALARM", f"区域 CHIP_{chip_idx:02d} 触发熔断阈值! 判定: {fault_type}")
                else:
                    self.log_sig.emit("PASS", f"区域 CHIP_{chip_idx:02d} Wi={w_norm:.2f} > 阈值, 状态健康。")

            time.sleep(0.04) # 扫描仪移动动画延迟
            
        self.scan_tick.emit(1000)
        self.log_sig.emit("SYS", ">>> 全局数字孪生扫描完成。")
        self.finished_sig.emit(results)

# =============================================================================
# 2. 物理蓝图图元系统 (QGraphicsItems for Digital Twin)
# =============================================================================

class ChipItem(QGraphicsObject):
    """表示 IGBT 模块内部的物理裸体晶圆 (Die)"""
    hover_sig = pyqtSignal(int, dict)
    
    def __init__(self, chip_id, x, y, width, height):
        super().__init__()
        self.chip_id = chip_id
        self.rect = QRectF(x, y, width, height)
        self.setAcceptHoverEvents(True)
        
        self.state = "IDLE" # IDLE, SCANNING, PASS, FAIL
        self.report = None
        
        # 呼吸灯动画效果
        self.pulse_alpha = 0
        self.pulse_dir = 1
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate_pulse)

    def boundingRect(self):
        return self.rect.adjusted(-5, -5, 5, 5)

    def set_diagnosed(self, report):
        self.report = report
        self.state = "FAIL" if report['is_faulty'] else "PASS"
        if self.state == "FAIL":
            self.anim_timer.start(50) # 故障红灯急促闪烁
        else:
            self.anim_timer.stop()
            self.pulse_alpha = 0
        self.update()

    def _animate_pulse(self):
        self.pulse_alpha += 15 * self.pulse_dir
        if self.pulse_alpha >= 200: self.pulse_dir = -1
        elif self.pulse_alpha <= 50: self.pulse_dir = 1
        self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 基础硅片金属质感
        grad = QLinearGradient(self.rect.topLeft(), self.rect.bottomRight())
        if self.state == "IDLE":
            grad.setColorAt(0, QColor(80, 90, 100)); grad.setColorAt(1, QColor(40, 50, 60))
            border = QColor(100, 110, 120)
        elif self.state == "PASS":
            grad.setColorAt(0, QColor(0, 150, 80)); grad.setColorAt(1, QColor(0, 80, 40))
            border = QColor(0, 255, 148)
        elif self.state == "FAIL":
            grad.setColorAt(0, QColor(200, 40, 40, self.pulse_alpha)); grad.setColorAt(1, QColor(100, 10, 10, self.pulse_alpha))
            border = QColor(255, 50, 50)

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(border, 2))
        painter.drawRoundedRect(self.rect, 3, 3)
        
        # 晶圆内部微小极板网格 (增加科幻细节)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        for i in range(1, 4):
            painter.drawLine(int(self.rect.left()), int(self.rect.top() + i*self.rect.height()/4),
                             int(self.rect.right()), int(self.rect.top() + i*self.rect.height()/4))
            
        # ID 标识
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(self.rect, Qt.AlignmentFlag.AlignCenter, f"C-{self.chip_id:02d}")

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 【修复点】：PyQt6 严格类型检查。如果 report 还是 None (没扫描过)，则发送空字典 {}
        safe_report = self.report if self.report is not None else {}
        self.hover_sig.emit(self.chip_id, safe_report)
        super().hoverEnterEvent(event)

class BondWireItem(QGraphicsItem):
    """表示 IGBT 模块内部的铝键合线 (Bond Wire)"""
    def __init__(self, start_pos, end_pos):
        super().__init__()
        self.start_p = start_pos
        self.end_p = end_pos
        self.setZValue(1) # 位于芯片上方

    def boundingRect(self):
        return QRectF(self.start_p, self.end_p).normalized().adjusted(-10, -10, 10, 10)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(180, 190, 200, 150), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        
        # 使用二次贝塞尔曲线模拟弧形的键合线
        path = QPainterPath()
        path.moveTo(self.start_p)
        ctrl_x = (self.start_p.x() + self.end_p.x()) / 2
        ctrl_y = min(self.start_p.y(), self.end_p.y()) - 30 # 向上凸起
        path.quadTo(QPointF(ctrl_x, ctrl_y), self.end_p)
        painter.drawPath(path)

# =============================================================================
# 3. 数字孪生画布 (Digital Twin Blueprint Canvas)
# =============================================================================

class DigitalTwinCanvas(QGraphicsView):
    """全屏互动蓝图画布，彻底打破传统左右分栏"""
    chip_hovered = pyqtSignal(int, dict)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 极客风格：网格图纸背景
        self.setBackgroundBrush(QBrush(QColor(8, 12, 16)))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.chips =[]
        self._build_physical_module()
        
        # 激光扫描线图元
        self.scan_line = QGraphicsLineItem()
        self.scan_line.setPen(QPen(QColor(0, 163, 255, 200), 4))
        self.scan_line.setZValue(10)
        self.scan_line.hide()
        self.scene.addItem(self.scan_line)

    def drawBackground(self, painter, rect):
        """覆盖重写，绘制全屏工程图纸网格"""
        super().drawBackground(painter, rect)
        painter.setPen(QPen(QColor(20, 30, 40), 1))
        grid_size = 40
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        for x in range(left, int(rect.right()), grid_size):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), grid_size):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    def _build_physical_module(self):
        """通过代码构建一个高度拟真的 2D IGBT 功率模块内部结构"""
        # 绘制底部铜基板 (Baseplate)
        base = QGraphicsRectItem(0, 0, 1000, 500)
        base.setBrush(QBrush(QColor(40, 30, 20)))
        base.setPen(QPen(QColor(150, 100, 50), 3))
        self.scene.addItem(base)
        
        # 建立 3 个 DBC 陶瓷基板
        chip_id = 0
        for i in range(3):
            dbc_x = 50 + i * 320
            dbc_y = 50
            dbc = QGraphicsRectItem(dbc_x, dbc_y, 260, 400)
            dbc.setBrush(QBrush(QColor(60, 70, 80)))
            dbc.setPen(QPen(QColor(100, 120, 140), 2))
            self.scene.addItem(dbc)
            
            # 每个 DBC 上放置 4 个 IGBT 裸片 (Chips)
            for r in range(2):
                for c in range(2):
                    cx = dbc_x + 30 + c * 120
                    cy = dbc_y + 60 + r * 160
                    chip = ChipItem(chip_id, cx, cy, 80, 100)
                    chip.hover_sig.connect(self.chip_hovered.emit)
                    self.scene.addItem(chip)
                    self.chips.append(chip)
                    
                    # 绘制键合线连接到旁边的虚拟汇流排
                    wire = BondWireItem(QPointF(cx+40, cy+50), QPointF(dbc_x+130, dbc_y+10))
                    self.scene.addItem(wire)
                    chip_id += 1

        self.setSceneRect(-100, -100, 1200, 700)

    def update_scan_line(self, x_pos):
        self.scan_line.show()
        # 画布总宽1000，映射坐标
        self.scan_line.setLine(x_pos, -50, x_pos, 550)

    def hide_scan_line(self):
        self.scan_line.hide()

    def update_chip_state(self, chip_id, report):
        if chip_id < len(self.chips):
            self.chips[chip_id].set_diagnosed(report)

# =============================================================================
# 4. 悬浮式透明 HUD 面板 (Floating HUD Overlays)
# =============================================================================

class FloatingPanel(QFrame):
    """科幻风半透明悬浮面板基类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 20, 25, 220);
                border: 1px solid #00A3FF;
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; }
        """)
        # 允许面板在画面上接收事件
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

# =============================================================================
# 5. 主控页面：彻底抛弃传统布局 (Production Fault Diagnostics Page)
# =============================================================================

class FaultDiagnosticsPage(QWidget):
    """
    第 11 个菜单：生产故障诊断
    颠覆性设计：没有左右分栏，全局为一张基于 QGraphicsView 的数字孪生画布。
    控制台、信息板作为半透明的 FloatingPanel 悬浮其上。
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self._init_ui()

    def _init_ui(self):
        # 1. 根布局：没有任何边距，让画布填满整个视口
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        
        # 2. 铺设底层数字孪生画布
        self.canvas = DigitalTwinCanvas()
        self.canvas.chip_hovered.connect(self._on_chip_hovered)
        self.main_layout.addWidget(self.canvas)
        
        # 3. 悬浮面板 A：左上角控制中枢 (Command Center)
        self.hud_ctrl = FloatingPanel(self.canvas)
        self.hud_ctrl.setFixedSize(350, 180)
        ctrl_l = QVBoxLayout(self.hud_ctrl)
        
        title = QLabel("生产故障诊断中枢")
        title.setStyleSheet("color: #00A3FF; font-size: 16px; font-weight: bold;")
        ctrl_l.addWidget(title)
        
        form_l = QFormLayout()
        self.dsp_th = QDoubleSpinBox(); self.sp_chip = QSpinBox()
        self.dsp_th.setRange(0.1, 1.0); self.dsp_th.setValue(0.75); self.dsp_th.setSingleStep(0.05)
        self.sp_chip.setRange(1, 12); self.sp_chip.setValue(12)
        # 修复悬浮面板内部输入框的暗色样式
        input_style = "background: #0A0A0A; border: 1px solid #333; color: white;"
        self.dsp_th.setStyleSheet(input_style); self.sp_chip.setStyleSheet(input_style)
        
        form_l.addRow(QLabel("Wi 故障熔断阈值:"), self.dsp_th)
        form_l.addRow(QLabel("激活晶圆探测区:"), self.sp_chip)
        ctrl_l.addLayout(form_l)
        
        self.btn_scan = QPushButton("⚡ 发射激光扫描执行诊断")
        self.btn_scan.setFixedHeight(45)
        self.btn_scan.setStyleSheet("""
            QPushButton { background: rgba(0, 163, 255, 180); color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background: rgba(0, 200, 255, 220); border: 1px solid white; }
        """)
        self.btn_scan.clicked.connect(self._start_scan)
        ctrl_l.addWidget(self.btn_scan)

        # 4. 悬浮面板 B：右上角个体溯源报告 (Detail Inspector)
        self.hud_detail = FloatingPanel(self.canvas)
        self.hud_detail.setFixedSize(300, 220)
        det_l = QVBoxLayout(self.hud_detail)
        
        self.lbl_det_title = QLabel("微观探针就绪 (Hover to Inspect)")
        self.lbl_det_title.setStyleSheet("color: #00FF94; font-weight: bold; font-size: 14px;")
        det_l.addWidget(self.lbl_det_title)
        
        self.lbl_det_w = QLabel("Wi (质量系数): --")
        self.lbl_det_p = QLabel("Pki (异常系数): --")
        self.lbl_det_status = QLabel("诊断结论: --")
        self.lbl_det_status.setWordWrap(True)
        
        for lbl in[self.lbl_det_w, self.lbl_det_p, self.lbl_det_status]:
            lbl.setStyleSheet("color: #DCDCDC; font-family: Arial; font-size: 12px; margin-top: 5px;")
            det_l.addWidget(lbl)
        det_l.addStretch()

        # 5. 悬浮面板 C：底部宽屏审计终端 (Terminal Overlay)
        self.hud_term = FloatingPanel(self.canvas)
        self.hud_term.setFixedHeight(150)
        term_l = QVBoxLayout(self.hud_term)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: transparent; color: #00FF94; font-family: Arial; border: none;")
        term_l.addWidget(QLabel("<b style='color:#00A3FF'>[SYSTEM TRACE]</b> 专利探伤算法事务流:"))
        term_l.addWidget(self.console)

    def resizeEvent(self, event):
        """确保在窗口缩放时，悬浮面板始终吸附在画面的各个角落"""
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        
        # 左上角控制台 (边距 20)
        self.hud_ctrl.move(20, 20)
        # 右上角检查面板 (边距 20)
        self.hud_detail.move(w - self.hud_detail.width() - 20, 20)
        # 底部居中终端
        self.hud_term.setFixedWidth(w - 40)
        self.hud_term.move(20, h - self.hud_term.height() - 20)

    # --- 核心交互联动 ---

    def _start_scan(self):
        self.btn_scan.setEnabled(False)
        self.console.clear()
        
        # 重置所有芯片状态
        for chip in self.canvas.chips:
            chip.state = "IDLE"
            chip.update()
            
        self.engine = DiagnosticExpertEngine(self.sp_chip.value(), self.dsp_th.value())
        self.engine.log_sig.connect(self._log)
        self.engine.scan_tick.connect(self.canvas.update_scan_line)
        self.engine.chip_diagnosed.connect(self.canvas.update_chip_state)
        self.engine.finished_sig.connect(self._on_scan_finished)
        self.engine.start()

    def _on_scan_finished(self, results):
        self.btn_scan.setEnabled(True)
        self.canvas.hide_scan_line()
        
        fail_cnt = sum(1 for r in results.values() if r['is_faulty'])
        self._log("SYS", f"探伤报告生成完毕。共计检出 {fail_cnt} 个致命异常节点。")

    def _on_chip_hovered(self, chip_id, report):
        """当鼠标悬停在物理晶圆上时，右上角面板展示专利映射细节"""
        self.lbl_det_title.setText(f"微观探针目标: 晶圆 [C-{chip_id:02d}]")
        
        # 【修复点响应处】：判断是否是空字典 {}
        if not report:
            self.lbl_det_w.setText("Wi (质量系数): 未扫描")
            self.lbl_det_p.setText("Pki (异常系数): 未扫描")
            self.lbl_det_status.setText("诊断结论: 数据待采集")
            self.lbl_det_status.setStyleSheet("color: #888;")
            return
            
        self.lbl_det_w.setText(f"Wi (归一化质量): {report['w_norm']:.4f}")
        self.lbl_det_p.setText(f"Pki (振荡异常): {report['p_ki']:.4f}")
        
        if report['is_faulty']:
            self.lbl_det_status.setText(f"结论: {report['fault_type']}")
            self.lbl_det_status.setStyleSheet("color: #FF4D4D; font-weight: bold;")
        else:
            self.lbl_det_status.setText(f"结论: 生产正常 (Pass)")
            self.lbl_det_status.setStyleSheet("color: #00FF94; font-weight: bold;")

    def _log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00FF94" if tag in ["SYS", "PASS"] else "#FF4D4D"
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: {color};'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())