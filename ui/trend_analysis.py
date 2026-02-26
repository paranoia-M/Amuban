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
from scipy import stats

# =============================================================================
# 1. 专利核心数学引擎 (Mann-Kendall Trend Engine)
# =============================================================================

class MannKendallEngine(QThread):
    """
    底层统计学引擎：实现严谨的 Mann-Kendall 趋势检验算法
    专利依据：[0105]-[0108] 评估 IGBT 随温度变化的短路电流趋势显著性
    """
    progress_sig = pyqtSignal(int, str)
    log_sig = pyqtSignal(str, str)
    result_sig = pyqtSignal(dict)

    def __init__(self, num_devices, temp_start, temp_end, temp_step):
        super().__init__()
        self.num_devices = num_devices
        self.temps = np.arange(temp_start, temp_end + 1, temp_step)
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        self.log_sig.emit("SYS", ">>> 启动 Mann-Kendall 趋势显著性检验引擎...")
        time.sleep(0.5)
        
        n_temps = len(self.temps)
        device_data = {}
        results = {}

        self.log_sig.emit("DATA", f"构建 {self.num_devices} 个器件的全温度梯度 (Total: {n_temps} pts) 数据模型...")

        # 1. 仿真生成器件在不同结温下的平均短路电流 (模拟专利[0101]描述的缺陷表现)
        for i in range(self.num_devices):
            if self._abort: return
            
            # 设定 20% 的概率为"缺陷器件" (随温度升高，电流无显著增大)
            is_defective = random.random() < 0.2
            
            base_current = random.uniform(15.0, 20.0)
            noise = np.random.normal(0, 0.3, n_temps)
            
            if is_defective:
                # 缺陷器件：趋势平缓，甚至产生衰退
                trend_coef = random.uniform(-0.02, 0.05)
                currents = base_current + trend_coef * (self.temps - self.temps[0]) + noise
                self.log_sig.emit("WARN", f"发现潜在缺陷器件特征 -> Device_{i:02d}")
            else:
                # 正常器件：温度越高，短路电流显著增大 (正相关)
                trend_coef = random.uniform(0.15, 0.35)
                currents = base_current + trend_coef * (self.temps - self.temps[0]) + noise
            
            device_data[f"DEV_{i:02d}"] = {
                'currents': currents,
                'is_defective': is_defective
            }

        # 2. 执行 Mann-Kendall 算法解算
        total_steps = self.num_devices
        for idx, (dev_id, data) in enumerate(device_data.items()):
            if self._abort: return
            
            curr_seq = data['currents']
            mean_curr = np.mean(curr_seq)
            
            # (1) 手写计算统计量 S
            n = len(curr_seq)
            S = 0
            for k in range(n - 1):
                for j in range(k + 1, n):
                    S += np.sign(curr_seq[j] - curr_seq[k])
                    
            # (2) 计算方差 Var(S) (包含结值 Ties 校正)
            unique_x, counts = np.unique(curr_seq, return_counts=True)
            ties_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
            var_s = (n * (n - 1) * (2 * n + 5) - ties_term) / 18.0
            
            # (3) 计算标准化检验统计量 Z (专利中的"趋势显著特征")
            if S > 0:
                Z = (S - 1) / np.sqrt(var_s)
            elif S < 0:
                Z = (S + 1) / np.sqrt(var_s)
            else:
                Z = 0
                
            abs_Z = abs(Z)
            
            # (4) 计算最终趋势显著性 Ti = Mean * |Z| (专利[0107])
            T_i = mean_curr * abs_Z
            
            # 记录计算链路供追溯
            self.log_sig.emit("MATH", f"[{dev_id}] Mean={mean_curr:.2f}, S={S}, Var(S)={var_s:.2f}, |Z|={abs_Z:.3f} => T_i={T_i:.2f}")
            
            results[dev_id] = {
                'currents': curr_seq,
                'mean': mean_curr,
                'S': S,
                'Z': Z,
                'abs_Z': abs_Z,
                'T_i': T_i,
                'status': 'HEALTHY' if abs_Z > 1.96 else 'DEGRADED' # Z > 1.96 (95% 置信度)
            }
            
            progress = int(((idx + 1) / total_steps) * 100)
            self.progress_sig.emit(progress, f"正在解算 {dev_id} 的趋势特征矩阵...")
            time.sleep(0.05) # 保证 UI 渲染刷新

        self.progress_sig.emit(100, "Mann-Kendall 趋势显著性检验分析完成。")
        
        # 封装所有数据返回
        payload = {
            'temps': self.temps,
            'results': results
        }
        self.result_sig.emit(payload)


# =============================================================================
# 2. 深度交互图表组件 (Interactive Visualizer)
# =============================================================================

class TrendVisualizerCanvas(QWidget):
    """
    联动式双图层可视化引擎
    支持全局趋势分布预览 + 选中行特征曲线高亮
    """
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.fig = Figure(facecolor='#0F1218', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        # 划分子图：上半部分显示群集曲线，下半部分显示 Ti 分布
        self.ax_curve = self.fig.add_subplot(211)
        self.ax_bar = self.fig.add_subplot(212)
        self._init_style()

    def _init_style(self):
        for ax in [self.ax_curve, self.ax_bar]:
            ax.set_facecolor('#0F1218')
            ax.tick_params(colors='#888', labelsize=9)
            for spine in ax.spines.values():
                spine.set_color('#333')
        
        self.ax_curve.set_title("Temperature vs. Short-Circuit Current (Global Cluster)", color='white', fontsize=11)
        self.ax_curve.set_xlabel("Junction Temperature (°C)", color='#666', fontsize=9)
        self.ax_curve.set_ylabel("Average Isc (A)", color='#666', fontsize=9)
        self.ax_curve.grid(True, linestyle='--', color='#222')
        
        self.ax_bar.set_title("Trend Significance Index (T_i) Distribution", color='white', fontsize=11)
        self.ax_bar.set_ylabel("T_i Score", color='#666', fontsize=9)
        
        self.fig.tight_layout()

    def render_global(self, temps, results):
        """渲染所有设备的初始状态"""
        self.ax_curve.clear(); self.ax_bar.clear()
        self._init_style()
        self.temps = temps
        self.results = results
        
        # 1. 绘制所有曲线 (低透明度)
        for dev_id, data in results.items():
            color = '#00FF94' if data['status'] == 'HEALTHY' else '#FF4D4D'
            self.ax_curve.plot(temps, data['currents'], color=color, alpha=0.3, linewidth=1.5)
            
        # 2. 绘制 Ti 柱状图
        dev_ids = list(results.keys())
        ti_vals = [r['T_i'] for r in results.values()]
        colors = ['#00A3FF' if r['status'] == 'HEALTHY' else '#FF3E3E' for r in results.values()]
        
        self.bars = self.ax_bar.bar(dev_ids, ti_vals, color=colors, edgecolor='#111')
        self.ax_bar.set_xticks(range(len(dev_ids)))
        self.ax_bar.set_xticklabels(dev_ids, rotation=45, ha='right')
        
        # 添加评估阈值横线
        mean_ti = np.mean(ti_vals)
        self.ax_bar.axhline(mean_ti, color='#FFCC00', linestyle='-.', linewidth=1.5, label=f'Avg Threshold ({mean_ti:.1f})')
        self.ax_bar.legend(facecolor='#151921', edgecolor='#333', labelcolor='white')
        
        self.canvas.draw()

    def highlight_device(self, target_dev_id):
        """交互核心：当表格选中时，高亮显示目标设备的曲线"""
        if not hasattr(self, 'results'): return
        
        self.ax_curve.clear()
        self._init_style()
        
        # 重新绘制背景曲线
        for dev_id, data in self.results.items():
            if dev_id != target_dev_id:
                self.ax_curve.plot(self.temps, data['currents'], color='#333', alpha=0.5, linewidth=1)
                
        # 绘制高亮曲线
        target_data = self.results[target_dev_id]
        hl_color = '#00FF94' if target_data['status'] == 'HEALTHY' else '#FF4D4D'
        self.ax_curve.plot(self.temps, target_data['currents'], color=hl_color, alpha=1.0, linewidth=3, marker='o', markersize=5, label=f"{target_dev_id} Trend")
        
        # 拟合高亮曲线的线性回归线(展示视觉趋势)
        slope, intercept, r, p, err = stats.linregress(self.temps, target_data['currents'])
        trend_line = intercept + slope * self.temps
        self.ax_curve.plot(self.temps, trend_line, color='#FFCC00', linestyle='-.', linewidth=2, label=f"Linear Fit (Slope={slope:.3f})")
        
        self.ax_curve.legend(facecolor='#151921', edgecolor='#333', labelcolor='white')
        
        # 高亮底部的柱子
        dev_ids = list(self.results.keys())
        for i, bar in enumerate(self.bars):
            if dev_ids[i] == target_dev_id:
                bar.set_edgecolor('white')
                bar.set_linewidth(2)
                bar.set_alpha(1.0)
            else:
                bar.set_edgecolor('#111')
                bar.set_linewidth(1)
                bar.set_alpha(0.3)
                
        self.canvas.draw()

# =============================================================================
# 3. 主界面整合 (Main Page Component)
# =============================================================================

class TrendSignificancePage(QWidget):
    """
    第八个菜单：趋势显著性检测
    涵盖复杂的表格-图表联动，统计学引擎及专利审计记录
    """
    def __init__(self):
        super().__init__()
        self.engine = None
        self.cached_results = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ---------------------------------------------------------
        # 左侧：核心管控面板 (配置、表格、日志) (500px)
        # ---------------------------------------------------------
        self.left_panel = QFrame()
        self.left_panel.setFixedWidth(500)
        self.left_panel.setStyleSheet("background-color: #151921; border-radius: 8px; border: 1px solid #2A2F3A;")
        self.left_vbox = QVBoxLayout(self.left_panel)

        header = QLabel("趋势显著性检测系统")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #00A3FF; border: none;")
        self.left_vbox.addWidget(header)

        # 1. 算法边界条件配置
        config_gb = QGroupBox("Mann-Kendall 算法边界")
        config_l = QGridLayout(config_gb)
        
        self.sp_dev_count = QSpinBox(); self.sp_dev_count.setRange(5, 50); self.sp_dev_count.setValue(15)
        self.sp_t_start = QSpinBox(); self.sp_t_start.setRange(25, 100); self.sp_t_start.setValue(25)
        self.sp_t_end = QSpinBox(); self.sp_t_end.setRange(100, 200); self.sp_t_end.setValue(145)
        self.sp_t_step = QSpinBox(); self.sp_t_step.setRange(5, 50); self.sp_t_step.setValue(10)
        
        config_l.addWidget(QLabel("批次样本数量:"), 0, 0); config_l.addWidget(self.sp_dev_count, 0, 1)
        config_l.addWidget(QLabel("起始结温 (℃):"), 1, 0); config_l.addWidget(self.sp_t_start, 1, 1)
        config_l.addWidget(QLabel("终止结温 (℃):"), 0, 2); config_l.addWidget(self.sp_t_end, 0, 3)
        config_l.addWidget(QLabel("结温步进 (ΔT):"), 1, 2); config_l.addWidget(self.sp_t_step, 1, 3)
        self.left_vbox.addWidget(config_gb)

        # 2. 交互式数据透视表
        table_lbl = QLabel("全样本 MK 统计量透视账本 (点击单行可交叉高亮右侧图表):")
        table_lbl.setStyleSheet("color: #8B949E; margin-top: 10px;")
        self.left_vbox.addWidget(table_lbl)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["设备 ID", "Mean(Isc)", "Z-Score", "T_i 指数", "评估结论"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget { background: #0D1117; color: #EEE; gridline-color: #30363D; border: 1px solid #30363D; }
            QTableWidget::item:selected { background-color: #004578; color: white; }
        """)
        # 绑定点击联动事件
        self.table.itemSelectionChanged.connect(self._handle_table_selection)
        self.left_vbox.addWidget(self.table)

        # 3. 统计审计终端
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(120)
        self.console.setStyleSheet("background: #05070A; color: #00FF94; font-family: 'Consolas'; font-size: 11px; border: 1px solid #222;")
        self.left_vbox.addWidget(QLabel("数学解算链路审计:"))
        self.left_vbox.addWidget(self.console)

        # 4. 执行控制区
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10); self.pbar.setTextVisible(False)
        self.left_vbox.addWidget(self.pbar)

        self.btn_run = QPushButton("⚡ 执行全批次 Mann-Kendall 趋势解算")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #0078D4; color: white; font-weight: bold; font-size: 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #0082CC; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        self.btn_run.clicked.connect(self._execute_analysis)
        self.left_vbox.addWidget(self.btn_run)

        # ---------------------------------------------------------
        # 右侧：交叉过滤可视化 (Flexible)
        # ---------------------------------------------------------
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #0F1218; border-radius: 10px; border: 1px solid #333;")
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.canvas = TrendVisualizerCanvas()
        self.right_layout.addWidget(self.canvas)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel, 1)

    # --- 核心交互逻辑与事件响应 ---

    def _execute_analysis(self):
        """触发多线程 MK 核心算法"""
        self.btn_run.setEnabled(False)
        self.console.clear()
        self.table.setRowCount(0)
        self.cached_results = None
        
        count = self.sp_dev_count.value()
        t_start = self.sp_t_start.value()
        t_end = self.sp_t_end.value()
        step = self.sp_t_step.value()

        if t_end <= t_start or step <= 0:
            QMessageBox.warning(self, "参数错误", "温度区间设置无效，请检查起始与终止温度。")
            self.btn_run.setEnabled(True)
            return

        self.engine = MannKendallEngine(count, t_start, t_end, step)
        self.engine.log_sig.connect(self._append_log)
        self.engine.progress_sig.connect(self._update_progress)
        self.engine.result_sig.connect(self._on_analysis_complete)
        self.engine.start()

    def _append_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#00A3FF"
        if tag == "WARN": color = "#FF8C00"
        elif tag == "MATH": color = "#CC00FF"
        self.console.append(f"<span style='color: #666;'>[{ts}]</span> <b style='color: {color};'>[{tag}]</b> {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _update_progress(self, val, msg):
        self.pbar.setValue(val)
        self.btn_run.setText(f"运算中: {msg}")

    def _on_analysis_complete(self, payload):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("⚡ 重新解算全批次数据")
        
        temps = payload['temps']
        results = payload['results']
        self.cached_results = results
        
        # 1. 填充多维表格
        self.table.blockSignals(True)
        self.table.setRowCount(len(results))
        for i, (dev_id, data) in enumerate(results.items()):
            self.table.setItem(i, 0, QTableWidgetItem(dev_id))
            self.table.setItem(i, 1, QTableWidgetItem(f"{data['mean']:.2f} A"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{data['Z']:.3f}"))
            
            # T_i 列加粗并着色
            ti_item = QTableWidgetItem(f"{data['T_i']:.2f}")
            font = QFont(); font.setBold(True); ti_item.setFont(font)
            if data['status'] == 'HEALTHY':
                ti_item.setForeground(QBrush(QColor('#00FF94')))
            else:
                ti_item.setForeground(QBrush(QColor('#FF4D4D')))
            self.table.setItem(i, 3, ti_item)
            
            self.table.setItem(i, 4, QTableWidgetItem(data['status']))
            
        self.table.blockSignals(False)
        
        # 2. 渲染初始全局图表
        self.canvas.render_global(temps, results)

    def _handle_table_selection(self):
        """交互：当用户在表格中选择一行时，右侧图表进行对应的联动高亮"""
        if not self.cached_results: return
        selected_items = self.table.selectedItems()
        if not selected_items: return
        
        row = selected_items[0].row()
        target_dev_id = self.table.item(row, 0).text()
        
        self._append_log("UI", f"交叉锁定目标：正在分析器件 {target_dev_id} 的衰退轨迹...")
        self.canvas.highlight_device(target_dev_id)