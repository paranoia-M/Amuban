import sys
import os
import traceback
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

# =============================================================================
# 1. 运行环境拓扑校准
# =============================================================================
# 强制将当前脚本所在目录添加到系统搜索路径，确保多层级 import 不会报错
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

try:
    # 导入自定义安全网关模块
    from ui.login_window import LoginWindow
    # 导入 14 菜单主控逻辑平台模块
    from ui.main_window import IndustrialUI
except ImportError as e:
    print(f"致命错误：核心 UI 模块导入失败。请检查目录结构是否完整。\n详情: {e}")
    traceback.print_exc()
    sys.exit(1)

# =============================================================================
# 2. 系统核心入口函数
# =============================================================================

def bootstrap():
    """
    IGBT 智能自动化测试系统启动引导程序
    执行顺序：初始化App -> 安全认证网关 -> 硬件自检流水线 -> 载入主控逻辑层
    """
    # 初始化全局 Application 对象
    # 参数 sys.argv 允许程序接收外部命令行指令
    app = QApplication(sys.argv)
    
    # 强制注入工业 Fusion 样式，解决暗黑模式下原生控件对比度不足的问题
    app.setStyle('Fusion')
    
    # 全局字体微调，提升专利算法数据的阅读性
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)

    try:
        print(">>> 正在启动安全身份认证中心...")
        
        # ---------------------------------------------------------
        # 第一阶段：身份认证与系统预检
        # ---------------------------------------------------------
        login_gateway = LoginWindow()
        
        # 使用 exec() 以模态方式启动登录窗体，阻塞主线程直到用户响应
        # 内部触发 _start_system_check 执行驱动链路与专利指纹校验
        if login_gateway.exec() == QDialog.DialogCode.Accepted:
            
            # 获取登录后的用户信息（可用于报告生成人的自动填充）
            user_identity = login_gateway.user_input.text()
            print(f">>> 认证通过。操作员: {user_identity}。正在解构并挂载 14 核心专利页面...")

            # ---------------------------------------------------------
            # 第二阶段：主逻辑平台载入
            # ---------------------------------------------------------
            # 在登录窗体销毁后，立即实例化庞大的主控制窗口
            # 此时会触发 main_window.py 中的 safe_import() 和 14 个页面的实例化
            main_controller = IndustrialUI()
            
            # 显示主窗口
            main_controller.show()
            
            print(">>> IGBT 智能自动化测试系统已就绪，进入实时事务监听状态。")
            
            # 进入 Qt 事件循环，维持程序运行
            sys.exit(app.exec())
            
        else:
            # 用户点击取消或关闭登录框
            print(">>> 认证已取消或硬件自检未通过，系统安全退出。")
            sys.exit(0)

    except Exception as fatal_error:
        # 最后的防线：捕获所有未被处理的运行时异常并打印堆栈轨迹
        print("-" * 60)
        print(f"CRITICAL ERROR: 系统在初始化期间发生不可恢复的故障")
        print(f"异常定位: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        traceback.print_exc()
        sys.exit(1)

# =============================================================================
# 3. 启动执行
# =============================================================================
if __name__ == "__main__":
    # 检查是否在 venv 环境中运行（可选）
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Warning: 系统未检测到虚拟环境 (venv)，建议在虚拟环境中运行以确保 Scipy/Sklearn 依赖稳定。")
    
    bootstrap()