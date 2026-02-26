import sys
import importlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PatentLogicReloader(FileSystemEventHandler):
    """
    专门负责热重载专利算法核心逻辑
    无需重启GUI即可修改数学公式并立即生效
    """
    def __init__(self, main_ui):
        self.ui = main_ui

    def on_modified(self, event):
        if event.src_path.endswith(".py") and "core" in event.src_path:
            module_name = event.src_path.split("/")[-1].replace(".py", "")
            print(f"检测到专利算法变动: {module_name}，正在动态编译...")
            try:
                # 重新加载具体算法模块
                if f"core.{module_name}" in sys.modules:
                    importlib.reload(sys.modules[f"core.{module_name}"])
                self.ui.statusBar().showMessage(f"逻辑重载成功: {module_name}", 5000)
            except Exception as e:
                print(f"重载冲突: {str(e)}")