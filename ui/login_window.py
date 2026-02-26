import sys
import math
import time
import random
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# =============================================================================
# 1. 左侧视觉区
# =============================================================================
class LeftVisualBoard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(450)
        self.scan_pos = 0
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(30)

    def update_anim(self):
        self.scan_pos = (self.scan_pos + 4) % (self.height() or 1)
        self.angle = (self.angle + 2) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#0A0E14")); grad.setColorAt(1, QColor("#1A212E"))
        p.fillRect(self.rect(), grad)
        p.save()
        p.translate(self.width()/2, self.height()/2)
        p.rotate(self.angle)
        p.setPen(QPen(QColor(0, 163, 255, 50), 1))
        for r in range(50, 400, 50): p.drawEllipse(QPointF(0, 0), r, r)
        p.restore()
        p.setPen(QPen(QColor(0, 255, 148, 150), 2))
        p.drawLine(0, self.scan_pos, self.width(), self.scan_pos)
        p.setPen(Qt.GlobalColor.white)
        p.setFont(QFont("Impact", 35))
        p.drawText(40, 120, "IGBT 智能自动化测试系统")

# =============================================================================
# 2. 登录窗体 (修复版)
# =============================================================================
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setFixedSize(1000, 650)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._init_ui()

    def _init_ui(self):
        self.root_vbox = QVBoxLayout(self)
        self.root_vbox.setContentsMargins(0, 0, 0, 0)
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet("background-color: #0F1218; border-radius: 20px; border: 1px solid #1C222D;")
        self.main_h_layout = QHBoxLayout(self.bg_frame)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0); self.main_h_layout.setSpacing(0)

        self.main_h_layout.addWidget(LeftVisualBoard(self))

        self.interaction_container = QWidget()
        self.interaction_container.setStyleSheet("background-color: #0F1218;")
        self.interaction_layout = QVBoxLayout(self.interaction_container)
        self.interaction_layout.setContentsMargins(0, 0, 0, 0)

        # 核心：创建两个盒，强制同步变量名
        self.login_box = self._build_login_box()
        self.register_box = self._build_register_box()
        
        self.interaction_layout.addWidget(self.login_box)
        self.interaction_layout.addWidget(self.register_box)
        self.register_box.hide()

        self.close_btn = QPushButton("×", self.interaction_container)
        self.close_btn.setGeometry(510, 10, 30, 30)
        self.close_btn.setStyleSheet("color: #555; font-size: 26px; border: none; background: transparent;")
        self.close_btn.clicked.connect(self.close)

        self.main_h_layout.addWidget(self.interaction_container)
        self.root_vbox.addWidget(self.bg_frame)

    def _build_login_box(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(70, 100, 70, 70); layout.setSpacing(25)
        title = QLabel("系统登陆")
        title.setStyleSheet("color: white; font-size: 32px; font-weight: bold;")
        layout.addWidget(title)

        style = "background: #1A1F26; border: 1px solid #333; color: white; padding: 12px; border-radius: 5px;"
        self.user_input = QLineEdit() # <--- 名字同步回 user_input
        self.user_input.setText("admin")
        self.pass_input = QLineEdit()
        self.pass_input.setText("patent2025")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.user_input.setStyleSheet(style); self.pass_input.setStyleSheet(style)
        layout.addWidget(self.user_input); layout.addWidget(self.pass_input)

        login_btn = QPushButton("登录认证")
        login_btn.setFixedHeight(50)
        login_btn.setStyleSheet("background: #0078D4; color: white; font-weight: bold; border-radius: 25px;")
        login_btn.clicked.connect(self.accept)
        layout.addWidget(login_btn)

        reg_link = QPushButton("没有授权? 立即申请入网")
        reg_link.setStyleSheet("color: #00A3FF; border: none; background: transparent; text-decoration: underline;")
        reg_link.clicked.connect(self._show_register_ui)
        layout.addWidget(reg_link, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return box

    def _build_register_box(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(70, 80, 70, 70); layout.setSpacing(20)
        title = QLabel("注册新账号")
        title.setStyleSheet("color: #00FF94; font-size: 30px; font-weight: bold;")
        layout.addWidget(title)

        reg_style = "background: #161B22; border: 1px solid #00FF94; color: white; padding: 12px; border-radius: 5px;"
        self.reg_u = QLineEdit(); self.reg_u.setPlaceholderText("设置账号 UID")
        self.reg_p = QLineEdit(); self.reg_p.setPlaceholderText("设置密钥 PASSWORD")
        self.reg_p.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_i = QLineEdit(); self.reg_i.setPlaceholderText("所属机构/单位")

        for w in [self.reg_u, self.reg_p, self.reg_i]:
            w.setStyleSheet(reg_style)
            layout.addWidget(w)

        do_reg_btn = QPushButton("提交注册申请")
        do_reg_btn.setFixedHeight(50)
        do_reg_btn.setStyleSheet("background: #238636; color: white; font-weight: bold; border-radius: 25px;")
        do_reg_btn.clicked.connect(self._handle_reg_done)
        layout.addWidget(do_reg_btn)

        back_btn = QPushButton("← 返回登录中心")
        back_btn.setStyleSheet("color: #666; border: none; background: transparent;")
        back_btn.clicked.connect(self._show_login_ui)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return box

    def _show_register_ui(self):
        self.login_box.hide(); self.register_box.show(); self.update()

    def _show_login_ui(self):
        self.register_box.hide(); self.login_box.show(); self.update()

    def _handle_reg_done(self):
        QMessageBox.information(self, "申请成功", "数据已同步，请返回登录。")
        self._show_login_ui()

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()