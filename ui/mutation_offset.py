import sys
import time
import random
import numpy as np
from datetime import datetime

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.colors as mcolors

# =============================================================================
# 1. 专利级核心算法引擎 (Patent Math Engine)
# =============================================================================

class DTWComputeEngine(QThread):
    """
    底层数学引擎：实现带 Sakoe-Chiba 约束窗的动态时间规整 (DTW)
    专利依据：[0070] 使用 DTW 距离衡量不同器件序列差异
    """
    progress_sig = pyqtSignal(int, str)
    log_sig = pyqtSignal(str, str)
    result_sig = pyqtSignal(dict)

    def __init__(self, num_devices, seq_length, window_size, aki_base):
        super().__init__()
        self.num_devices = num_devices
        self.seq_length = seq_length
        self.window = window_size
        self.aki_base = aki_base
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        self.log_sig.emit("SYS", ">>> 启动 DTW 动态时间规整核心解算引擎...")
        time.sleep(0.5)

        # 1. 模拟生成 N 个 IGBT 器件的短路电流序列 (包含相位偏移和幅值畸变)
        sequences =[]
        t = np.linspace(0, 10, self.seq_length)
        self.log_sig.emit("DATA", f"正在生成 {self.num_devices} 组器件特征序列矩阵...")
        for i in range(self.num_devices):
            phase_shift = random.uniform(-0.5, 0.5)
            amp_var = random.uniform(0.9, 1.1)
            # 基础波形：阻尼振荡
            seq = 20 * amp_var * np.sin(2 * np.pi * 1.5 * (t + phase_shift)) * np.exp(-0.3 * t)
            seq += np.random.normal(0, 0.2, self.seq_length)
            sequences.append(seq)
            
        # 2. 计算 N x N 的 DTW 距离矩阵
        dist_matrix = np.zeros((self.num_devices, self.num_devices))
        paths = {} # 存储规整回溯路径
        
        total_calcs = (self.num_devices * (self.num_devices - 1)) // 2
        calc_cnt = 0

        for i in range(self.num_devices):
            for j in range(i+1, self.num_devices):
                if self._abort: return
                
                # 执行 DTW 核心算法
                dist, path = self._compute_dtw(sequences[i], sequences[j], self.window)
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist
                paths[f"{i}-{j}"] = path
                
                calc_cnt += 1
                progress = int((calc_cnt / total_calcs) * 70)
                self.progress_sig.emit(progress, f"正在对齐序列 {i} 与 {j} ...")
                self.log_sig.emit("DTW", f"DTW(Device_{i}, Device_{j}) = {dist:.4f}")

        # 3. 计算综合差异系数 F_ki (专利[0017])
        self.progress_sig.emit(80, "正在计算多器件综合差异系数 F_ki ...")
        f_ki_array = np.zeros(self.num_devices)
        for i in range(self.num_devices):
            # 排除自身距离(0)求均值
            f_ki_array[i] = np.sum(dist_matrix[i]) / (self.num_devices - 1)
            self.log_sig.emit("MATH", f"Device_{i} 综合差异 F_ki = {f_ki_array[i]:.4f}")

        # 4. 计算最终突变偏移系数 G_ki (专利[0015])
        self.progress_sig.emit(95, "解算最终突变偏移系数 G_ki ...")
        g_ki_array = f_ki_array * self.aki_base
        
        for i in range(self.num_devices):
            self.log_sig.emit("SUCCESS", f"Device_{i} 突变偏移系数 G_ki = {g_ki_array[i]:.6f}")

        self.progress_sig.emit(100, "DTW 全序列对齐与解算完成。")
        
        # 打包结果返回 UI
        self.result_sig.emit({
            'sequences': sequences,
            'dist_matrix': dist_matrix,
            'paths': paths,
            'f_ki': f_ki_array,
            'g_ki': g_ki_array
        })

    def _compute_dtw(self, s, t, window):
        """
        手写底层 DTW 动态时间规整算法 (带 Sakoe-Chiba 约束窗)
        实现精准的序列弹性对齐
        """
        n, m = len(s), len(t)
        w = np.max([window, abs(n - m)])
        
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0
        
        # 填充成本矩阵
        for i in range(1, n + 1):
            for j in range(max(1, i - w), min(m, i + w) + 1):
                cost = abs(s[i - 1] - t[j - 1])
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i - 1, j],    # 插入
                    dtw_matrix[i, j - 1],    # 删除
                    dtw_matrix[i - 1, j - 1] # 匹配
                )
                
        # 回溯寻找最优规整路径 (Warping Path Traceback)
        path =[]
        i, j = n, m
        while i > 0 and j > 0:
            path.append((i - 1, j - 1))
            min_val = min(dtw_matrix[i - 1, j - 1], dtw_matrix[i - 1, j], dtw_matrix[i, j - 1])
            if min_val == dtw_matrix[i - 1, j - 1]:
                i -= 1; j -= 1
            elif min_val == dtw_matrix[i - 1, j]:
                i -= 1
            else:
                j -= 1
        path.reverse()
        return dtw_matrix[n, m], path

# =============================================================================
# 2. 交互式多维可视化画布 (Data Visualization Canvas)
# =============================================================================

class DTWVisualizerCanvas(QWidget):
    """集成 3 种子图：DTW 对齐路径图、距离热力图、G_ki 分布柱状图"""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.fig = Figure(facecolor='#0F1218', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        # 创建 3 个极具专业感的子图
        self.ax_align = self.fig.add_subplot(221)
        self.ax_heat = self.fig.add_subplot(222)
        self.ax_bar = self.fig.add_subplot(212)
        self._init_axes_style()

    def _init_axes_style(self):
        for ax in[self.ax_align, self.ax_heat, self.ax_bar]:
            ax.set_facecolor('#0F1218')
            ax.tick_params(colors='#888', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#333')
        self.fig.tight_layout()

    def render_results(self, data, dev_a, dev_b):
        self.ax_align.clear(); self.ax_heat.clear(); self.ax_bar.clear()
        self._init_axes_style()
        
        sequences = data['sequences']
        dist_matrix = data['dist_matrix']
        paths = data['paths']
        g_ki = data['g_ki']
        
        # --- 1. 渲染 DTW 规整对齐连线图 (Warping Path) ---
        seq_a = sequences[dev_a]
        seq_b = sequences[dev_b]
        # 获取预计算的路径，注意字典键的顺序
        path_key = f"{dev_a}-{dev_b}" if f"{dev_a}-{dev_b}" in paths else f"{dev_b}-{dev_a}"
        path = paths.get(path_key,[])
        
        # 将序列 B 在视觉上向下偏移以便观察连线
        offset = np.max(seq_a) - np.min(seq_b) + 5
        self.ax_align.plot(seq_a, color='#00FF94', label=f'Device {dev_a}')
        self.ax_align.plot(seq_b - offset, color='#00A3FF', label=f'Device {dev_b} (Offset)')
        
        # 绘制浅色规整连线 (抽样绘制防密集)
        if path:
            for (idx_a, idx_b) in path[::max(1, len(path)//50)]:
                self.ax_align.plot([idx_a, idx_b], [seq_a[idx_a], seq_b[idx_b] - offset], 
                                   color='#FF8C00', alpha=0.3, linewidth=0.8)
                
        self.ax_align.set_title(f"DTW Sequence Alignment (Dev_{dev_a} vs Dev_{dev_b})", color='white', fontsize=10)
        self.ax_align.legend(facecolor='#151921', edgecolor='#333', labelcolor='white', fontsize=8)

        # --- 2. 渲染差异距离矩阵热力图 (Heatmap) ---
        cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["#0B0E14", "#722ED1", "#FF3E3E"])
        im = self.ax_heat.imshow(dist_matrix, cmap=cmap, aspect='auto')
        
        # 标注热力图数值
        for i in range(len(dist_matrix)):
            for j in range(len(dist_matrix)):
                val = f"{dist_matrix[i, j]:.1f}" if i != j else "0"
                self.ax_heat.text(j, i, val, ha="center", va="center", color="w", fontsize=7)
                
        self.ax_heat.set_title("N x N DTW Distance Matrix", color='white', fontsize=10)
        self.ax_heat.set_xticks(range(len(dist_matrix)))
        self.ax_heat.set_yticks(range(len(dist_matrix)))
        self.ax_heat.set_xticklabels([f"D{i}" for i in range(len(dist_matrix))])
        self.ax_heat.set_yticklabels([f"D{i}" for i in range(len(dist_matrix))])

        # --- 3. 渲染最终突变偏移系数 G_ki 柱状图 ---
        x_pos = np.arange(len(g_ki))
        bars = self.ax_bar.bar(x_pos, g_ki, color='#00A3FF', edgecolor='#0078D4')
        self.ax_bar.set_title(f"Mutation Offset Coefficient (G_ki) Distribution", color='white', fontsize=10)
        self.ax_bar.set_xticks(x_pos)
        self.ax_bar.set_xticklabels([f"Device_{i}" for i in range(len(g_ki))])
        
        # 顶部标注数值
        for bar in bars:
            yval = bar.get_height()
            self.ax_bar.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.3f}', 
                             va='bottom', ha='center', color='#00FF94', fontsize=9)
            
        self.fig.tight_layout()
        self.canvas.draw()

# =============================================================================
# 3. 突变偏移解算主页面 (Main UI Page)
# =============================================================================

class MutationOffsetPage(QWidget):
    """
    第五个菜单：突变偏移解算 (基于 DTW 算法)
    实现极其复杂的逻辑计算与深度可视化交互
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self.result_data = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ---------------------------------------------------------
        # 左侧：参数配置与审计终端 (420px)
        # ---------------------------------------------------------
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(420)
        self.left_panel.setStyleSheet("background-color: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        self.left_layout = QVBoxLayout(self.left_panel)

        title = QLabel("突变偏移系数矩阵解算")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00A3FF; border: none; padding-bottom: 5px;")
        self.left_layout.addWidget(title)

        # A. 算法超参数配置
        algo_gb = QGroupBox("DTW 算法引擎参数")
        algo_l = QFormLayout(algo_gb)
        
        self.sp_devices = QSpinBox(); self.sp_devices.setRange(3, 10); self.sp_devices.setValue(5)
        self.sp_length = QSpinBox(); self.sp_length.setRange(50, 500); self.sp_length.setValue(100)
        self.sp_window = QSpinBox(); self.sp_window.setRange(5, 100); self.sp_window.setValue(20)
        self.dsp_aki = QDoubleSpinBox(); self.dsp_aki.setRange(0.01, 10.0); self.dsp_aki.setValue(1.542); self.dsp_aki.setDecimals(3)
        
        algo_l.addRow("待测同批次器件数量 (N):", self.sp_devices)
        algo_l.addRow("单序列采样点长度 (L):", self.sp_length)
        algo_l.addRow("Sakoe-Chiba 约束窗宽:", self.sp_window)
        algo_l.addRow("继承簇间差异均值 (Aki):", self.dsp_aki)
        self.left_layout.addWidget(algo_gb)

        # B. 交互式可视化选择器
        view_gb = QGroupBox("序列对齐观测通道")
        view_l = QFormLayout(view_gb)
        self.cmb_dev_a = QComboBox()
        self.cmb_dev_b = QComboBox()
        self._update_comboboxes(5)
        
        self.cmb_dev_a.currentIndexChanged.connect(self._refresh_plot)
        self.cmb_dev_b.currentIndexChanged.connect(self._refresh_plot)
        
        view_l.addRow("基准序列 (Reference):", self.cmb_dev_a)
        view_l.addRow("对比序列 (Query):", self.cmb_dev_b)
        self.left_layout.addWidget(view_gb)

        # C. 数据表格展示 (专利要求明确的差异矩阵)
        self.left_layout.addWidget(QLabel("综合差异系数 F_ki 矩阵账本:"), alignment=Qt.AlignmentFlag.AlignBottom)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["器件 ID", "DTW 均距", "F_ki 综合系数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background: #0D1117; color: #EEE; font-family: Consolas;")
        self.table.setFixedHeight(150)
        self.left_layout.addWidget(self.table)

        # D. 执行终端与按钮
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10); self.pbar.setTextVisible(False)
        self.left_layout.addWidget(self.pbar)

        self.btn_run = QPushButton("⚡ 执行多维 DTW 序列规整分析")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { background: #0078D4; color: white; font-weight: bold; font-size: 15px; border-radius: 4px; }
            QPushButton:hover { background: #0082CC; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.btn_run.clicked.connect(self._execute_analysis)
        self.left_layout.addWidget(self.btn_run)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #05070A; color: #00FF94; font-family: 'Consolas'; font-size: 11px; border: 1px solid #222;")
        self.left_layout.addWidget(QLabel("数学引擎解算终端:"))
        self.left_layout.addWidget(self.console)

        # ---------------------------------------------------------
        # 右侧：可视化画布 (Flexible Stretch)
        # ---------------------------------------------------------
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #0F1218; border-radius: 10px; border: 1px solid #333;")
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.canvas = DTWVisualizerCanvas()
        self.right_layout.addWidget(self.canvas)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel, 1)

    def _update_comboboxes(self, n):
        self.cmb_dev_a.blockSignals(True)
        self.cmb_dev_b.blockSignals(True)
        self.cmb_dev_a.clear(); self.cmb_dev_b.clear()
        items = [f"Device_{i}" for i in range(n)]
        self.cmb_dev_a.addItems(items)
        self.cmb_dev_b.addItems(items)
        if n > 1: self.cmb_dev_b.setCurrentIndex(1)
        self.cmb_dev_a.blockSignals(False)
        self.cmb_dev_b.blockSignals(False)

    def _execute_analysis(self):
        n = self.sp_devices.value()
        self._update_comboboxes(n)
        
        self.btn_run.setEnabled(False)
        self.console.clear()
        self.table.setRowCount(0)
        
        # 启动多线程 DTW 引擎
        self.engine = DTWComputeEngine(
            n, self.sp_length.value(), self.sp_window.value(), self.dsp_aki.value()
        )
        self.engine.log_sig.connect(self._append_log)
        self.engine.progress_sig.connect(self._update_progress)
        self.engine.result_sig.connect(self._on_analysis_complete)
        self.engine.start()

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: #00A3FF;'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _update_progress(self, val, status):
        self.pbar.setValue(val)
        self.btn_run.setText(f"运算中: {status}")

    def _on_analysis_complete(self, data):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("⚡ 重新执行多维 DTW 序列规整分析")
        self.result_data = data
        
        # 1. 填充结果数据表
        n = self.sp_devices.value()
        self.table.setRowCount(n)
        for i in range(n):
            self.table.setItem(i, 0, QTableWidgetItem(f"Device_{i}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{np.sum(data['dist_matrix'][i])/(n-1):.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{data['f_ki'][i]:.4f}"))
            
        # 2. 触发可视化绘图
        self._refresh_plot()

    def _refresh_plot(self):
        if not self.result_data: return
        dev_a = self.cmb_dev_a.currentIndex()
        dev_b = self.cmb_dev_b.currentIndex()
        if dev_a == -1 or dev_b == -1: return
        
        self.canvas.render_results(self.result_data, dev_a, dev_b)