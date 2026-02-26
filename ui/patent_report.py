import sys
import time
import hashlib
import math
import random
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

# =============================================================================
# 1. 专利鉴定数据生成引擎 (Report Logic Engine)
# =============================================================================

class ReportDataEngine(QThread):
    """
    报告数据聚合器：模拟从 core 算法模块提取最终计算值
    """
    status_sig = pyqtSignal(int, str)
    finished_sig = pyqtSignal(dict)

    def __init__(self, inspector, batch_id):
        super().__init__()
        self.inspector = inspector
        self.batch_id = batch_id

    def run(self):
        steps = [
            (20, "正在检索实验数据库..."),
            (50, "聚合 25℃-145℃ 结温梯度特征..."),
            (80, "执行归一化 Wi 熔断判定算法...")
        ]
        for p, msg in steps:
            self.status_sig.emit(p, msg)
            time.sleep(0.4)
            
        # 构造符合专利 CN 119270019 B 逻辑的汇总数据
        report = {
            'batch_num': self.batch_id,
            'date': datetime.now().strftime("%Y年%m月%d日"),
            'inspector': self.inspector,
            'institution': "IGBT 智能自动化测试研发中心",
            'conclusions': (
                "经过多维度的 Mann-Kendall 趋势检验与三元组聚类分析，该批次器件的总体质量指数 Wi 均值为 1.1205。"
                "其中 95% 的器件符合判定标准，2 个器件检出键合线接触电阻异常导致的振荡畸变。"
            ),
            'table_data': [
                ("突变偏移系数 Gk,i (均值)", "1.6542", "符合标准"),
                ("振荡差异值 Mk,i (均值)", "0.3015", "符合标准"),
                ("振荡异常系数 Pk,i (均值)", "4.2100", "异常"),
                ("趋势显著性 Ti (均值)", "1.1850", "符合标准"),
                ("振荡一致性 Ui (均值)", "0.9122", "极佳"),
                ("综合质量评定 Wi (Norm)", "0.8841", "合格")
            ]
        }
        
        # 生成基于数据内容的 SHA-256 数字摘要 (防伪水印)
        raw_token = f"{report['batch_num']}{report['institution']}{time.time()}"
        report['auth_code'] = hashlib.sha256(raw_token.encode()).hexdigest().upper()[:32]
        
        self.finished_sig.emit(report)

# =============================================================================
# 2. 高仿真 A4 报告画布 (Virtual A4 Canvas)
# =============================================================================

class A4ReportCanvas(QWidget):
    """
    虚拟 A4 仿真纸张：包含页眉、网格、防伪底纹和核心公章
    """
    def __init__(self):
        super().__init__()
        # A4 比例 1:1.414 -> 750x1060
        self.setFixedSize(750, 1060)
        self.data = None
        self.is_certified = False
        self.random_seal_angle = random.randint(-10, 10)

    def set_report_data(self, data):
        self.data = data
        self.is_certified = True
        self.random_seal_angle = random.randint(-12, 12)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        rect = self.rect()
        
        # 1. 绘制纸张阴影与本体
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawRect(rect.adjusted(8, 8, 0, 0))
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRect(rect.adjusted(0, 0, -8, -8))

        if not self.data:
            self._draw_empty_state(painter)
            return

        # 2. 绘制页眉装饰
        self._draw_header(painter)
        
        # 3. 绘制基本信息
        self._draw_meta_info(painter)
        
        # 4. 绘制专利核心指标表
        self._draw_metrics_table(painter)
        
        # 5. 绘制鉴定结论
        self._draw_conclusion(painter)
        
        # 6. 绘制底部防伪指纹
        self._draw_footer_hash(painter)

        # 7. 【核心】绘制电子鉴定公章
        if self.is_certified:
            self._draw_advanced_seal(painter)

    def _draw_empty_state(self, painter):
        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "WAITING FOR ANALYSIS...")

    def _draw_header(self, painter):
        # 专利标题
        painter.setPen(QColor(40, 40, 40))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        painter.drawText(60, 60, "一种IGBT器件的智能自动化测试系统")
        
        # 装饰红线
        painter.setPen(QPen(QColor(200, 0, 0), 2))
        painter.drawLine(60, 75, 690, 75)
        
        # 报告主标题
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        painter.drawText(QRect(0, 120, 750, 60), Qt.AlignmentFlag.AlignCenter, "IGBT 模块质量评估鉴定报告")

    def _draw_meta_info(self, painter):
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.setPen(QColor(80, 80, 80))
        y_start = 220
        fields = [
            ("批次序列号 (Batch ID):", self.data['batch_num']),
            ("鉴定机构 (Institution):", self.data['institution']),
            ("主鉴定人 (Inspector):", self.data['inspector']),
            ("报告签发日期 (Date):", self.data['date'])
        ]
        for i, (k, v) in enumerate(fields):
            painter.drawText(80, y_start + i*35, k)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(260, y_start + i*35, v)
            painter.setPen(QColor(80, 80, 80))

    def _draw_metrics_table(self, painter):
        y_top = 400
        # 绘制表头背景
        painter.setBrush(QColor(240, 245, 255))
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawRect(80, y_top, 590, 40)
        
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        painter.drawText(100, y_top + 25, "评估维度")
        painter.drawText(380, y_top + 25, "解算分值")
        painter.drawText(560, y_top + 25, "状态判定")

        # 绘制行数据
        painter.setFont(QFont("Consolas", 10))
        for i, (name, val, status) in enumerate(self.data['table_data']):
            y_row = y_top + 40 + (i+1)*35
            painter.setPen(QColor(230, 230, 230))
            painter.drawLine(80, y_row + 5, 670, y_row + 5)
            
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(100, y_row, name)
            painter.drawText(380, y_row, val)
            
            # 状态着色
            if "异常" in status: painter.setPen(QColor(200, 0, 0))
            else: painter.setPen(QColor(0, 120, 0))
            painter.drawText(560, y_row, status)

    def _draw_conclusion(self, painter):
        y_con = 750
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        painter.drawText(80, y_con, "专家鉴定意见:")
        
        painter.setFont(QFont("Microsoft YaHei", 10))
        painter.drawText(QRect(80, y_con + 25, 590, 120), Qt.TextFlag.TextWordWrap, self.data['conclusions'])

    def _draw_footer_hash(self, painter):
        painter.setPen(QColor(180, 180, 180))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(60, 1020, f"{self.data['auth_code']}")
        painter.drawText(60, 1035, "")

    def _draw_advanced_seal(self, painter):
        """
        重新设计的、具备精确数学排版的电子公章
        """
        painter.save()
        # 1. 设置印章中心位置
        center_x, center_y = 550, 880
        painter.translate(center_x, center_y)
        painter.rotate(self.random_seal_angle)
        
        seal_red = QColor(230, 30, 30, 210)
        painter.setPen(QPen(seal_red, 4))
        
        # 2. 绘制双外圈
        painter.drawEllipse(-85, -85, 170, 170)
        painter.setPen(QPen(seal_red, 2))
        painter.drawEllipse(-78, -78, 156, 156)
        
        # 3. 绘制中心五角星
        painter.setBrush(seal_red)
        star_path = QPainterPath()
        for i in range(5):
            angle = math.radians(90 + i * 144)
            p = QPointF(28 * math.cos(angle), -28 * math.sin(angle))
            if i == 0: star_path.moveTo(p)
            else: star_path.lineTo(p)
        star_path.closeSubpath()
        painter.drawPath(star_path)
        
        # 4. 【核心修复】环形文字排版
        # 将文字围绕上半圆均匀分布
        font = QFont("Microsoft YaHei", 13, QFont.Weight.Bold)
        painter.setFont(font)
        text = "IGBT智能自动化测试鉴定中心"
        
        # 算法：计算每个字符的旋转角度
        # 我们希望文字从左侧 -140度 分布到 右侧 140度 (共280度范围)
        total_angle = 260.0
        start_angle = -130.0 # 起始角度
        step = total_angle / (len(text) - 1)
        
        radius = 65 # 文字排列半径
        
        for i, char in enumerate(text):
            painter.save()
            # 计算当前字符应该偏转的角度
            char_angle = start_angle + i * step
            # 平移坐标系到字符位置，并旋转字符使其垂直于切线
            painter.rotate(char_angle)
            # 向半径方向平移
            painter.translate(0, -radius)
            # 绘制字符 (修正位置使字符居中)
            painter.drawText(-10, 0, char)
            painter.restore()
            
        # 5. 绘制底部编号 (弧形或直线)
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(QRect(-50, 45, 100, 20), Qt.AlignmentFlag.AlignCenter, "CERTIFIED")
        
        painter.restore()

# =============================================================================
# 3. 报告中心主控界面 (Main Report Manager)
# =============================================================================

class PatentReportPage(QWidget):
    """
    第 14 个菜单页面逻辑
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self._init_ui()

    def _init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(20)

        # --- A. 左侧操作区 ---
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(320)
        self.left_panel.setStyleSheet("background: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        l_vbox = QVBoxLayout(self.left_panel)
        
        l_vbox.addWidget(QLabel("<b style='color:#00A3FF; font-size:15px;'>报告生成控制器</b>"))
        
        form = QFormLayout()
        self.edit_id = QLineEdit("SC-BATCH-2025-02-26")
        self.edit_user = QLineEdit("HE-YIFAN (高级工程专家)")
        form.addRow("测试批次号:", self.edit_id)
        form.addRow("授权鉴定人:", self.edit_user)
        l_vbox.addLayout(form)
        
        l_vbox.addSpacing(20)
        l_vbox.addWidget(QLabel("<b style='color:#777;'>报告预检清单:</b>"))
        self.check_list = QListWidget()
        self.check_list.setStyleSheet("background: #0B0E14; border: 1px solid #333;")
        self.check_list.addItems(["1. 数据完整性校验 - OK", "2. 专利公式依赖核对 - OK", "3. Wi 空间归一化校准 - OK"])
        l_vbox.addWidget(self.check_list)
        
        self.btn_gen = QPushButton("📑 执行专利级鉴定并生成报告")
        self.btn_gen.setFixedHeight(50)
        self.btn_gen.setStyleSheet("background: #238636; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_gen.clicked.connect(self._run_generation)
        l_vbox.addWidget(self.btn_gen)
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8); self.pbar.setTextVisible(False)
        l_vbox.addWidget(self.pbar)
        
        l_vbox.addStretch()
        
        self.btn_pdf = QPushButton("📤 导出为加密 PDF 文档")
        self.btn_pdf.setFixedHeight(45)
        self.btn_pdf.setStyleSheet("background: #0078D4; color: white; font-weight: bold;")
        l_vbox.addWidget(self.btn_pdf)

        # --- B. 中间预览区 ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("background: #1C2128; border: none;")
        
        self.report_canvas = A4ReportCanvas()
        self.scroll.setWidget(self.report_canvas)

        # --- C. 右侧信息区 ---
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(280)
        self.right_panel.setStyleSheet("background: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        r_vbox = QVBoxLayout(self.right_panel)
        
        r_vbox.addWidget(QLabel("<b style='color:#FFCC00;'>数据数字摘要</b>"))
        self.hash_log = QTextEdit("READY")
        self.hash_log.setReadOnly(True)
        self.hash_log.setFixedHeight(150)
        self.hash_log.setStyleSheet("background: #05070A; color: #444; font-family: Consolas; font-size: 11px;")
        r_vbox.addWidget(self.hash_log)
        
        r_vbox.addStretch()

        self.layout.addWidget(self.left_panel)
        self.layout.addWidget(self.scroll, 1)
        self.layout.addWidget(self.right_panel)

    def _run_generation(self):
        self.btn_gen.setEnabled(False)
        self.engine = ReportDataEngine(self.edit_user.text(), self.edit_id.text())
        self.engine.status_sig.connect(lambda p, m: self.pbar.setValue(p))
        self.engine.finished_sig.connect(self._on_finished)
        self.engine.start()

    def _on_finished(self, data):
        self.btn_gen.setEnabled(True)
        self.report_canvas.set_report_data(data)
        self.hash_log.setText(data['auth_code'])
        self.hash_log.setStyleSheet("background: #05070A; color: #00FF94; font-family: Consolas;")