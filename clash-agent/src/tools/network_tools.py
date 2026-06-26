"""
网络诊断工具
"""

from typing import Optional
import re

from src.utils.helpers import run_command
from src.utils.logger import get_logger

logger = get_logger()


class NetworkTools:
    """网络诊断工具类"""

    def __init__(self):
        self.default_timeout = 10

    def _run(self, command: str, timeout: int = None) -> dict:
        """执行命令"""
        result = run_command(command, timeout or self.default_timeout)
        return result.to_dict()

    def dns_check(self, domain: str = "google.com") -> dict:
        """DNS污染检查"""
        logger.info(f"检查DNS: {domain}")

        # 使用dig检查DNS解析
        result = self._run(f"dig +short {domain}", timeout=5)

        if not result["success"]:
            # 尝试使用nslookup作为后备
            result = self._run(f"nslookup {domain}", timeout=5)

        if result["success"]:
            output = result["stdout"].strip()
            ips = [line.strip() for line in output.split("\n") if line.strip() and self._is_ip(line.strip())]

            # 检查是否有多个IP（可能是DNS污染）
            is_suspicious = len(ips) > 3

            return {
                "success": True,
                "domain": domain,
                "resolved_ips": ips,
                "count": len(ips),
                "is_resolved": len(ips) > 0,
                "is_suspicious": is_suspicious,
                "message": f"DNS解析正常，共{len(ips)}个IP" if ips else "DNS解析失败",
                "raw_output": output
            }
        else:
            return {
                "success": False,
                "domain": domain,
                "error": result.get("error", "DNS查询失败"),
                "message": f"DNS检查失败: {result.get('error')}"
            }

    def connectivity_test(self, target: str = "https://www.google.com", use_proxy: bool = True) -> dict:
        """网络连接测试"""
        logger.info(f"测试网络连接: {target}")

        # 使用curl测试，带代理和不带代理两种情况
        if use_proxy:
            cmd = f"curl -I -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {target}"
        else:
            cmd = f"curl -I -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 --noproxy '*' {target}"

        result = self._run(cmd, timeout=10)

        if result["success"]:
            http_code = result["stdout"].strip()
            try:
                code = int(http_code)
                reachable = 200 <= code < 400
                return {
                    "success": True,
                    "target": target,
                    "http_code": code,
                    "reachable": reachable,
                    "message": f"目标可达 (HTTP {code})" if reachable else f"目标不可达 (HTTP {code})"
                }
            except ValueError:
                return {
                    "success": False,
                    "target": target,
                    "error": f"无效的HTTP响应: {http_code}",
                    "message": f"连接测试失败"
                }
        else:
            return {
                "success": False,
                "target": target,
                "error": result.get("error", "连接超时"),
                "message": f"连接测试失败: {result.get('error')}"
            }

    def proxy_test(self, host: str = "127.0.0.1", port: int = 7890) -> dict:
        """代理连接测试"""
        logger.info(f"测试代理连接: {host}:{port}")

        # 测试SOCKS5代理
        result = self._run(
            f"curl -I -s -o /dev/null -w '%{{http_code}}' --proxy socks5://{host}:{port} "
            f"--connect-timeout 5 https://www.google.com",
            timeout=15
        )

        if result["success"]:
            http_code = result["stdout"].strip()
            try:
                code = int(http_code)
                return {
                    "success": code == 200,
                    "proxy": f"{host}:{port}",
                    "http_code": code,
                    "reachable": code == 200,
                    "message": "代理正常工作" if code == 200 else f"代理响应异常 (HTTP {code})"
                }
            except ValueError:
                return {
                    "success": False,
                    "proxy": f"{host}:{port}",
                    "error": f"无效响应: {http_code}",
                    "message": "代理测试失败"
                }
        else:
            return {
                "success": False,
                "proxy": f"{host}:{port}",
                "error": result.get("error", "连接失败"),
                "message": f"代理连接失败: {result.get('error')}"
            }

    def latency_test(self, host: str = "1.1.1.1") -> dict:
        """延迟测试"""
        logger.info(f"测试延迟: {host}")

        result = self._run(f"ping -c 4 -W 2 {host}", timeout=15)

        if result["success"]:
            output = result["stdout"]
            # 解析平均延迟
            match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output)
            if match:
                return {
                    "success": True,
                    "host": host,
                    "min_ms": float(match.group(1)),
                    "avg_ms": float(match.group(2)),
                    "max_ms": float(match.group(3)),
                    "message": f"平均延迟: {match.group(2)}ms"
                }
            else:
                return {
                    "success": True,
                    "host": host,
                    "raw_output": output,
                    "message": "延迟测试完成"
                }
        else:
            return {
                "success": False,
                "host": host,
                "error": result.get("error", "ping失败"),
                "message": f"延迟测试失败: {result.get('error')}"
            }

    def route_check(self) -> dict:
        """路由检查"""
        logger.info("检查路由表")

        # 检查默认路由
        result = self._run("ip route show default", timeout=5)

        return {
            "success": result["success"],
            "default_route": result["stdout"] if result["success"] else None,
            "message": result["stdout"] if result["success"] else f"路由检查失败: {result.get('error')}"
        }

    def dns_servers_check(self) -> dict:
        """检查DNS服务器配置"""
        logger.info("检查DNS服务器配置")

        # 读取/etc/resolv.conf
        result = self._run("cat /etc/resolv.conf", timeout=5)

        if result["success"]:
            nameservers = re.findall(r"nameserver\s+(\S+)", result["stdout"])
            return {
                "success": True,
                "nameservers": nameservers,
                "message": f"当前DNS服务器: {', '.join(nameservers)}" if nameservers else "未配置DNS服务器"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "读取失败"),
                "message": "DNS服务器检查失败"
            }

    @staticmethod
    def _is_ip(text: str) -> bool:
        """判断是否为IP地址"""
        ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        ipv6_pattern = r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$"
        return bool(re.match(ipv4_pattern, text) or re.match(ipv6_pattern, text))


# 全局实例
network_tools = NetworkTools()
