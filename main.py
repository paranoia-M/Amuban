import sys
import os
import traceback
import random
from datetime import datetime

# 导入 PyQt6 核心组件
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtCore import Qt

# =============================================================================
# 1. 资源路径校准引擎 (支持本地运行与 PyInstaller 打包)
# =============================================================================
def resource_path(relative_path):
    """ 
    获取资源绝对路径。针对 PyInstaller 的单文件打包模式 (_MEIPASS) 进行自适应。
    """
    if hasattr(sys, '_MEIPASS'):
        # 打包后的临时解压路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 本地开发环境路径
    return os.path.join(os.path.abspath("."), relative_path)

# 将校准后的目录添加至搜索路径，确保动态加载 14 个菜单模块时不报错
sys.path.append(resource_path("ui"))
sys.path.append(resource_path("core"))

try:
    # 导入自定义模块
    from ui.login_window import LoginWindow
    from ui.main_window import IndustrialUI
except ImportError as e:
    print(f"模块载入失败：请确认 ui/ 目录下包含 __init__.py 以及对应的逻辑文件。")
    print(f"详情: {e}")
    sys.exit(1)

# =============================================================================
# 2. 系统启动调度中枢
# =============================================================================

class IGBTAppController:
    """
    系统引导控制器
    管理从 venv 环境检查、身份认证到总控平台载入的全生命周期
    """
    def __init__(self):
        self.app = QApplication(sys.argv)
        self._apply_global_config()

    def _apply_global_config(self):
        """ 应用全局工业级视觉配置 """
        # 设置 Fusion 样式，确保跨平台暗色主题表现一致
        self.app.setStyle('Fusion')
        
        # 统一字体渲染 (解决部分系统文字发虚)
        font = self.app.font()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.app.setFont(font)

    def run(self):
        """ 执行启动流水线 """
        try:
            print(f">>> [{datetime.now().strftime('%H:%M:%S')}] 正在初始化安全网关...")

            # ---------------------------------------------------------
            # 第一阶段：身份认证网关 (Login & Registration)
            # ---------------------------------------------------------
            login_gate = LoginWindow()
            
            # 以阻塞模式运行登录对话框
            if login_gate.exec() == QDialog.DialogCode.Accepted:
                
                # 从登录窗口获取已验证的操作员 ID
                operator_id = "未知用户"
                if hasattr(login_gate, 'user_input'):
                    operator_id = login_gate.user_input.text()
                
                print(f">>> 身份验证通过。操作员: {operator_id}。正在构建专利算法拓扑图...")

                # ---------------------------------------------------------
                # 第二阶段：载入 14 菜单主控逻辑平台
                # ---------------------------------------------------------
                # 此处会触发 main_window.py 中的 safe_import 和页面实例化
                self.main_window = IndustrialUI()
                self.main_window.show()
                
                print(">>> 系统运行中。监控状态：ACTIVE")
                
                # 启动事件循环
                return self.app.exec()
            
            else:
                print(">>> 认证流程被用户中断，程序安全退出。")
                return 0

        except Exception:
            # 捕获所有运行时导致的“闪退”异常并打印位置
            print("\n" + "="*60)
            print("CRITICAL ERROR: 系统核心逻辑发生致命崩溃")
            print(f"发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            traceback.print_exc()
            
            # 弹出图形化报错提示
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("系统运行异常")
            error_dialog.setText("检测到核心算法模块冲突或路径丢失。")
            error_dialog.setInformativeText(traceback.format_exc())
            error_dialog.exec()
            return 1

# =============================================================================
# 3. 运行环境入口
# =============================================================================
if __name__ == "__main__":
    # 模拟 venv 激活状态检查
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("注意: 当前未检测到 venv 环境，请确保第三方科学计算库 (numpy/scipy/sklearn) 已安装。")

    # 实例化控制器并执行
    controller = IGBTAppController()
    sys.exit(controller.run())