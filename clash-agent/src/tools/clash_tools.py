"""
Clash运维工具集 - 封装clashctl等命令
"""

import time
from typing import Optional

from config.settings import CLASH_CONFIG
from src.models.schemas import OperationType, OperationLog
from src.utils.helpers import run_command
from src.utils.logger import get_logger

logger = get_logger()


class ClashTools:
    """Clash运维工具类"""

    def __init__(self):
        self.service_name = CLASH_CONFIG["service_name"]
        self.clashctl_path = CLASH_CONFIG["clashctl_path"]
        self.timeout = CLASH_CONFIG["command_timeout"]

    def _run(self, command: str, timeout: int = None) -> dict:
        """执行clash命令"""
        result = run_command(command, timeout or self.timeout)
        return result.to_dict()

    def status(self) -> dict:
        """检查Clash服务状态"""
        result = self._run(f"{self.clashctl_path} status")
        return {
            "success": result["success"],
            "status": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def on(self) -> dict:
        """开启Clash代理"""
        logger.info("正在开启Clash代理...")
        result = self._run("clashon")
        if result["success"]:
            logger.info("Clash代理已开启")
        return {
            "success": result["success"],
            "message": "Clash代理已开启" if result["success"] else result.get("error", result["stderr"])
        }

    def off(self) -> dict:
        """关闭Clash代理"""
        logger.info("正在关闭Clash代理...")
        result = self._run("clashoff")
        if result["success"]:
            logger.info("Clash代理已关闭")
        return {
            "success": result["success"],
            "message": "Clash代理已关闭" if result["success"] else result.get("error", result["stderr"])
        }

    def restart(self) -> dict:
        """重启Clash服务"""
        logger.info("正在重启Clash服务...")

        # 先关闭
        off_result = self._run("clashoff")
        if not off_result["success"]:
            logger.warning(f"关闭Clash失败: {off_result.get('error')}")

        time.sleep(1)

        # 再开启
        on_result = self._run("clashon")
        if on_result["success"]:
            logger.info("Clash服务已重启")
        return {
            "success": on_result["success"],
            "message": "Clash服务已重启" if on_result["success"] else on_result.get("error", on_result["stderr"])
        }

    def update_subscription(self, url: Optional[str] = None) -> dict:
        """更新订阅"""
        logger.info(f"正在更新订阅: {url or '默认订阅'}...")
        if url:
            cmd = f"{self.clashctl_path} update {url}"
        else:
            cmd = f"{self.clashctl_path} update"
        result = self._run(cmd, timeout=60)  # 订阅更新可能较慢
        return {
            "success": result["success"],
            "output": result["stdout"],
            "message": "订阅更新成功" if result["success"] else result.get("error", result["stderr"])
        }

    def ui(self) -> dict:
        """获取面板访问信息"""
        result = self._run(f"{self.clashctl_path} ui")
        return {
            "success": result["success"],
            "info": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def secret(self, new_secret: Optional[str] = None) -> dict:
        """查看或设置Web密钥"""
        if new_secret:
            cmd = f"{self.clashctl_path} secret {new_secret}"
        else:
            cmd = f"{self.clashctl_path} secret"
        result = self._run(cmd)
        return {
            "success": result["success"],
            "secret": result["stdout"] if result["success"] and not new_secret else None,
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def tun(self, action: str = "on") -> dict:
        """TUN模式控制"""
        if action not in ["on", "off"]:
            return {"success": False, "error": "action must be 'on' or 'off'"}

        logger.info(f"正在{action} TUN模式...")
        result = self._run(f"clashtun {action}")
        return {
            "success": result["success"],
            "message": f"TUN模式已{action}" if result["success"] else result.get("error", result["stderr"])
        }

    def proxy(self, action: str = "on") -> dict:
        """系统代理开关"""
        if action not in ["on", "off"]:
            return {"success": False, "error": "action must be 'on' or 'off'"}

        cmd = f"{self.clashctl_path} proxy {action}"
        result = self._run(cmd)
        return {
            "success": result["success"],
            "message": f"系统代理已{action}" if result["success"] else result.get("error", result["stderr"])
        }

    def sub(self, profile: Optional[str] = None) -> dict:
        """订阅管理"""
        if profile:
            cmd = f"{self.clashctl_path} sub {profile}"
        else:
            cmd = f"{self.clashctl_path} sub"
        result = self._run(cmd)
        return {
            "success": result["success"],
            "info": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def mixin(self, action: str = "view") -> dict:
        """Mixin配置管理"""
        if action not in ["view", "edit", "runtime", "e", "r"]:
            return {"success": False, "error": "action must be 'view', 'edit', 'runtime' or 'e', 'r'"}

        cmd = f"{self.clashctl_path} mixin -{action[0]}" if len(action) == 1 else f"{self.clashctl_path} mixin -{action}"
        result = self._run(cmd)
        return {
            "success": result["success"],
            "info": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def lang(self, language: str = "zh") -> dict:
        """切换语言"""
        if language not in ["zh", "en"]:
            return {"success": False, "error": "language must be 'zh' or 'en'"}

        cmd = f"{self.clashctl_path} lang {language}"
        result = self._run(cmd)
        return {
            "success": result["success"],
            "message": f"语言已切换为{language}" if result["success"] else result.get("error", result["stderr"])
        }

    def version(self) -> dict:
        """获取Clash版本"""
        result = self._run(f"{self.clashctl_path} version")
        return {
            "success": result["success"],
            "version": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }

    def help(self) -> dict:
        """获取帮助信息"""
        result = self._run(f"{self.clashctl_path} help")
        return {
            "success": result["success"],
            "help": result["stdout"],
            "message": result["stdout"] if result["success"] else result.get("error", result["stderr"])
        }


# 全局实例
clash_tools = ClashTools()
