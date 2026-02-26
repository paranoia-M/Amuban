import time
import random
import numpy as np
from datetime import datetime
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

# =============================================================================
# 核心数据模型与模拟引擎
# =============================================================================

class HardwareControlEngine(QThread):
    """工业级硬件调度引擎：模拟专利中的多线程数据流"""
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, str)
    wave_sync = pyqtSignal(np.ndarray)

    def __init__(self, config_data):
        super().__init__()
        self.config = config_data
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        self.log_signal.emit("SYS", ">>> 初始化底层 VISA 堆栈...")
        time.sleep(1.0)
        
        # 获取批次任务列表 (模拟逻辑)
        batches = self.config.get('batches', [])
        if not batches:
            self.log_signal.emit("WARN", "无有效批次序列，执行单次预检采集")
            batches = [{"id": "PRE-01", "temp": "25"}]

        for idx, batch in enumerate(batches):
            if not self._is_running: break
            
            # 模拟温控与触发
            current_temp = batch.get('temp', '25')
            self.progress_signal.emit(int((idx/len(batches))*100), f"批次 {batch['id']}: {current_temp}℃")
            self.log_signal.emit("ENV", f"温控箱同步: 结温目标 {current_temp}℃")
            time.sleep(1.0)
            
            # 模拟波形生成
            x = np.linspace(0, 10, 250)
            wave = np.sin(x) * np.exp(-x/4) + np.random.normal(0, 0.02, 250)
            self.wave_sync.emit(wave)
            self.log_signal.emit("ACQ", f"批次 {batch['id']} 采集成功，数据已压入二级缓存")
            
        self.progress_signal.emit(100, "全序列任务就绪")
        self.log_signal.emit("SYS", ">>> 采集任务链路正常断开")

# =============================================================================
# 示波器显示组件
# =============================================================================

class ScopeCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.data = np.zeros(250)

    def update_wave(self, new_data):
        self.data = new_data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.fillRect(r, QColor(10, 12, 15))
        
        # 绘制专业栅格
        p.setPen(QPen(QColor(35, 40, 45), 1))
        for x in range(0, r.width(), 50): p.drawLine(x, 0, x, r.height())
        for y in range(0, r.height(), 40): p.drawLine(0, y, r.width(), y)
        
        # 绘制波形
        if len(self.data) < 2: return
        p.setPen(QPen(QColor(0, 255, 148), 2))
        path = QPainterPath()
        sx = r.width() / len(self.data)
        for i, v in enumerate(self.data):
            px = i * sx
            py = r.height()/2 - (v * r.height() * 0.4)
            if i == 0: path.moveTo(px, py)
            else: path.lineTo(px, py)
        p.drawPath(path)

# =============================================================================
# 主配置页面
# =============================================================================

class AcquisitionConfigPage(QWidget):
    """
    第一个菜单：设备采集配置 (全交互版)
    """
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- 左侧：配置面板 ---
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(620)
        self.left_panel.setStyleSheet("background: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        self.left_layout = QVBoxLayout(self.left_panel)

        header = QLabel("系统配置矩阵")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #00A3FF; border:none; padding: 5px;")
        self.left_layout.addWidget(header)

        # Tab 系统
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #151921; }
            QTabBar::tab { background: #1A1F26; color: #999; padding: 12px 20px; border: 1px solid #333; }
            QTabBar::tab:selected { background: #004578; color: white; border-bottom: 2px solid #00A3FF; }
            QComboBox QAbstractItemView { background-color: #1A1F26; color: white; selection-background-color: #004578; }
        """)
        
        self.tabs.addTab(self._ui_tab_physical(), "📡 物理链路")
        self.tabs.addTab(self._ui_tab_trigger(), "⏱ 触发逻辑")
        self.tabs.addTab(self._ui_tab_batch(), "⛓ 批次序列")
        self.tabs.addTab(self._ui_tab_dsp(), "⚙ 信号调理")
        
        self.left_layout.addWidget(self.tabs)
        self.left_layout.addStretch()

        # --- 右侧：显示与执行 ---
        self.right_panel = QVBoxLayout()
        
        # 1. 示波器
        scope_gb = self._create_section("实时特征波形预演")
        scope_l = QVBoxLayout(scope_gb)
        self.canvas = ScopeCanvas()
        scope_l.addWidget(self.canvas)
        self.right_panel.addWidget(scope_gb)

        # 2. 事务监控
        self.right_panel.addWidget(QLabel("底层通讯事务流:"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #05070A; color: #00FF94; font-family: 'Consolas'; font-size: 12px; border: 1px solid #222;")
        self.right_panel.addWidget(self.console)

        # 3. 进度与执行
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(12); self.pbar.setTextVisible(False)
        self.right_panel.addWidget(self.pbar)

        self.btn_run = QPushButton("⚡ 执行全链路初始化并启动采集任务")
        self.btn_run.setFixedHeight(55)
        self.btn_run.setStyleSheet("""
            QPushButton { background: #0078D4; color: white; font-weight: bold; font-size: 15px; border-radius: 4px; }
            QPushButton:hover { background: #0082CC; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.btn_run.clicked.connect(self._run_task)
        self.right_panel.addWidget(self.btn_run)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addLayout(self.right_panel)

    # --- 各个 Tab 页签内容实现 ---

    def _ui_tab_physical(self):
        w = QWidget(); l = QVBoxLayout(w)
        gb1 = QGroupBox("VISA 资源寻址与链路层")
        f1 = QFormLayout(gb1)
        self.cmb_visa = QComboBox()
        self.cmb_visa.addItems(["GPIB0::7::INSTR", "TCPIP::192.168.1.100", "USB0::X112"])
        f1.addRow("远程地址:", self.cmb_visa)
        l.addWidget(gb1)

        gb2 = QGroupBox("三元组信号物理调理配置")
        grid = QGridLayout(gb2)
        signals = ["短路电流 Isc", "饱和电压 Vce", "门极电流 Ige"]
        for i, sig in enumerate(signals):
            grid.addWidget(QLabel(sig), i, 0)
            c = QComboBox(); c.addItems(["CH1", "CH2", "CH3", "CH4"]); grid.addWidget(c, i, 1)
            imp = QComboBox(); imp.addItems(["1 MΩ", "50 Ω"]); grid.addWidget(imp, i, 2)
            sp = QDoubleSpinBox(); sp.setSuffix(" V/div"); sp.setValue(1.0); grid.addWidget(sp, i, 3)
        l.addWidget(gb2); l.addStretch(); return w

    def _ui_tab_trigger(self):
        w = QWidget(); l = QVBoxLayout(w)
        gb = QGroupBox("高级多级触发判定矩阵")
        f = QFormLayout(gb)
        
        # 修复点：添加选项
        self.cmb_trig_mode = QComboBox()
        self.cmb_trig_mode.addItems(["Edge (边沿触发)", "Pulse (脉冲宽度)", "Window (窗口触发)", "Timeout"])
        f.addRow("触发模式选择:", self.cmb_trig_mode)
        
        self.cmb_slope = QComboBox()
        self.cmb_slope.addItems(["Rising (上升沿)", "Falling (下降沿)", "Either (双向)"])
        f.addRow("判决斜率:", self.cmb_slope)
        
        self.cmb_trig_src = QComboBox()
        self.cmb_trig_src.addItems(["CH1 (Isc)", "CH2 (Vce)", "CH3 (Vge)", "EXT (外部模拟触发)"])
        f.addRow("触发主信号源:", self.cmb_trig_src)
        
        l.addWidget(gb); l.addStretch(); return w

    def _ui_tab_batch(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("自动化测试批次序列调度器"))
        
        # 批次任务表格
        self.batch_table = QTableWidget(3, 4)
        self.batch_table.setHorizontalHeaderLabels(["批次ID", "目标结温(℃)", "步进ΔT", "循环次数"])
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.batch_table.setStyleSheet("background: #0D1117; color: #EEE;")
        
        # 初始化默认数据
        default_data = [["B-001", "25", "10", "1"], ["B-002", "75", "10", "1"], ["B-003", "125", "10", "1"]]
        for r, row_data in enumerate(default_data):
            for c, val in enumerate(row_data):
                self.batch_table.setItem(r, c, QTableWidgetItem(val))
        
        l.addWidget(self.batch_table)
        
        # 修复点：实现按钮逻辑
        btn_box = QHBoxLayout()
        self.btn_add_step = QPushButton("+ 新增测试步")
        self.btn_add_step.clicked.connect(self._on_add_step)
        
        self.btn_remove_step = QPushButton("- 移除选中行")
        self.btn_remove_step.clicked.connect(self._on_remove_step)
        
        btn_box.addWidget(self.btn_add_step); btn_box.addWidget(self.btn_remove_step)
        l.addLayout(btn_box); return w

    def _ui_tab_dsp(self):
        w = QWidget(); l = QVBoxLayout(w)
        gb = QGroupBox("实时数字信号调理与滤波")
        f = QFormLayout(gb)
        
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["None (原始透传)", "Butterworth (巴特沃斯)", "Chebyshev (切比雪夫)", "FIR Moving Average"])
        f.addRow("滤波器算法类型:", self.cmb_filter)
        
        self.cmb_cutoff = QComboBox()
        self.cmb_cutoff.addItems(["500 KHz", "1 MHz", "5 MHz", "20 MHz (Full)"])
        f.addRow("硬件截止频率:", self.cmb_cutoff)
        
        l.addWidget(gb); l.addStretch(); return w

    # --- 交互逻辑实现 ---

    def _on_add_step(self):
        row = self.batch_table.rowCount()
        self.batch_table.insertRow(row)
        new_id = f"B-{row+1:03d}"
        self.batch_table.setItem(row, 0, QTableWidgetItem(new_id))
        self.batch_table.setItem(row, 1, QTableWidgetItem("25"))
        self.batch_table.setItem(row, 2, QTableWidgetItem("10"))
        self.batch_table.setItem(row, 3, QTableWidgetItem("1"))

    def _on_remove_step(self):
        current_row = self.batch_table.currentRow()
        if current_row >= 0:
            self.batch_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "操作提示", "请先在表格中点击选择一行任务。")

    def _run_task(self):
        self.btn_run.setEnabled(False)
        self.console.clear()
        
        # 收集表格中的任务数据
        batch_data = []
        for r in range(self.batch_table.rowCount()):
            batch_data.append({
                'id': self.batch_table.item(r, 0).text(),
                'temp': self.batch_table.item(r, 1).text()
            })
        
        config = {'batches': batch_data}
        self.worker = HardwareControlEngine(config)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.wave_sync.connect(self.canvas.update_wave)
        self.worker.finished.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()

    def _log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: #DDD;'>[{tag}]</b> {msg}")

    def _update_progress(self, val, status):
        self.pbar.setValue(val)
        self.btn_run.setText(f"正在执行: {status}...")

    def _create_section(self, title):
        gb = QGroupBox(title)
        gb.setStyleSheet("QGroupBox { border: 1px solid #333; margin-top: 10px; font-weight: bold; color: #00A3FF; padding: 10px; }")
        return gb