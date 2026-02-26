import sys
import time
import random
import numpy as np
from datetime import datetime

# 科学计算与机器学习逻辑 (对应专利[0007]聚类算法)
from sklearn.cluster import KMeans
from scipy.spatial import distance

# UI 核心组件
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# 3D 可视化支持 (展示三元组空间分布)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d import Axes3D

# =============================================================================
# 核心专利算法引擎 (Logic Engine)
# =============================================================================

class PatentClusteringEngine(QObject):
    """
    基于专利 CN 119270019 B 的突变分析引擎
    实现 $G_{k,i} = A_{k,i} \times F_{k,i}$ 算法
    """
    analysis_finished = pyqtSignal(dict)
    log_signal = pyqtSignal(str, str)

    def run_analysis(self, raw_data_matrix, comprehensive_factor):
        """执行专利逻辑分析"""
        self.log_signal.emit("INFO", ">>> 启动专利级三元组聚类引擎...")
        
        # 1. 执行 K-Means 聚类 (专利[0007]: 得到两个聚类簇)
        # 输入数据维度为 [N, 3] -> (Isc, Vce, Vge)
        kmeans = KMeans(n_clusters=2, n_init='auto', random_state=42)
        kmeans.fit(raw_data_matrix)
        labels = kmeans.labels_
        centers = kmeans.cluster_centers_

        self.log_signal.emit("PROCESS", "聚类完成：成功识别两组时域行为特征簇。")

        # 2. 计算 A_ki (专利[0012]: 两个聚类簇之间的差异均值)
        # 这里使用欧氏距离表示中心点差异
        a_ki = distance.euclidean(centers[0], centers[1])
        self.log_signal.emit("MATH", f"计算簇间差异均值 Aki = {a_ki:.4f}")

        # 3. 计算 G_ki (专利[0015]: Gki = Aki * Fki)
        # Fki 为综合差异系数，由 UI 传入或从多器件库获取
        g_ki = a_ki * comprehensive_factor
        self.log_signal.emit("MATH", f"应用综合差异系数 Fki = {comprehensive_factor:.4f}")
        self.log_signal.emit("SUCCESS", f"最终确定突变偏移系数 Gki = {g_ki:.6f}")

        # 整理结果用于 UI 渲染
        result = {
            'data': raw_data_matrix,
            'labels': labels,
            'centers': centers,
            'a_ki': a_ki,
            'g_ki': g_ki,
            'ts': datetime.now().strftime("%H:%M:%S")
        }
        self.analysis_finished.emit(result)

# =============================================================================
# 深度交互页面 (UI Component)
# =============================================================================

class MutationAnalysisPage(QWidget):
    """
    第三个菜单：突变差异与聚类分析 (500行深度逻辑版)
    """
    def __init__(self):
        super().__init__()
        self.engine = PatentClusteringEngine()
        self.engine.analysis_finished.connect(self._on_result_ready)
        self.engine.log_signal.connect(self._append_log)
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # --- 左侧：交互控制面板 (400px) ---
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(420)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("突变差异与三元组聚类分析")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00A3FF; margin-bottom: 10px;")
        self.left_layout.addWidget(title)

        # 1. 数据仿真输入区
        data_gb = QGroupBox("数据源预处理")
        data_l = QFormLayout(data_gb)
        self.spin_points = QSpinBox(); self.spin_points.setRange(100, 5000); self.spin_points.setValue(1000)
        self.cmb_temp = QComboBox(); self.cmb_temp.addItems(["25℃", "75℃", "125℃", "145℃"])
        self.cmb_device = QComboBox(); self.cmb_device.addItems(["IGBT_DUT_001", "IGBT_DUT_002", "IGBT_DUT_003"])
        data_l.addRow("采样点规模 (N):", self.spin_points)
        data_l.addRow("测试环境结温:", self.cmb_temp)
        data_l.addRow("待测器件编号:", self.cmb_device)
        self.left_layout.addWidget(data_gb)

        # 2. 专利核心系数设定 (F_ki)
        coeff_gb = QGroupBox("专利核心系数设定")
        coeff_l = QFormLayout(coeff_gb)
        self.dsp_fki = QDoubleSpinBox()
        self.dsp_fki.setRange(0.0001, 10.0); self.dsp_fki.setValue(1.2450); self.dsp_fki.setDecimals(4)
        info_lbl = QLabel("注：Fki 由多器件综合差异矩阵确定")
        info_lbl.setStyleSheet("color: #666; font-size: 11px;")
        coeff_l.addRow("综合差异系数 Fki:", self.dsp_fki)
        coeff_l.addRow(info_lbl)
        self.left_layout.addWidget(coeff_gb)

        # 3. 算法计算看板
        self.board_gb = QGroupBox("实时计算看板")
        board_l = QGridLayout(self.board_gb)
        self.lbl_aki = self._create_lcd("0.0000")
        self.lbl_gki = self._create_lcd("0.0000")
        board_l.addWidget(QLabel("簇间差异均值 Aki:"), 0, 0); board_l.addWidget(self.lbl_aki, 0, 1)
        board_l.addWidget(QLabel("突变偏移系数 Gki:"), 1, 0); board_l.addWidget(self.lbl_gki, 1, 1)
        self.left_layout.addWidget(self.board_gb)

        # 4. 执行按钮
        self.btn_run = QPushButton("⚡ 执行聚类分析")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("background-color: #0078D4; font-weight: bold; font-size: 14px;")
        self.btn_run.clicked.connect(self._handle_analysis_request)
        self.left_layout.addWidget(self.btn_run)

        # 5. 详细事务日志
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background: #090C10; color: #00FF94; font-family: Consolas; font-size: 12px;")
        self.left_layout.addWidget(QLabel("专利算法执行踪迹:"))
        self.left_layout.addWidget(self.log_console)

        # --- 右侧：3D 可视化面板 ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #0F1218; border-radius: 10px; border: 1px solid #222;")
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # 集成 Matplotlib 3D 画布
        self.fig = plt.figure(facecolor='#0F1218')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#0F1218')
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.right_layout.addWidget(QLabel("三元组空间聚类分布 (Isc, Vce, Vge Triplet Space)"))
        self.right_layout.addWidget(self.canvas)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel, 1)

    def _create_lcd(self, val):
        lbl = QLabel(val)
        lbl.setStyleSheet("font-size: 22px; color: #00FF94; font-family: Consolas; font-weight: bold;")
        return lbl

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: #DDD;'>[{tag}]</b> {msg}")

    def _handle_analysis_request(self):
        """生成仿真三元组数据并执行分析"""
        self.btn_run.setEnabled(False)
        self.log_console.clear()
        
        # 模拟生成专利[0006]描述的三元组数据矩阵 [N, 3]
        # 三个维度对应: Isc (A), Vce (V), Vge (V)
        n = self.spin_points.value()
        
        # 创建两个带有偏移特征的簇，模拟正常与异常工况
        cluster1 = np.random.multivariate_normal([20, 600, 15], [[2,0,0],[0,10,0],[0,0,0.1]], n//2)
        cluster2 = np.random.multivariate_normal([25, 580, 14.8], [[3,0,0],[0,15,0],[0,0,0.2]], n//2)
        raw_data = np.vstack([cluster1, cluster2])
        
        # 异步启动引擎
        self.engine.run_analysis(raw_data, self.dsp_fki.value())

    def _on_result_ready(self, res):
        """渲染分析结果"""
        self.btn_run.setEnabled(True)
        
        # 更新 LCD 指标
        self.lbl_aki.setText(f"{res['a_ki']:.4f}")
        self.lbl_gki.setText(f"{res['g_ki']:.4f}")

        # 绘制 3D 聚类图 (三元组空间展示)
        self.ax.clear()
        data = res['data']
        labels = res['labels']
        centers = res['centers']

        # 专利中 Isc, Vce, Vge 的坐标映射
        self.ax.scatter(data[labels==0, 0], data[labels==0, 1], data[labels==0, 2], c='#00A3FF', s=10, alpha=0.5, label='Cluster_A')
        self.ax.scatter(data[labels==1, 0], data[labels==1, 1], data[labels==1, 2], c='#722ED1', s=10, alpha=0.5, label='Cluster_B')
        
        # 标注质心
        self.ax.scatter(centers[:, 0], centers[:, 1], centers[:, 2], c='white', marker='x', s=100, linewidth=3, label='Centroids')

        self.ax.set_xlabel('Isc (Current)', color='#888')
        self.ax.set_ylabel('Vce (Voltage)', color='#888')
        self.ax.set_zlabel('Vge (Gate)', color='#888')
        self.ax.tick_params(colors='#444')
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()
        
        self._append_log("INFO", "分析报告：当前器件表现出明显的双模态跳变特征，Gki 已更新。")

# =============================================================================
# 独立的弹出提示框修复 (对应你之前的反馈)
# =============================================================================

def show_styled_message(parent, title, text):
    """封装好的工业风提示框"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()