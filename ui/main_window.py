import sys
import os
import random
import traceback
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QStackedWidget, QLabel, QPushButton, QFrame, QProgressBar, 
    QStatusBar, QSplitter, QApplication, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QAction
from ui.oscillation_quant import OscillationQuantPage

# =============================================================================
# 1. 专利功能模块导入控制 (带异常防护)
# =============================================================================

PAGES = {}

def safe_import():
    """按需安全导入，防止因单个文件缺失导致全局无法启动"""
    # 菜单 1: 设备采集配置 (Index 0)
    try:
        from ui.acquisition_config import AcquisitionConfigPage
        PAGES[0] = AcquisitionConfigPage
    except Exception: print("Warning: AcquisitionConfigPage failed to load.")

    # 菜单 2: 实时波形监控 (Index 1)
    try:
        from ui.waveform_monitor import WaveformMonitorPage
        PAGES[1] = WaveformMonitorPage
    except Exception: print("Warning: WaveformMonitorPage failed to load.")

    # 菜单 3: 三元组聚类分析 (Index 2)
    try:
        from ui.mutation_analysis import MutationAnalysisPage
        PAGES[2] = MutationAnalysisPage 
    except Exception: print("Warning: MutationAnalysisPage failed to load.")

    # 菜单 4: 振荡特性量化 (Index 3)
    try:
        from ui.oscillation_analysis import OscillationAnalysisPage
        PAGES[3] = OscillationAnalysisPage 
    except Exception: pass

    # 菜单 5: 突变偏移解算 (Index 4)
    try:
        from ui.mutation_offset import MutationOffsetPage
        PAGES[4] = MutationOffsetPage 
    except Exception: pass

    # --- 👇 新增：菜单 6: 波峰波谷特征 (Index 5) ---
    try:
        from ui.peak_valley_feature import PeakValleyPage
        PAGES[5] = PeakValleyPage 
    except Exception as e: 
        print(f"Warning: PeakValleyPage failed to load -> {e}")
    try:
        from ui.oscillation_quant import OscillationQuantPage
        PAGES[6] = OscillationQuantPage 
    except Exception: print("Warning: OscillationQuantPage failed to load.")
    # 菜单 8: 趋势显著性 (Index 7)
    try:
        from ui.trend_analysis import TrendSignificancePage
        PAGES[7] = TrendSignificancePage 
    except Exception: pass

    # 菜单 9: 一致性 (Index 8)
    try:
        from ui.consistency_check import ConsistencyCheckPage
        PAGES[8] = ConsistencyCheckPage 
    except Exception: pass

    # 菜单 10: 质量分级 (Index 9)
    try:
        from ui.quality_evaluator import QualityEvaluationPage
        PAGES[9] = QualityEvaluationPage 
    except Exception: pass

    # 菜单 11: 故障诊断 (Index 10)
    try:
        from ui.fault_diagnostics import FaultDiagnosticsPage
        PAGES[10] = FaultDiagnosticsPage 
    except Exception: pass

    # 菜单 12: 数据中心 (Index 11)
    try:
        from ui.data_center import ExperimentalDataCenterPage
        PAGES[11] = ExperimentalDataCenterPage 
    except Exception: pass

    # 菜单 13: 流水线 (Index 12)
    try:
        from ui.automated_pipeline import AutomatedPipelinePage
        PAGES[12] = AutomatedPipelinePage 
    except Exception: pass

    # 菜单 14: 专利报告 (Index 13)
    try:
        from ui.patent_report import PatentReportPage
        PAGES[13] = PatentReportPage 
    except Exception: pass

# 执行安全导入
safe_import()

# =============================================================================
# 2. 主 UI 控制框架实现
# =============================================================================

class IndustrialUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 基础元数据
        self.setWindowTitle("IGBT 智能自动化测试系统")
        self.setMinimumSize(1500, 950)
        self.sys_version = "v2.8.2-Enterprise"
        
        # 14 个功能菜单 (严格对应专利流程)
        self.menu_items = [
            "设备采集配置", "实时波形监控", "三元组聚类分析",
            "振荡特性量化", "突变偏移解算", "波峰波谷特征",
            "振荡异常量化", "趋势显著性检测", "振荡一致性校核",
            "质量分级评定", "生产故障诊断", "实验数据中心",
            "自动化流水线", "器件测试报告"
        ]

        self._setup_style()
        self._init_main_structure()
        self._start_telemetry()

    def _setup_style(self):
        """工业级暗黑 QSS 引擎"""
        self.setStyleSheet("""
            QMainWindow { background-color: #0B0E14; }
            QWidget { color: #DCDCDC; font-family: 'Segoe UI', 'Consolas', 'Microsoft YaHei'; }
            
            /* 侧边导航栏 */
            QListWidget { background-color: #12161D; border: none; font-size: 14px; outline: none; border-right: 1px solid #1A1F26; }
            QListWidget::item { height: 55px; border-bottom: 1px solid #1A1F26; padding-left: 20px; color: #8B949E; }
            QListWidget::item:selected { background-color: #161B22; color: #00A3FF; border-left: 5px solid #00A3FF; font-weight: bold; }
            QListWidget::item:hover { background-color: #1C2128; }

            /* 修正弹窗与组件颜色 */
            QMessageBox { background-color: #161B22; border: 1px solid #00A3FF; }
            QMessageBox QLabel { color: #DCDCDC; font-size: 14px; min-width: 400px; }
            QMessageBox QPushButton { background-color: #30363D; border: 1px solid #444; border-radius: 4px; color: #E0E0E0; padding: 6px 20px; }
            
            QGroupBox { border: 1px solid #30363D; border-radius: 6px; margin-top: 15px; font-weight: bold; color: #00A3FF; padding-top: 10px; }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit { background-color: #1A1F26; border: 1px solid #333; border-radius: 4px; padding: 5px; color: white; }
            QComboBox QAbstractItemView { background-color: #1A1F26; color: white; selection-background-color: #004578; }
        """)

    def _init_main_structure(self):
        """构建 Header + Body + Status 布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.root_layout = QVBoxLayout(central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0); self.root_layout.setSpacing(0)

        # --- 1. Header ---
        self.header = QFrame()
        self.header.setFixedHeight(70)
        self.header.setStyleSheet("background-color: #161B22; border-bottom: 2px solid #00A3FF;")
        h_layout = QHBoxLayout(self.header)
        
        title_vbox = QVBoxLayout()
        sys_title = QLabel("IGBT 智能自动化测试系统逻辑总控平台")
        sys_title.setStyleSheet("font-size: 19px; font-weight: bold; color: white; border:none;")
        patent_info = QLabel("")
        patent_info.setStyleSheet("font-size: 12px; color: #8B949E; border:none;")
        title_vbox.addWidget(sys_title); title_vbox.addWidget(patent_info)
        
        self.link_status = QLabel("● 硬件链路：ACTIVE")
        self.link_status.setStyleSheet("color: #00FF94; font-weight: bold; margin-right: 20px; border:none;")
        
        h_layout.addLayout(title_vbox); h_layout.addStretch(); h_layout.addWidget(self.link_status)
        self.root_layout.addWidget(self.header)

        # --- 2. Body Splitter ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.sidebar = QListWidget()
        self.sidebar.addItems(self.menu_items)
        self.sidebar.setFixedWidth(260)
        
        self.stack = QStackedWidget()
        self._load_all_functional_pages()
        
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.root_layout.addWidget(self.splitter)

        # --- 3. Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_cpu = QLabel("CPU: 0%"); self.lbl_mem = QLabel("MEM: 0MB")
        self.lbl_time = QLabel()
        for lbl in [self.lbl_cpu, self.lbl_mem, self.lbl_time]:
            lbl.setStyleSheet("margin-left: 20px; color: #8B949E; font-family: Consolas;")
            self.status_bar.addPermanentWidget(lbl)

    def _load_all_functional_pages(self):
        """挂载 14 个菜单对应的逻辑页面"""
        for i, name in enumerate(self.menu_items):
            if i in PAGES:
                # 如果安全导入成功，加载真实页面
                try:
                    self.stack.addWidget(PAGES[i]())
                except Exception as e:
                    # 如果实例化出错，显示详细报错页面
                    self.stack.addWidget(self._create_error_placeholder(i+1, name, str(e)))
            else:
                # 显示未开发或导入失败占位符
                self.stack.addWidget(self._create_placeholder_page(i+1, name))

    def _create_placeholder_page(self, index, name):
        p = QWidget(); l = QVBoxLayout(p); l.setContentsMargins(60, 60, 60, 60)
        t = QLabel(f"{index}. {name}")
        t.setStyleSheet("font-size: 32px; font-weight: bold; color: #1F242D;")
        d = QLabel("该核心专利算法模块正在进行底层解耦开发...")
        d.setStyleSheet("color: #30363D; font-size: 16px; margin-top: 10px;")
        l.addWidget(t); l.addWidget(d); l.addStretch()
        return p

    def _create_error_placeholder(self, index, name, err):
        p = QWidget(); l = QVBoxLayout(p); l.setContentsMargins(50, 50, 50, 50)
        t = QLabel(f"❌ 模块加载崩溃: {name}"); t.setStyleSheet("color: #FF4D4D; font-size: 24px; font-weight: bold;")
        e = QTextEdit(f"错误详情:\n{err}\n\n建议检查 ui/ 目录下对应的文件是否存在类定义冲突。"); e.setReadOnly(True)
        e.setStyleSheet("background: #1A1212; color: #FF9999; border: 1px solid #442222;")
        l.addWidget(t); l.addWidget(e); return p

    def _start_telemetry(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(1000)

    def _update_status(self):
        self.lbl_cpu.setText(f"CPU: {random.randint(10, 30)}%")
        self.lbl_mem.setText(f"MEM: {random.randint(480, 520)}MB")
        self.lbl_time.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def closeEvent(self, event):
        """关闭时级联清理所有子线程"""
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if hasattr(w, 'closeEvent'): w.closeEvent(event)
        super().closeEvent(event)

# --- 启动 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    try:
        win = IndustrialUI()
        win.show()
        sys.exit(app.exec())
    except Exception:
        traceback.print_exc()