import sys
import time
import random
import numpy as np
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

# =============================================================================
# 1. 核心流水线状态机引擎 (Pipeline Orchestration Engine)
# =============================================================================

class PipelineEngine(QThread):
    """
    自动化流水线引擎：严格按照专利 CN 119270019 B 的算法依赖拓扑执行任务
    """
    node_state_changed = pyqtSignal(int, str) # node_id, state
    edge_active = pyqtSignal(int, int, bool)  # src, dst, active
    log_msg = pyqtSignal(str, str)
    task_timing = pyqtSignal(int, float, float) # node_id, start_time, end_time

    def __init__(self):
        super().__init__()
        self._abort = False
        
        # 定义专利算法的 DAG 依赖结构
        # 节点定义：0:采集, 1:三元组聚类(Gki), 2:振荡解析(Pki), 3:一致性(Ui), 4:趋势(Ti), 5:综合质量(Wi)
        self.nodes =[0, 1, 2, 3, 4, 5]
        
        # 定义数据流向依赖 (src -> dest)
        # 例如 2(Pki) 需要 1(Gki) 的结果，公式 Pki = Gki * (Hki + Mki)
        self.edges =[
            (0, 1), (0, 2), 
            (1, 2), 
            (2, 3), (2, 4), 
            (3, 5), (4, 5)
        ]

    def run(self):
        self.log_msg.emit("SYSTEM", ">>> 启动全自动专利算法分析流水线...")
        start_t = time.time()

        # 模拟 0. 性能数据采集 [0048]
        self._execute_node(0, "正在通过 VISA 协议调取所有批次短路电流底层数据...", 1.5)

        # 模拟并发阶段 A: 聚类分析先执行
        self.edge_active.emit(0, 1, True)
        self._execute_node(1, "执行三元组 KMeans 聚类并解算突变偏移系数 (G_ki)...", 2.0)
        self.edge_active.emit(0, 1, False)

        # 模拟 2. 振荡异常解析 [0024] (依赖 0 和 1)
        self.edge_active.emit(0, 2, True)
        self.edge_active.emit(1, 2, True)
        self._execute_node(2, "提取波峰特征，结合 G_ki 注入，解算振荡异常系数 (P_ki)...", 2.5)
        self.edge_active.emit(0, 2, False)
        self.edge_active.emit(1, 2, False)

        # 模拟并发阶段 B: 一致性 Ui 与 趋势 Ti 同时或乱序解算
        self.edge_active.emit(2, 3, True)
        self._execute_node(3, "构建多维皮尔逊相关性网络，计算振荡一致性 (U_i)...", 1.8)
        self.edge_active.emit(2, 3, False)

        self.edge_active.emit(2, 4, True)
        self._execute_node(4, "执行 Mann-Kendall 检验，量化温度趋势显著性 (T_i)...", 1.6)
        self.edge_active.emit(2, 4, False)

        # 模拟最终汇聚节点: 质量分级[0114]
        self.edge_active.emit(3, 5, True)
        self.edge_active.emit(4, 5, True)
        self._execute_node(5, "融合 T_i 与 U_i，生成最终质量评分 W_i 并执行切片熔断判定...", 2.2)
        self.edge_active.emit(3, 5, False)
        self.edge_active.emit(4, 5, False)

        total_time = time.time() - start_t
        self.log_msg.emit("SUCCESS", f"流水线总控执行完毕。全序列耗时: {total_time:.2f} 秒")

    def _execute_node(self, node_id, desc, duration):
        if self._abort: return
        self.node_state_changed.emit(node_id, "RUNNING")
        self.log_msg.emit(f"NODE-{node_id}", desc)
        
        t0 = time.time()
        # 模拟真实算法的计算耗时
        steps = int(duration * 10)
        for _ in range(steps):
            if self._abort: return
            time.sleep(0.1)
            
        t1 = time.time()
        self.task_timing.emit(node_id, t0, t1)
        self.node_state_changed.emit(node_id, "SUCCESS")

    def stop(self):
        self._abort = True

# =============================================================================
# 2. 纯自绘 DAG 节点图元系统 (Node & Edge Graphics Items)
# =============================================================================

class PipelineEdge(QGraphicsItem):
    """
    表示节点间数据流向的贝塞尔曲线
    包含虚线流动动画 (Marching Ants Effect)
    """
    def __init__(self, src_node, dst_node):
        super().__init__()
        self.src = src_node
        self.dst = dst_node
        self.is_active = False
        self.dash_offset = 0
        self.setZValue(1)

    def boundingRect(self):
        return QRectF(self.src.scenePos(), self.dst.scenePos()).normalized().adjusted(-20, -20, 20, 20)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 计算连接点
        p1 = self.src.scenePos() + QPointF(self.src.width, self.src.height/2)
        p2 = self.dst.scenePos() + QPointF(0, self.dst.height/2)
        
        # 绘制平滑的三次贝塞尔曲线
        path = QPainterPath(p1)
        ctrl_1 = QPointF(p1.x() + 80, p1.y())
        ctrl_2 = QPointF(p2.x() - 80, p2.y())
        path.cubicTo(ctrl_1, ctrl_2, p2)
        
        # 基础连线样式 (深色背景轨)
        painter.setPen(QPen(QColor(50, 60, 70), 3, Qt.PenStyle.SolidLine))
        painter.drawPath(path)
        
        # 激活状态的流动光效 (流动虚线)
        if self.is_active:
            glow_pen = QPen(QColor(0, 255, 148), 3, Qt.PenStyle.DashLine)
            glow_pen.setDashPattern([5, 5])
            glow_pen.setDashOffset(self.dash_offset)
            painter.setPen(glow_pen)
            painter.drawPath(path)

    def advance_animation(self):
        if self.is_active:
            self.dash_offset -= 1 # 虚线向右流动
            self.update()

class PipelineNode(QGraphicsObject):
    """
    带呼吸灯效果与阴影渲染的工业级流水线节点
    """
    clicked_sig = pyqtSignal(int)

    def __init__(self, node_id, title, subtitle, x, y):
        super().__init__()
        self.node_id = node_id
        self.title = title
        self.subtitle = subtitle
        self.width = 180
        self.height = 70
        self.setPos(x, y)
        
        self.state = "PENDING" # PENDING, RUNNING, SUCCESS, FAIL
        self.glow_alpha = 0
        self.glow_dir = 1
        
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-10, -10, self.width + 20, self.height + 20)

    def set_state(self, state):
        self.state = state
        self.update()

    def advance_animation(self):
        if self.state == "RUNNING":
            self.glow_alpha += 10 * self.glow_dir
            if self.glow_alpha >= 180: self.glow_dir = -1
            elif self.glow_alpha <= 40: self.glow_dir = 1
            self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width, self.height)
        
        # 1. 绘制阴影与外发光
        if self.state == "RUNNING":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 163, 255, self.glow_alpha), 6))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 6, 6)
        elif self.state == "SUCCESS":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 255, 148, 100), 4))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 6, 6)

        # 2. 节点主体渐变背景
        grad = QLinearGradient(0, 0, self.width, self.height)
        if self.state == "PENDING":
            grad.setColorAt(0, QColor(30, 35, 40)); grad.setColorAt(1, QColor(20, 25, 30))
            border_color = QColor(60, 70, 80)
        elif self.state == "RUNNING":
            grad.setColorAt(0, QColor(0, 90, 150)); grad.setColorAt(1, QColor(0, 45, 80))
            border_color = QColor(0, 163, 255)
        elif self.state == "SUCCESS":
            grad.setColorAt(0, QColor(0, 100, 50)); grad.setColorAt(1, QColor(0, 50, 25))
            border_color = QColor(0, 255, 148)

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(rect, 6, 6)

        # 3. 状态标识圈
        painter.setBrush(border_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, 15, 10, 10)

        # 4. 文字渲染
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        painter.drawText(30, 25, self.title)
        
        painter.setPen(QColor(150, 160, 170))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(30, 50, self.subtitle)

    def mousePressEvent(self, event):
        self.clicked_sig.emit(self.node_id)
        super().mousePressEvent(event)

# =============================================================================
# 3. 画布视图与底层甘特图组件 (Canvas & Gantt Chart)
# =============================================================================

class PipelineCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(10, 14, 18))) # 暗黑图纸色
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.nodes_dict = {}
        self.edges_dict = {}
        
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate_elements)
        self.anim_timer.start(30) # 30 FPS 驱动所有光效

    def _animate_elements(self):
        for node in self.nodes_dict.values():
            node.advance_animation()
        for edge in self.edges_dict.values():
            edge.advance_animation()

    def drawBackground(self, painter, rect):
        """工程网格底纹"""
        super().drawBackground(painter, rect)
        painter.setPen(QPen(QColor(25, 30, 40), 1))
        for x in range(int(rect.left()), int(rect.right()), 40):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(int(rect.top()), int(rect.bottom()), 40):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

class GanttChartWidget(QWidget):
    """底层自绘执行甘特图：精准还原各环节耗时占比"""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.tasks =[] # (node_id, start_t, end_t, label)
        self.global_start = None

    def add_task(self, node_id, start_t, end_t, label):
        if not self.global_start: self.global_start = start_t
        self.tasks.append((node_id, start_t, end_t, label))
        self.update()

    def clear_tasks(self):
        self.tasks.clear()
        self.global_start = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        painter.fillRect(rect, QColor(13, 17, 22))
        painter.setPen(QPen(QColor(40, 50, 60), 1))
        painter.drawLine(0, 20, rect.width(), 20)
        
        if not self.tasks or not self.global_start:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Waiting for pipeline execution...")
            return

        # 计算时间轴跨度
        max_t = max([t[2] for t in self.tasks])
        total_duration = max(0.1, max_t - self.global_start)
        
        # 绘制时间轴刻度
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Consolas", 8))
        for i in range(11):
            x = i * (rect.width() / 10)
            t_val = (i / 10) * total_duration
            painter.drawLine(int(x), 15, int(x), 20)
            painter.drawText(int(x) + 2, 12, f"{t_val:.1f}s")
            # 辅助网格线
            painter.setPen(QPen(QColor(30, 40, 50), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(x), 20, int(x), rect.height())
            painter.setPen(QColor(150, 150, 150))

        # 绘制甘特任务块
        row_height = 20
        for idx, task in enumerate(self.tasks):
            nid, t0, t1, label = task
            x_start = ((t0 - self.global_start) / total_duration) * rect.width()
            x_end = ((t1 - self.global_start) / total_duration) * rect.width()
            w = max(4, x_end - x_start)
            y = 30 + idx * (row_height + 5)
            
            # 色块
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 163, 255, 180))
            painter.drawRoundedRect(QRectF(x_start, y, w, row_height), 3, 3)
            
            # 标签
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Microsoft YaHei", 8))
            painter.drawText(int(x_start) + 5, int(y) + 14, label)

# =============================================================================
# 4. 自动化流水线总控主页 (Automated Pipeline Page)
# =============================================================================

class AutomatedPipelinePage(QWidget):
    """
    第 13 个菜单：自动化流水线编排系统
    采用先进的 DAG 节点连线视图与甘特图协同
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self._init_ui()
        self._build_pipeline_graph()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 1. 顶部控制栏
        self.toolbar = QFrame()
        self.toolbar.setFixedHeight(50)
        self.toolbar.setStyleSheet("background-color: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        tb_l = QHBoxLayout(self.toolbar)
        
        title = QLabel("自动化评估流水线编排引擎")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00A3FF; border: none;")
        tb_l.addWidget(title)
        tb_l.addStretch()
        
        self.btn_start = QPushButton("▶ 启动全自动流水线")
        self.btn_start.setStyleSheet("background: #238636; color: white; font-weight:bold; padding: 6px 20px; border-radius:4px;")
        self.btn_start.clicked.connect(self._start_pipeline)
        
        self.btn_reset = QPushButton("重置引擎状态")
        self.btn_reset.setStyleSheet("background: #30363D; color: white; padding: 6px 20px; border-radius:4px;")
        self.btn_reset.clicked.connect(self._reset_pipeline)
        
        tb_l.addWidget(self.btn_reset); tb_l.addWidget(self.btn_start)
        self.main_layout.addWidget(self.toolbar)

        # 2. 中间核心区：拆分为左右 (画布 + 侧边栏)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：无限画布
        self.canvas = PipelineCanvas()
        self.h_splitter.addWidget(self.canvas)
        
        # 右侧：节点检查器与日志
        right_panel = QFrame()
        right_panel.setStyleSheet("background: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        r_layout = QVBoxLayout(right_panel)
        
        r_layout.addWidget(QLabel("<b style='color:#00A3FF'>节点参数检查器</b>"))
        self.prop_table = QTableWidget(4, 2)
        self.prop_table.horizontalHeader().hide(); self.prop_table.verticalHeader().hide()
        self.prop_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.prop_table.setStyleSheet("background: #0D1117; color: #EEE; border: 1px solid #333;")
        self._update_inspector("就绪", "请点击左侧画布中的节点查看对应专利参数。")
        r_layout.addWidget(self.prop_table)
        
        r_layout.addWidget(QLabel("<b style='color:#00FF94'>流水线微服务输出日志</b>"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #05070A; color: #DCDCDC; font-family: Consolas; font-size: 11px; border: 1px solid #333;")
        r_layout.addWidget(self.console)
        
        self.h_splitter.addWidget(right_panel)
        self.h_splitter.setStretchFactor(0, 7)
        self.h_splitter.setStretchFactor(1, 3)
        self.main_layout.addWidget(self.h_splitter)

        # 3. 底部区：执行甘特图
        self.gantt_box = QGroupBox("流水线执行性能剖析 (Execution Waterfall)")
        self.gantt_box.setStyleSheet("QGroupBox { font-weight: bold; color: #00A3FF; border: 1px solid #333; margin-top: 10px; }")
        gantt_l = QVBoxLayout(self.gantt_box)
        self.gantt = GanttChartWidget()
        gantt_l.addWidget(self.gantt)
        self.main_layout.addWidget(self.gantt_box)

    def _build_pipeline_graph(self):
        """
        构建契合专利依赖关系的 DAG 图
        坐标布局经过精心硬编码，呈现完美的工作流
        """
        self.canvas.scene.clear()
        self.canvas.nodes_dict.clear()
        self.canvas.edges_dict.clear()

        # 节点定义：(ID, 标题, 专利来源, X, Y)
        node_defs =[
            (0, "性能数据采集 (ACQ)", "[0048] 多通道同步", 50, 200),
            (1, "三元组聚类解算", "[0007] G_ki 计算", 300, 100),
            (2, "振荡特征量化", "[0024] P_ki 计算", 300, 300),
            (3, "振荡一致性校核", "[0112] U_i 计算", 550, 100),
            (4, "趋势显著性检测", "[0108] T_i 计算", 550, 300),
            (5, "综合质量分级评定", "[0114] W_i 熔断", 800, 200)
        ]

        # 实例化节点
        for nid, title, sub, x, y in node_defs:
            n = PipelineNode(nid, title, sub, x, y)
            n.clicked_sig.connect(self._on_node_clicked)
            self.canvas.scene.addItem(n)
            self.canvas.nodes_dict[nid] = n

        # 实例化边 (流向依赖)
        edges =[(0,1), (0,2), (1,2), (2,3), (2,4), (3,5), (4,5)]
        for src, dst in edges:
            e = PipelineEdge(self.canvas.nodes_dict[src], self.canvas.nodes_dict[dst])
            self.canvas.scene.addItem(e)
            self.canvas.edges_dict[(src, dst)] = e

    def _update_inspector(self, name, desc):
        """伪造不同节点的属性配置"""
        self.prop_table.setItem(0, 0, QTableWidgetItem("节点模块:"))
        self.prop_table.setItem(0, 1, QTableWidgetItem(name))
        self.prop_table.setItem(1, 0, QTableWidgetItem("业务状态:"))
        self.prop_table.setItem(1, 1, QTableWidgetItem(desc))
        self.prop_table.setItem(2, 0, QTableWidgetItem("线程调度:"))
        self.prop_table.setItem(2, 1, QTableWidgetItem("Async / GPU-Accelerated"))
        self.prop_table.setItem(3, 0, QTableWidgetItem("专利关联度:"))
        self.prop_table.setItem(3, 1, QTableWidgetItem("CN119270019B - HIGH"))

    def _on_node_clicked(self, node_id):
        node = self.canvas.nodes_dict[node_id]
        self._update_inspector(node.title, f"State: {node.state}")
        self._log("UI", f"载入节点 {node.title} 详细超参数配置表...")

    def _start_pipeline(self):
        if self.engine and self.engine.isRunning(): return
        self._reset_pipeline()
        self.btn_start.setEnabled(False)
        self.btn_reset.setEnabled(False)
        
        self.engine = PipelineEngine()
        self.engine.log_msg.connect(self._log)
        self.engine.node_state_changed.connect(self._on_node_state)
        self.engine.edge_active.connect(self._on_edge_active)
        self.engine.task_timing.connect(self._on_task_done)
        self.engine.finished.connect(self._on_pipeline_done)
        self.engine.start()

    def _reset_pipeline(self):
        self.console.clear()
        self.gantt.clear_tasks()
        for node in self.canvas.nodes_dict.values():
            node.set_state("PENDING")
        for edge in self.canvas.edges_dict.values():
            edge.is_active = False
            edge.update()

    def _log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00A3FF"
        if tag == "SYSTEM": color = "#FFCC00"
        elif tag == "SUCCESS": color = "#00FF94"
        self.console.append(f"<span style='color:#555'>[{ts}]</span> <b style='color:{color}'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _on_node_state(self, node_id, state):
        if node_id in self.canvas.nodes_dict:
            self.canvas.nodes_dict[node_id].set_state(state)

    def _on_edge_active(self, src, dst, active):
        if (src, dst) in self.canvas.edges_dict:
            self.canvas.edges_dict[(src, dst)].is_active = active

    def _on_task_done(self, node_id, start_t, end_t):
        node = self.canvas.nodes_dict[node_id]
        self.gantt.add_task(node_id, start_t, end_t, node.title)

    def _on_pipeline_done(self):
        self.btn_start.setEnabled(True)
        self.btn_reset.setEnabled(True)