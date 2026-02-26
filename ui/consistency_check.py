import sys
import time
import math
import random
import numpy as np
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# 使用 SciPy 提供的高级统计学特征关联算法
from scipy.stats import pearsonr, spearmanr, kendalltau

# =============================================================================
# 1. 专利核心数学引擎：多维序列生成与一致性解算
# =============================================================================

class ConsistencyComputeEngine(QThread):
    """
    专利[0110]-[0112] 振荡一致性核心解算引擎
    生成不同温度下的振荡异常系数序列，并计算全局相关性矩阵
    """
    result_ready = pyqtSignal(dict)
    log_sig = pyqtSignal(str, str)

    def __init__(self, num_devices, num_temps, method):
        super().__init__()
        self.num_devices = num_devices
        self.num_temps = num_temps
        self.method = method
        self._abort = False
        
    def stop(self):
        self._abort = True

    def run(self):
        self.log_sig.emit("SYS", f">>> 启动全局一致性关联分析引擎 (算法: {self.method})...")
        time.sleep(0.5)
        
        # 1. 模拟生成专利[0110]要求的“振荡异常序列 P_ki”
        # 假设大部分正常器件在并联中表现出相似的温度-振荡衰减特性
        base_sequence = np.linspace(1.5, 3.5, self.num_temps) + np.sin(np.linspace(0, 3, self.num_temps))
        
        p_matrix =[]
        for i in range(self.num_devices):
            if self._abort: return
            # 随机注入 15% 的“一致性崩塌”异常器件
            if random.random() < 0.15:
                # 异常序列：热应力导致振荡系数 P_ki 突变或相位滞后
                seq = base_sequence * random.uniform(0.3, 0.6) + np.random.normal(1.0, 0.8, self.num_temps)
                self.log_sig.emit("WARN", f"发现潜在热应力失控器件特征: Device_{i:02d}")
            else:
                # 正常序列：紧跟基准表现
                seq = base_sequence + np.random.normal(0, 0.15, self.num_temps)
            p_matrix.append(seq)
            
        # 2. 交叉计算序列相关性矩阵 (专利[0111]-[0112])
        self.log_sig.emit("PROCESS", f"构建 {self.num_devices}x{self.num_devices} 维度高阶相关性矩阵...")
        corr_matrix = np.zeros((self.num_devices, self.num_devices))
        
        for i in range(self.num_devices):
            for j in range(i, self.num_devices):
                if self._abort: return
                if i == j:
                    corr_matrix[i, j] = 1.0
                    continue
                
                # 支持专利提到的多种相关性算法扩展
                if self.method == 'Pearson':
                    c, _ = pearsonr(p_matrix[i], p_matrix[j])
                elif self.method == 'Spearman':
                    c, _ = spearmanr(p_matrix[i], p_matrix[j])
                else:
                    c, _ = kendalltau(p_matrix[i], p_matrix[j])
                    
                # 规整到 0~1 范围便于力导向图渲染
                c_norm = max(0, min(1, c)) 
                corr_matrix[i, j] = c_norm
                corr_matrix[j, i] = c_norm

        # 3. 计算每个器件的振荡一致性 Ui (均值)
        u_scores =[]
        for i in range(self.num_devices):
            # 排除自身(1.0)后求均值
            mean_corr = (np.sum(corr_matrix[i]) - 1.0) / (self.num_devices - 1)
            u_scores.append(mean_corr)
            self.log_sig.emit("MATH", f"[Device_{i:02d}] 综合振荡一致性 Ui = {mean_corr:.4f}")

        self.log_sig.emit("SUCCESS", "多维一致性拓扑矩阵解算完成。")
        self.result_ready.emit({
            'p_matrix': p_matrix,
            'corr_matrix': corr_matrix,
            'u_scores': u_scores
        })

# =============================================================================
# 2. 独创：基于 PyQt6 手写的力导向物理引擎拓扑图 (Force-Directed Graph)
# =============================================================================

class NodeItem(QGraphicsEllipseItem):
    """拓扑图中的 IGBT 器件节点"""
    def __init__(self, dev_id, u_score, parent=None):
        super().__init__(-22, -22, 44, 44, parent)
        self.dev_id = dev_id
        self.u_score = u_score
        
        # 物理引擎参数
        self.velocity = QPointF(0, 0)
        self.mass = 1.0
        
        # 开启鼠标拖拽和悬停，并监听位置变化
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        # 专利逻辑映射：根据一致性 Ui 确定颜色 (高一致性为荧光绿，低为危险红)
        self.base_color = QColor(0, 255, 148) if u_score > 0.7 else QColor(255, 77, 77)
        if 0.4 < u_score <= 0.7: 
            self.base_color = QColor(255, 204, 0) # 边缘状态显示为黄色
            
        self.setBrush(QBrush(self.base_color))
        self.setPen(QPen(QColor(255, 255, 255), 2))
        self.setZValue(2)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        # 节点中心文字绘制
        painter.setPen(Qt.GlobalColor.black if self.u_score > 0.7 else Qt.GlobalColor.white)
        painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, f"D{self.dev_id}")

    def itemChange(self, change, value):
        """位置改变时实时通知相连的边重绘 (修复了NoneType错误)"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 必须进行 self.scene() 的空值校验，防止初始化时崩溃
            if self.scene() is not None:
                for edge in self.scene().items():
                    if isinstance(edge, EdgeItem):
                        if edge.source == self or edge.dest == self:
                            edge.update_position()
        return super().itemChange(change, value)

class EdgeItem(QGraphicsLineItem):
    """拓扑图中的相关性连线 (模拟物理弹簧)"""
    def __init__(self, source_node, dest_node, weight):
        super().__init__()
        self.source = source_node
        self.dest = dest_node
        self.weight = weight # Pearson 相关系数作为弹簧引力权重
        self.setZValue(1)
        self.update_position()

    def update_position(self):
        line = QLineF(self.source.pos(), self.dest.pos())
        self.setLine(line)
        
        # 线条视觉效果随相关性权重动态变化
        if self.weight > 0.8:
            color = QColor(0, 163, 255, int(255 * self.weight))
            width = 3.0 * self.weight
        elif self.weight > 0.5:
            color = QColor(150, 150, 150, int(180 * self.weight))
            width = 1.5
        else:
            color = QColor(255, 77, 77, 80) # 弱相关显示为红色虚弱线
            width = 1.0
            
        self.setPen(QPen(color, width, Qt.PenStyle.SolidLine))

class ForceDirectedTopology(QGraphicsView):
    """
    物理引擎画布核心：利用库仑力与胡克定律实时推演节点位置
    直观展示 IGBT 模块在一致性空间中的“抱团聚集”与“孤立游离”状态
    """
    node_clicked_sig = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(10, 14, 18))) # 极客深邃背景
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        self.nodes = []
        self.edges =[]
        
        # 物理引擎可调超参数
        self.corr_threshold = 0.0
        self.k_repel = 8000.0   # 库仑斥力
        self.k_spring = 0.02    # 胡克引力
        self.damping = 0.85     # 空间阻尼
        self.ideal_len = 150.0  # 弹簧原长
        
        # 物理引擎时钟 (30 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.physics_step)

    def build_network(self, num_devices, corr_matrix, u_scores):
        self.timer.stop()
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        
        # 初始化节点位置 (在视图中心进行高斯随机散布)
        for i in range(num_devices):
            nx = random.gauss(0, 100)
            ny = random.gauss(0, 100)
            node = NodeItem(i, u_scores[i])
            node.setPos(nx, ny)
            self.scene.addItem(node)
            self.nodes.append(node)
            
        # 建立物理连线网络
        for i in range(num_devices):
            for j in range(i+1, num_devices):
                weight = corr_matrix[i, j]
                edge = EdgeItem(self.nodes[i], self.nodes[j], weight)
                self.scene.addItem(edge)
                self.edges.append(edge)
                
        self.timer.start(33) # 约 30 FPS

    def update_physics_params(self, param_type, value):
        """响应 UI 调节物理引擎参数"""
        if param_type == 'threshold':
            self.corr_threshold = value
            for edge in self.edges:
                edge.setVisible(edge.weight >= self.corr_threshold)
        elif param_type == 'repel':
            self.k_repel = value
        elif param_type == 'spring':
            self.k_spring = value
        elif param_type == 'damping':
            self.damping = value

    def physics_step(self):
        """核心推演：每帧进行排斥力与吸引力叠加计算"""
        if not self.nodes: return
        
        forces = {node: QPointF(0, 0) for node in self.nodes}
        
        # 1. 计算节点间的库仑排斥力 (防止重叠聚堆)
        for i, n1 in enumerate(self.nodes):
            for j, n2 in enumerate(self.nodes):
                if i >= j: continue
                dx = n1.pos().x() - n2.pos().x()
                dy = n1.pos().y() - n2.pos().y()
                dist_sq = dx*dx + dy*dy + 0.1 # 加 0.1 防止除以 0
                dist = math.sqrt(dist_sq)
                
                repel_f = self.k_repel / dist_sq
                fx = repel_f * (dx / dist)
                fy = repel_f * (dy / dist)
                
                forces[n1] += QPointF(fx, fy)
                forces[n2] -= QPointF(fx, fy)
                
        # 2. 计算连线的胡克吸引力 (相关性越强，引力越大)
        for edge in self.edges:
            if not edge.isVisible(): continue
            n1, n2 = edge.source, edge.dest
            dx = n2.pos().x() - n1.pos().x()
            dy = n2.pos().y() - n1.pos().y()
            dist = math.sqrt(dx*dx + dy*dy + 0.1)
            
            # F = k * (x - x0) * weight
            attract_f = self.k_spring * (dist - self.ideal_len) * edge.weight
            fx = attract_f * (dx / dist)
            fy = attract_f * (dy / dist)
            
            forces[n1] += QPointF(fx, fy)
            forces[n2] -= QPointF(fx, fy)

        # 3. 计算中心引力 (防止孤立节点飞出宇宙边界)
        for node in self.nodes:
            center_dx, center_dy = -node.pos().x(), -node.pos().y()
            forces[node] += QPointF(center_dx * 0.02, center_dy * 0.02)

            # 更新速度 (包含阻尼减速)
            node.velocity.setX(node.velocity.x() * self.damping + forces[node].x())
            node.velocity.setY(node.velocity.y() * self.damping + forces[node].y())
            
            # 速度钳制，防止动能爆炸
            vx = max(-25, min(25, node.velocity.x()))
            vy = max(-25, min(25, node.velocity.y()))
            
            node.setPos(node.pos().x() + vx, node.pos().y() + vy)

    def mousePressEvent(self, event):
        """捕获鼠标点击节点事件，触发右侧雷达图联动"""
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            self.node_clicked_sig.emit(item.dev_id)

    def wheelEvent(self, event):
        """支持滚轮缩放画布"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

# =============================================================================
# 3. 雷达特征图表 (Radar Chart Canvas)
# =============================================================================

class RadarChartCanvas(QWidget):
    """
    极坐标雷达图：用于多维展示选中器件与全网其他器件的相关性 Ui 剖面
    """
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.fig = Figure(facecolor='#151921', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111, polar=True)
        self.ax.set_facecolor('#0B0E14')

    def render_radar(self, target_id, corr_matrix):
        self.ax.clear()
        
        num_vars = len(corr_matrix)
        if num_vars < 3: return # 雷达图至少需要3个点
        
        # 提取目标设备与其他设备的相关性
        corrs = corr_matrix[target_id].tolist()
        
        # 构造雷达图的闭合环数据
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        corrs += corrs[:1]
        angles += angles[:1]
        
        # 绘制雷达扫描面
        self.ax.plot(angles, corrs, color='#00A3FF', linewidth=2.5)
        self.ax.fill(angles, corrs, color='#00A3FF', alpha=0.3)
        
        # 绘制专利核心指标：平均一致性基准线 Ui
        avg_corr = np.mean(corr_matrix[target_id])
        self.ax.plot(angles, [avg_corr]*len(angles), color='#FFCC00', linestyle='-.', linewidth=2, label=f'Overall Consistency (Ui): {avg_corr:.3f}')
        
        # 装饰图表
        labels =[f"D{i}" for i in range(num_vars)]
        self.ax.set_xticks(angles[:-1])
        self.ax.set_xticklabels(labels, color='#888', fontsize=9, fontweight='bold')
        self.ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        self.ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], color='#444', fontsize=8)
        self.ax.spines['polar'].set_color('#2A2F3A')
        
        self.ax.set_title(f"Multi-dimensional Consistency Profile (Device_{target_id})", color='white', pad=20, fontsize=12)
        self.ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1), facecolor='#1A1F26', edgecolor='#333', labelcolor='white')
        
        self.fig.tight_layout()
        self.canvas.draw()

# =============================================================================
# 4. 主控页面统筹整合 (Consistency Check Page)
# =============================================================================

class ConsistencyCheckPage(QWidget):
    """
    第九个菜单主类：振荡一致性校核 (Ui 计算)
    融合了大量滑动控制杆、物理拓扑网络、雷达图与多线程数学解算引擎
    代码规模极为庞大
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self.corr_matrix_cache = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ---------------------------------------------------------
        # 左侧：深度配置与引擎参数调节面板 (450px)
        # ---------------------------------------------------------
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(450)
        self.left_panel.setStyleSheet("background-color: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        self.left_layout = QVBoxLayout(self.left_panel)

        title = QLabel("振荡一致性校核分析系统")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF; border: none;")
        self.left_layout.addWidget(title)
        
        info = QLabel("")
        info.setStyleSheet("color: #8B949E; font-size: 11px; border: none; margin-bottom: 10px;")
        self.left_layout.addWidget(info)

        # A. 算法超参数设定
        config_gb = QGroupBox("相关性矩阵构建参数")
        config_l = QFormLayout(config_gb)
        self.sp_dev = QSpinBox(); self.sp_dev.setRange(5, 50); self.sp_dev.setValue(20)
        self.sp_temp = QSpinBox(); self.sp_temp.setRange(5, 100); self.sp_temp.setValue(24)
        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["Pearson (皮尔逊积矩相关)", "Spearman (斯皮尔曼秩相关)", "Kendall (肯德尔秩相关)"])
        config_l.addRow("并联样本组规模 (N):", self.sp_dev)
        config_l.addRow("温度切片维度数 (Dim):", self.sp_temp)
        config_l.addRow("关联度统计算法:", self.cmb_method)
        self.left_layout.addWidget(config_gb)

        # B. 物理引擎实时控制器 (新增的极致交互功能)
        phys_gb = QGroupBox("力导向物理引擎控制台")
        phys_l = QFormLayout(phys_gb)
        
        self.sl_th = QSlider(Qt.Orientation.Horizontal); self.sl_th.setRange(0, 100); self.sl_th.setValue(40)
        self.sl_repel = QSlider(Qt.Orientation.Horizontal); self.sl_repel.setRange(1000, 20000); self.sl_repel.setValue(8000)
        self.sl_spring = QSlider(Qt.Orientation.Horizontal); self.sl_spring.setRange(1, 100); self.sl_spring.setValue(20)
        
        self.lbl_th = QLabel("剪枝阈值: 0.40")
        self.lbl_repel = QLabel("库仑斥力: 8000")
        self.lbl_spring = QLabel("弹簧刚度: 0.02")
        
        # 绑定滑动事件进行实时调节
        self.sl_th.valueChanged.connect(lambda v: self._update_phys('threshold', v))
        self.sl_repel.valueChanged.connect(lambda v: self._update_phys('repel', v))
        self.sl_spring.valueChanged.connect(lambda v: self._update_phys('spring', v))
        
        phys_l.addRow(self.lbl_th, self.sl_th)
        phys_l.addRow(self.lbl_repel, self.sl_repel)
        phys_l.addRow(self.lbl_spring, self.sl_spring)
        self.left_layout.addWidget(phys_gb)

        # C. 引擎执行控制
        self.btn_run = QPushButton("⚡ 重构物理网络与多维关联矩阵")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { background: #0078D4; color: white; font-weight: bold; font-size: 15px; border-radius: 4px;}
            QPushButton:hover { background: #0086F0; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.btn_run.clicked.connect(self._execute_analysis)
        self.left_layout.addWidget(self.btn_run)

        # D. 审计监控日志
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #090C10; color: #00FF94; font-family: Consolas; font-size: 11px; border: 1px solid #222;")
        self.left_layout.addWidget(QLabel("物理引擎与数学推演踪迹:"))
        self.left_layout.addWidget(self.console)

        # ---------------------------------------------------------
        # 右侧：可视化画布分割 (物理网络 + 雷达图) 占用剩余全部空间
        # ---------------------------------------------------------
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 物理拓扑网络
        self.topo_box = QGroupBox("力导向一致性关联拓扑网络 (支持滚轮缩放/节点拖拽)")
        topo_l = QVBoxLayout(self.topo_box)
        self.topo_view = ForceDirectedTopology()
        self.topo_view.node_clicked_sig.connect(self._on_node_clicked) # 绑定点击联动
        topo_l.addWidget(self.topo_view)
        
        # 雷达图分析
        self.radar_box = QGroupBox("单一器件多维一致性雷达扫描剖面")
        radar_l = QVBoxLayout(self.radar_box)
        self.radar_canvas = RadarChartCanvas()
        radar_l.addWidget(self.radar_canvas)
        
        self.right_splitter.addWidget(self.topo_box)
        self.right_splitter.addWidget(self.radar_box)
        self.right_splitter.setStretchFactor(0, 6)
        self.right_splitter.setStretchFactor(1, 4)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_splitter, 1)

    # --- 信号槽与交互逻辑 ---

    def _update_phys(self, ptype, val):
        """响应左侧滑块，实时改变右侧的物理引擎参数"""
        if ptype == 'threshold':
            v = val / 100.0
            self.lbl_th.setText(f"剪枝阈值: {v:.2f}")
            self.topo_view.update_physics_params('threshold', v)
        elif ptype == 'repel':
            self.lbl_repel.setText(f"库仑斥力: {val}")
            self.topo_view.update_physics_params('repel', float(val))
        elif ptype == 'spring':
            v = val / 1000.0
            self.lbl_spring.setText(f"弹簧刚度: {v:.3f}")
            self.topo_view.update_physics_params('spring', v)

    def _execute_analysis(self):
        self.btn_run.setEnabled(False)
        self.console.clear()
        
        n_dev = self.sp_dev.value()
        n_tmp = self.sp_temp.value()
        method = self.cmb_method.currentText().split()[0]
        
        self.engine = ConsistencyComputeEngine(n_dev, n_tmp, method)
        self.engine.log_sig.connect(self._append_log)
        self.engine.result_ready.connect(self._on_analysis_complete)
        self.engine.start()

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00A3FF" if tag == "MATH" else ("#FF8C00" if tag == "WARN" else "#00FF94")
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: {color};'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _on_analysis_complete(self, data):
        self.btn_run.setEnabled(True)
        self.corr_matrix_cache = data['corr_matrix']
        
        # 1. 建立物理拓扑网络
        self.topo_view.build_network(self.sp_dev.value(), data['corr_matrix'], data['u_scores'])
        
        # 2. 注入当前 UI 面板上的物理参数状态
        self._update_phys('threshold', self.sl_th.value())
        self._update_phys('repel', self.sl_repel.value())
        self._update_phys('spring', self.sl_spring.value())
        
        # 3. 默认绘制 0 号器件的雷达图联动
        self._on_node_clicked(0)

    def _on_node_clicked(self, dev_id):
        """当用户在拓扑图中点击某个光球节点时，瞬间联动更新底部的雷达图"""
        if self.corr_matrix_cache is not None:
            self._append_log("UI", f"交叉锁定目标：正在生成 Device_{dev_id} 的全网多维雷达剖面。")
            self.radar_canvas.render_radar(dev_id, self.corr_matrix_cache)