"""
系统工具 - 系统状态检查和配置
"""

import re
from typing import Optional

from config.settings import CLASH_CONFIG
from src.utils.helpers import run_command
from src.utils.logger import get_logger

logger = get_logger()


class SystemTools:
    """系统工具类"""

    def __init__(self):
        self.timeout = 10

    def _run(self, command: str, timeout: int = None) -> dict:
        """执行命令"""
        result = run_command(command, timeout or self.timeout)
        return result.to_dict()

    def port_check(self, port: int) -> dict:
        """端口占用检查"""
        logger.info(f"检查端口: {port}")

        # 使用ss命令检查端口
        result = self._run(f"ss -tlnp | grep ':{port}'", timeout=5)

        if result["success"] and result["stdout"]:
            # 解析端口信息
            listening = "LISTEN" in result["stdout"]
            return {
                "success": True,
                "port": port,
                "in_use": True,
                "listening": listening,
                "details": result["stdout"],
                "message": f"端口 {port} 已被占用" if listening else f"端口 {port} 已被使用但未监听"
            }
        else:
            return {
                "success": True,
                "port": port,
                "in_use": False,
                "listening": False,
                "message": f"端口 {port} 未被占用"
            }

    def ip_forward_check(self) -> dict:
        """IP转发状态检查"""
        logger.info("检查IP转发状态")

        result = self._run("sysctl net.ipv4.ip_forward", timeout=5)

        if result["success"]:
            value = result["stdout"].split("=")[-1].strip() if "=" in result["stdout"] else "unknown"
            enabled = value == "1"
            return {
                "success": True,
                "enabled": enabled,
                "value": value,
                "message": "IP转发已开启" if enabled else "IP转发已关闭（网关模式需要开启）"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "检查失败"),
                "message": "IP转发检查失败"
            }

    def ip_forward_enable(self) -> dict:
        """开启IP转发"""
        logger.info("开启IP转发...")

        # 临时开启
        result = self._run("sysctl -w net.ipv4.ip_forward=1", timeout=5)

        if result["success"]:
            # 永久开启（写入配置文件）
            self._run("echo 1 > /proc/sys/net/ipv4/ip_forward", timeout=5)
            logger.info("IP转发已开启")
            return {
                "success": True,
                "message": "IP转发已开启（临时）"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "操作失败"),
                "message": "IP转发开启失败"
            }

    def firewall_check(self) -> dict:
        """防火墙规则检查"""
        logger.info("检查防火墙规则")

        # 检查iptables规则
        result = self._run("iptables -L -n -v", timeout=10)

        if result["success"]:
            output = result["stdout"]
            # 检查是否有Clash相关规则
            has_clash_rules = "CLASH" in output or "mihomo" in output.lower()

            return {
                "success": True,
                "has_clash_rules": has_clash_rules,
                "rules_count": len([l for l in output.split("\n") if l.startswith("Chain")]),
                "message": "Clash规则已配置" if has_clash_rules else "未检测到Clash规则"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "检查失败"),
                "message": "防火墙规则检查失败"
            }

    def service_status(self, service_name: str = None) -> dict:
        """服务状态检查"""
        service = service_name or CLASH_CONFIG["service_name"]
        logger.info(f"检查服务状态: {service}")

        result = self._run(f"systemctl status {service}", timeout=10)

        if result["success"]:
            output = result["stdout"]
            is_active = "active (running)" in output
            is_enabled = "enabled" in output

            return {
                "success": True,
                "service": service,
                "is_active": is_active,
                "is_enabled": is_enabled,
                "status": "running" if is_active else "stopped",
                "message": f"{service} 服务运行中" if is_active else f"{service} 服务未运行"
            }
        else:
            # 尝试使用service命令
            result = self._run(f"service {service} status", timeout=10)
            if result["success"]:
                return {
                    "success": True,
                    "service": service,
                    "is_active": True,
                    "message": f"{service} 服务运行中"
                }
            return {
                "success": False,
                "service": service,
                "error": result.get("error", "检查失败"),
                "message": f"{service} 服务状态检查失败"
            }

    def process_check(self, process_name: str = "mihomo") -> dict:
        """进程检查"""
        logger.info(f"检查进程: {process_name}")

        result = self._run(f"pgrep -f {process_name}", timeout=5)

        if result["success"] and result["stdout"]:
            pids = [int(p) for p in result["stdout"].strip().split("\n") if p.strip()]
            return {
                "success": True,
                "process": process_name,
                "running": True,
                "pids": pids,
                "count": len(pids),
                "message": f"进程 {process_name} 正在运行 (PID: {pids[0] if pids else 'N/A'})"
            }
        else:
            return {
                "success": True,
                "process": process_name,
                "running": False,
                "pids": [],
                "count": 0,
                "message": f"进程 {process_name} 未运行"
            }

    def disk_usage(self, path: str = "/") -> dict:
        """磁盘使用率检查"""
        logger.info(f"检查磁盘使用: {path}")

        result = self._run(f"df -h {path}", timeout=5)

        if result["success"]:
            lines = result["stdout"].strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                return {
                    "success": True,
                    "path": path,
                    "filesystem": parts[0],
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                    "message": f"{path}: {parts[4]} 已使用"
                }
        return {
            "success": False,
            "error": result.get("error", "检查失败"),
            "message": "磁盘使用检查失败"
        }

    def memory_usage(self) -> dict:
        """内存使用率检查"""
        logger.info("检查内存使用")

        result = self._run("free -m", timeout=5)

        if result["success"]:
            lines = result["stdout"].strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])
                percent = round(used / total * 100, 1)

                return {
                    "success": True,
                    "total_mb": total,
                    "used_mb": used,
                    "free_mb": free,
                    "percent": percent,
                    "message": f"内存使用: {used}MB / {total}MB ({percent}%)"
                }
        return {
            "success": False,
            "error": result.get("error", "检查失败"),
            "message": "内存使用检查失败"
        }

    def cpu_usage(self) -> dict:
        """CPU使用率检查"""
        logger.info("检查CPU使用")

        result = self._run("top -bn1 | head -5", timeout=5)

        if result["success"]:
            output = result["stdout"]
            match = re.search(r"Cpu\(s\):\s*([\d.]+)%*us,\s*([\d.]+)%*sy", output)
            if match:
                return {
                    "success": True,
                    "user_percent": float(match.group(1)),
                    "system_percent": float(match.group(2)),
                    "total_percent": round(float(match.group(1)) + float(match.group(2)), 1),
                    "message": f"CPU使用率: {round(float(match.group(1)) + float(match.group(2)), 1)}%"
                }

        # 后备方案：使用uptime
        result = self._run("uptime", timeout=5)
        if result["success"]:
            match = re.search(r"load average[s]:\s*([\d.]+)", result["stdout"])
            if match:
                return {
                    "success": True,
                    "load_average": float(match.group(1)),
                    "message": f"负载: {match.group(1)}"
                }

        return {
            "success": False,
            "error": "无法获取CPU使用率",
            "message": "CPU使用检查失败"
        }

    def system_info(self) -> dict:
        """获取系统基本信息"""
        logger.info("获取系统信息")

        results = {}

        # hostname
        r = self._run("hostname", timeout=5)
        results["hostname"] = r["stdout"] if r["success"] else "unknown"

        # os版本
        r = self._run("cat /etc/os-release | head -2", timeout=5)
        if r["success"]:
            match = re.search(r'PRETTY_NAME="([^"]+)"', r["stdout"])
            results["os"] = match.group(1) if match else "unknown"
        else:
            results["os"] = "unknown"

        # 内核版本
        r = self._run("uname -r", timeout=5)
        results["kernel"] = r["stdout"] if r["success"] else "unknown"

        # 架构
        r = self._run("uname -m", timeout=5)
        results["arch"] = r["stdout"] if r["success"] else "unknown"

        return {
            "success": True,
            "info": results,
            "message": f"{results['hostname']} | {results['os']} | {results['arch']}"
        }


# 全局实例
system_tools = SystemTools()
