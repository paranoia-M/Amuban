import sys
import sqlite3
import random
import csv
import numpy as np
from datetime import datetime, timedelta

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# =============================================================================
# 1. 核心数据库驱动引擎 (SQLite ORM Engine)
# =============================================================================

class DatabaseManager:
    """工业级 SQLite 持久化引擎：管理专利中所有核心特征数据的存取"""
    def __init__(self, db_path="igbt_patent_records.sqlite"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS igbt_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_date TEXT,
                    batch_id TEXT,
                    device_id TEXT,
                    temperature REAL,
                    g_ki REAL,
                    m_ki REAL,
                    p_ki REAL,
                    t_i REAL,
                    u_i REAL,
                    w_i REAL,
                    status TEXT
                )
            """)
            conn.commit()
            
            # 自动注水：如果数据库为空，生成 1000 条仿真专利测试数据
            cursor.execute("SELECT COUNT(*) FROM igbt_metrics")
            if cursor.fetchone()[0] == 0:
                self._generate_mock_data(cursor)
                conn.commit()

    def _generate_mock_data(self, cursor):
        batches =[f"B-{202500+i}" for i in range(1, 6)]
        temps =[25.0, 75.0, 125.0, 145.0]
        
        data_to_insert =[]
        for batch in batches:
            base_date = datetime.now() - timedelta(days=random.randint(1, 100))
            for dev in range(1, 21):
                dev_id = f"D-{dev:03d}"
                is_faulty = random.random() < 0.15 # 15% 故障率
                
                for t in temps:
                    # 模拟专利算法生成的系列系数
                    g_ki = random.uniform(1.2, 2.5) if not is_faulty else random.uniform(2.5, 5.0)
                    m_ki = random.uniform(0.1, 0.5) if not is_faulty else random.uniform(0.6, 2.0)
                    p_ki = g_ki * (random.uniform(2.0, 3.0) + m_ki)
                    t_i = random.uniform(0.8, 1.2) if not is_faulty else random.uniform(0.2, 0.6)
                    u_i = random.uniform(0.85, 0.99) if not is_faulty else random.uniform(0.3, 0.7)
                    w_i = t_i * u_i
                    status = "PASS" if w_i >= 0.75 else "FAIL"
                    
                    date_str = (base_date + timedelta(hours=random.randint(1, 12))).strftime("%Y-%m-%d %H:%M:%S")
                    data_to_insert.append((date_str, batch, dev_id, t, g_ki, m_ki, p_ki, t_i, u_i, w_i, status))
                    
        cursor.executemany("""
            INSERT INTO igbt_metrics 
            (test_date, batch_id, device_id, temperature, g_ki, m_ki, p_ki, t_i, u_i, w_i, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)

    def execute_query(self, query, params=()):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description] if cursor.description else[]
                return True, columns, cursor.fetchall()
        except Exception as e:
            return False,[], str(e)

# =============================================================================
# 2. MVC 架构：底层数据模型与高级渲染委托 (Data Model & Delegates)
# =============================================================================

class IGBTTableModel(QAbstractTableModel):
    """纯手写的高性能数据模型：支持百万级数据流畅滑动与动态排序"""
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers

    def data(self, index, role):
        if not index.isValid(): return None
        value = self._data[index.row()][index.column()]
        
        # 核心数据展示逻辑
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, float): return f"{value:.3f}"
            return str(value)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.UserRole:
            # 供自定义 Delegate 使用的原始数值
            return value
        return None

    def rowCount(self, index=QModelIndex()): return len(self._data)
    def columnCount(self, index=QModelIndex()): return len(self._headers)
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        self._data.sort(key=lambda x: x[column], reverse=(order == Qt.SortOrder.DescendingOrder))
        self.layoutChanged.emit()

class MetricVisualDelegate(QStyledItemDelegate):
    """
    终极视觉增强：自定义单元格渲染器
    将枯燥的数字变为内置的微型进度条与彩色状态胶囊
    """
    def paint(self, painter, option, index):
        val = index.data(Qt.ItemDataRole.UserRole)
        col_name = index.model()._headers[index.column()]
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = option.rect.adjusted(4, 4, -4, -4)
        
        if col_name == "w_i": # 为质量指数画迷你进度条
            pct = max(0.0, min(1.0, float(val)))
            # 背景槽
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(30, 35, 40))
            painter.drawRoundedRect(rect, 4, 4)
            # 进度条
            bar_rect = QRectF(rect.x(), rect.y(), rect.width() * pct, rect.height())
            color = QColor(0, 255, 148) if pct >= 0.75 else QColor(255, 77, 77)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_rect, 4, 4)
            # 文字
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, f"{val:.3f}")
            
        elif col_name == "status": # 画红绿胶囊 (Pill Tag)
            is_pass = (val == "PASS")
            bg_color = QColor(0, 150, 80, 180) if is_pass else QColor(200, 40, 40, 180)
            border_color = QColor(0, 255, 148) if is_pass else QColor(255, 77, 77)
            
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect, rect.height()/2, rect.height()/2)
            
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, str(val))
            
        else:
            # 默认文字渲染
            super().paint(painter, option, index)
            
        painter.restore()

# =============================================================================
# 3. 数据透视图表组件 (Historical Trend Chart)
# =============================================================================

class HistoryChartCanvas(QWidget):
    """联动图表：点击表格数据，实时绘制该批次的温漂特征曲线"""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.fig = Figure(facecolor='#0F1218', dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0F1218')

    def render_chart(self, raw_data, headers):
        self.ax.clear()
        
        if not raw_data:
            self.ax.text(0.5, 0.5, "NO DATA", color='#555', fontsize=20, ha='center', va='center')
            self.canvas.draw()
            return
            
        # 寻找对应的列索引
        try:
            t_idx = headers.index('temperature')
            w_idx = headers.index('w_i')
            p_idx = headers.index('p_ki')
        except ValueError:
            # 如果 SQL 查询没有包含这些列，直接清空返回
            self.canvas.draw()
            return
            
        temps = [row[t_idx] for row in raw_data]
        wis =[row[w_idx] for row in raw_data]
        pkis = [row[p_idx] for row in raw_data]
        
        # 绘制 Wi 质量衰退散点与回归线
        scatter = self.ax.scatter(temps, wis, c=pkis, cmap='coolwarm', s=60, alpha=0.8, edgecolors='w', linewidth=0.5)
        
        self.ax.axhline(0.75, color='#FFCC00', linestyle='--', linewidth=1.5, label='Quality Threshold (0.75)')
        
        self.ax.set_title("Temperature Drift vs Quality Index (Wi)", color='white', fontsize=11)
        self.ax.set_xlabel("Junction Temperature (°C)", color='#888', fontsize=9)
        self.ax.set_ylabel("Quality Index (Wi)", color='#888', fontsize=9)
        self.ax.tick_params(colors='#666')
        
        for spine in self.ax.spines.values():
            spine.set_color('#333')
            
        self.ax.legend(facecolor='#151921', edgecolor='#333', labelcolor='white')
        self.fig.tight_layout()
        self.canvas.draw()

# =============================================================================
# 4. 极致交互主控面板 (Data Center Master Page)
# =============================================================================

class ExperimentalDataCenterPage(QWidget):
    """
    第 12 个菜单：实验数据中心
    具有 DataGrip 风格的极致数据库 UI
    包含多级 Splitter，SQL 沙盒，自绘单元格以及无损导出
    """
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self._init_ui()
        self._execute_sql("SELECT * FROM igbt_metrics ORDER BY test_date DESC LIMIT 100")

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 1. 顶部全功能操作栏 (Toolbar)
        self.toolbar = QFrame()
        self.toolbar.setFixedHeight(50)
        self.toolbar.setStyleSheet("background-color: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        tb_l = QHBoxLayout(self.toolbar)
        
        title = QLabel("实验数据中心")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00A3FF; border: none;")
        tb_l.addWidget(title)
        tb_l.addStretch()
        
        btn_style = "QPushButton { background: #0078D4; color: white; font-weight:bold; border-radius:4px; padding: 5px 15px;} QPushButton:hover { background: #0086F0; }"
        
        self.btn_refresh = QPushButton("🔄 刷新库")
        self.btn_export = QPushButton("📤 导出报表")
        self.btn_del = QPushButton("🗑 抹除缺陷数据")
        self.btn_del.setStyleSheet("QPushButton { background: #D83B01; color: white; font-weight:bold; border-radius:4px; padding: 5px 15px;} QPushButton:hover { background: #E5531B; }")
        
        for btn in[self.btn_refresh, self.btn_export, self.btn_del]:
            if btn != self.btn_del: btn.setStyleSheet(btn_style)
            tb_l.addWidget(btn)
            
        self.main_layout.addWidget(self.toolbar)

        # 2. 核心三分体结构 (QSplitter)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- 上半部分 (Browser Area) ---
        self.h_splitter_top = QSplitter(Qt.Orientation.Horizontal)
        
        # 左上：维度导航树
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("background: #0D1117; color: #DCDCDC; border: 1px solid #2A2F3A;")
        self._build_nav_tree()
        self.h_splitter_top.addWidget(self.tree)
        
        # 右上：高级数据表格
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setStyleSheet("""
            QTableView { background: #0B0E14; color: #DCDCDC; gridline-color: #2A2F3A; border: 1px solid #2A2F3A; }
            QHeaderView::section { background: #151921; color: #00A3FF; border: 1px solid #2A2F3A; padding: 4px; font-weight: bold; }
            QTableView::item:selected { background: #004578; }
        """)
        # 挂载高级视觉渲染器
        self.delegate = MetricVisualDelegate()
        self.table_view.setItemDelegate(self.delegate)
        self.h_splitter_top.addWidget(self.table_view)
        
        self.h_splitter_top.setStretchFactor(0, 2)
        self.h_splitter_top.setStretchFactor(1, 8)
        self.v_splitter.addWidget(self.h_splitter_top)

        # --- 下半部分 (Analysis & Console Area) ---
        self.h_splitter_bot = QSplitter(Qt.Orientation.Horizontal)
        
        # 左下：专家级 SQL 沙盒
        sql_frame = QFrame()
        sql_frame.setStyleSheet("background: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        sql_l = QVBoxLayout(sql_frame)
        
        sql_top = QHBoxLayout()
        sql_top.addWidget(QLabel("<b style='color:#00A3FF'>SQL Sandbox:</b> Execute Raw Query"))
        self.btn_exec_sql = QPushButton("▶ 运行 SQL")
        self.btn_exec_sql.setStyleSheet("background:#238636; color:white; font-weight:bold; border-radius:3px;")
        self.btn_exec_sql.clicked.connect(self._on_sql_execute)
        sql_top.addWidget(self.btn_exec_sql)
        
        self.sql_editor = QTextEdit("SELECT * FROM igbt_metrics\nWHERE w_i < 0.75 \nORDER BY p_ki DESC;")
        self.sql_editor.setStyleSheet("background: #05070A; color: #FFCC00; font-family: Consolas; font-size: 14px; border: 1px solid #333;")
        
        sql_l.addLayout(sql_top)
        sql_l.addWidget(self.sql_editor)
        self.h_splitter_bot.addWidget(sql_frame)
        
        # 右下：联动分析图表
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background: #151921; border-radius: 6px; border: 1px solid #2A2F3A;")
        chart_l = QVBoxLayout(chart_frame)
        self.chart = HistoryChartCanvas()
        chart_l.addWidget(self.chart)
        self.h_splitter_bot.addWidget(chart_frame)

        self.h_splitter_bot.setStretchFactor(0, 4)
        self.h_splitter_bot.setStretchFactor(1, 6)
        self.v_splitter.addWidget(self.h_splitter_bot)

        self.v_splitter.setStretchFactor(0, 6)
        self.v_splitter.setStretchFactor(1, 4)
        self.main_layout.addWidget(self.v_splitter)

        # ---------------------------------------------------------
        # 事件绑定与交互信号连接
        # ---------------------------------------------------------
        self.tree.itemClicked.connect(self._on_tree_click)
        self.btn_refresh.clicked.connect(lambda: self._execute_sql("SELECT * FROM igbt_metrics LIMIT 200"))
        self.btn_del.clicked.connect(self._delete_selected)
        
        # 绑定导出功能
        self.btn_export.clicked.connect(self._export_report)

    def _build_nav_tree(self):
        """生成多维导航树"""
        root = QTreeWidgetItem(self.tree,["🗂 全部批次"])
        root.setExpanded(True)
        for i in range(1, 6):
            batch = QTreeWidgetItem(root,[f"📦 批次 B-{202500+i}"])
            QTreeWidgetItem(batch, ["✅ 生产正常 (PASS)"])
            QTreeWidgetItem(batch, ["❌ 生产故障 (FAIL)"])

    def _on_tree_click(self, item, col):
        """树节点联动 SQL 引擎"""
        text = item.text(0)
        if "All" in text:
            self._execute_sql("SELECT * FROM igbt_metrics LIMIT 300")
        elif "批次" in text:
            batch_id = text.split(" ")[1]
            self._execute_sql(f"SELECT * FROM igbt_metrics WHERE batch_id='{batch_id}'")
        elif "PASS" in text:
            batch_id = item.parent().text(0).split(" ")[1]
            self._execute_sql(f"SELECT * FROM igbt_metrics WHERE batch_id='{batch_id}' AND status='PASS'")
        elif "FAIL" in text:
            batch_id = item.parent().text(0).split(" ")[1]
            self._execute_sql(f"SELECT * FROM igbt_metrics WHERE batch_id='{batch_id}' AND status='FAIL'")

    def _on_sql_execute(self):
        query = self.sql_editor.toPlainText()
        self._execute_sql(query)

    def _execute_sql(self, query):
        """核心查询引擎，串联 Table 和 Chart"""
        success, headers, data = self.db.execute_query(query)
        
        if not success:
            QMessageBox.critical(self, "SQL 执行失败", f"数据库引擎报错:\n{data}")
            return
            
        # 1. 刷新表格 MVC 模型
        self.model = IGBTTableModel(data, headers)
        self.table_view.setModel(self.model)
        
        # 2. 刷新底部联动图表
        if data:
            self.chart.render_chart(data, headers)
        else:
            self.chart.render_chart([],[])

    def _delete_selected(self):
        """完整的物理删除 CRUD 逻辑"""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "操作无效", "请先在表格中选择要抹除的缺陷数据行。")
            return
            
        # 获取 ID 列
        ids_to_delete =[]
        for idx in indexes:
            record_id = self.model._data[idx.row()][0] # 假设 id 是第0列
            ids_to_delete.append(str(record_id))
            
        confirm = QMessageBox.question(self, "危险操作确认", f"确定要从物理数据库中抹除这 {len(ids_to_delete)} 条记录吗？该操作不可逆！")
        if confirm == QMessageBox.StandardButton.Yes:
            ids_str = ",".join(ids_to_delete)
            sql = f"DELETE FROM igbt_metrics WHERE id IN ({ids_str})"
            success, _, msg = self.db.execute_query(sql)
            if success:
                QMessageBox.information(self, "操作成功", "缺陷记录已从数据库中抹除。")
                self._on_sql_execute() # 刷新当前视图
            else:
                QMessageBox.critical(self, "操作失败", f"删除异常: {msg}")

    def _export_report(self):
        """
        工业级数据导出引擎
        将当前 MVC 模型中的数据序列化为 CSV 报表，兼容 Excel 防乱码
        """
        # 1. 拦截校验：检查当前是否有数据
        if not hasattr(self, 'model') or not self.model._data:
            QMessageBox.warning(self, "导出失败", "当前视图无有效数据，请先执行 SQL 查询或选择左侧批次。")
            return

        # 2. 动态生成工业标准文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"IGBT_Patent_Report_{timestamp}.csv"

        # 3. 呼出系统级文件保存对话框
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出专利分析报表", 
            default_filename, 
            "CSV 报表文件 (*.csv);;所有文件 (*)"
        )

        if path:
            try:
                # 4. 执行序列化写入 (使用 utf-8-sig 防止 Excel 中文乱码)
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    
                    # 写入表头 (Headers)
                    writer.writerow(self.model._headers)
                    
                    # 写入数据本体 (Data rows)
                    for row in self.model._data:
                        # 针对浮点数进行精度截断美化，保持报表专业度
                        formatted_row =[
                            f"{val:.4f}" if isinstance(val, float) else val 
                            for val in row
                        ]
                        writer.writerow(formatted_row)
                
                # 5. 成功反馈
                QMessageBox.information(self, "导出成功", f"当前视图数据已成功序列化并导出至:\n{path}")
                
            except Exception as e:
                # 异常兜底
                QMessageBox.critical(self, "导出异常", f"文件系统拒绝写入或发生 IO 错误:\n{str(e)}")