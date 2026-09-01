"""
美化日志模块 - 为 Windows 控制台提供彩色、美观的日志输出
使用 colorama 实现跨平台彩色输出
"""

import logging
import sys
import os
from datetime import datetime

# 尝试导入 colorama
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # 定义空的颜色常量
    class _Dummy:
        def __getattr__(self, name):
            return ""
    Fore = _Dummy()
    Back = _Dummy()
    Style = _Dummy()


# 日志级别颜色配置
LEVEL_COLORS = {
    logging.DEBUG: Fore.CYAN + Style.DIM,
    logging.INFO: Fore.GREEN,
    logging.WARNING: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Fore.WHITE + Back.RED,
}

# 日志级别图标
LEVEL_ICONS = {
    logging.DEBUG: "🔍",
    logging.INFO: "✅",
    logging.WARNING: "⚠️",
    logging.ERROR: "❌",
    logging.CRITICAL: "💥",
}

# 模块颜色
MODULE_COLORS = {
    "__main__": Fore.MAGENTA,
    "database": Fore.CYAN,
    "downloader": Fore.BLUE,
    "netease_api": Fore.YELLOW,
    "httpx": Fore.WHITE + Style.DIM,
    "aiohttp": Fore.WHITE + Style.DIM,
    "urllib3": Fore.WHITE + Style.DIM,
}


class BeautifulFormatter(logging.Formatter):
    """美化的日志格式化器"""

    def __init__(self, use_color=True):
        super().__init__()
        self.use_color = use_color and COLORAMA_AVAILABLE

    def format(self, record):
        # 时间
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # 级别
        level_name = record.levelname
        level_color = LEVEL_COLORS.get(record.levelno, "")
        level_icon = LEVEL_ICONS.get(record.levelno, "📝")

        # 模块名
        module_name = record.name
        module_color = MODULE_COLORS.get(module_name, Fore.WHITE)

        # 消息
        message = record.getMessage()

        if self.use_color:
            # 彩色输出
            time_part = f"{Style.DIM}{Fore.WHITE}{time_str}{Style.RESET_ALL}"
            level_part = f"{level_color}{level_icon} {level_name:<7}{Style.RESET_ALL}"
            module_part = f"{module_color}[{module_name}]{Style.RESET_ALL}"
            msg_part = f"{Fore.WHITE}{message}{Style.RESET_ALL}"

            return f"{time_part} {level_part} {module_part} {msg_part}"
        else:
            # 无颜色输出
            return f"{time_str} {level_icon} {level_name:<7} [{module_name}] {message}"


class BeautifulLogger:
    """美化日志器配置"""

    @staticmethod
    def setup(level=logging.INFO, log_file=None):
        """
        设置美化日志

        Args:
            level: 日志级别
            log_file: 日志文件路径（可选）
        """
        # 获取根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # 清除已有的处理器
        root_logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(BeautifulFormatter(use_color=True))
        root_logger.addHandler(console_handler)

        # 文件处理器（如果指定）
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(BeautifulFormatter(use_color=False))
            root_logger.addHandler(file_handler)

        # 设置第三方库的日志级别
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        return root_logger

    @staticmethod
    def print_banner():
        """打印启动横幅"""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════╗
{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}    🎵 网易云音乐 Telegram Bot 🎵          {Fore.CYAN}{Style.BRIGHT}║
{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}    本地部署版                              {Fore.CYAN}{Style.BRIGHT}║
{Fore.CYAN}{Style.BRIGHT}╚══════════════════════════════════════════════╝{Style.RESET_ALL}
{Fore.GREEN}启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}
{Fore.YELLOW}按 Ctrl+C 停止 Bot{Style.RESET_ALL}
"""
        print(banner)

    @staticmethod
    def print_section(title):
        """打印分隔线"""
        print(f"\n{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}📌 {title}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}\n")

    @staticmethod
    def print_success(message):
        """打印成功消息"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

    @staticmethod
    def print_error(message):
        """打印错误消息"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

    @staticmethod
    def print_warning(message):
        """打印警告消息"""
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")

    @staticmethod
    def print_info(message):
        """打印信息消息"""
        print(f"{Fore.CYAN}ℹ️  {message}{Style.RESET_ALL}")


# 便捷函数
def setup_logging(level=logging.INFO, log_file=None):
    """快速设置美化日志"""
    return BeautifulLogger.setup(level, log_file)


def get_logger(name):
    """获取日志器"""
    return logging.getLogger(name)
