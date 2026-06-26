"""
Clash Agent 主入口
"""

import argparse
import sys
import json
from pathlib import Path

from config.settings import LLM_CONFIG, REACT_CONFIG
from src.core.llm_adapter import LLMManager
from src.core.tool_registry import ToolRegistry, global_tool_registry
from src.core.memory import Memory
from src.core.react_engine import ReActEngine
from src.tools.clash_tools import clash_tools
from src.tools.network_tools import network_tools
from src.tools.system_tools import system_tools
from src.utils.logger import get_logger

logger = get_logger()


def register_all_tools():
    """注册所有工具到全局工具注册表"""

    # Clash运维工具
    registry = global_tool_registry

    # Clash服务控制
    registry.register(
        name="clash_status",
        description="检查Clash服务状态",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.status)

    registry.register(
        name="clash_on",
        description="开启Clash代理",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.on)

    registry.register(
        name="clash_off",
        description="关闭Clash代理",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.off)

    registry.register(
        name="clash_restart",
        description="重启Clash服务",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.restart)

    registry.register(
        name="clash_update",
        description="更新订阅链接",
        params_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "订阅URL（可选，不提供则使用默认订阅）"
                }
            },
            "required": []
        }
    )(clash_tools.update_subscription)

    registry.register(
        name="clash_ui",
        description="获取Clash面板访问信息",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.ui)

    registry.register(
        name="clash_secret",
        description="查看或设置Web面板密钥",
        params_schema={
            "type": "object",
            "properties": {
                "new_secret": {
                    "type": "string",
                    "description": "新密钥（可选，不提供则只查看）"
                }
            },
            "required": []
        }
    )(clash_tools.secret)

    registry.register(
        name="clash_tun",
        description="控制TUN模式",
        params_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "开启或关闭"
                }
            },
            "required": ["action"]
        }
    )(clash_tools.tun)

    registry.register(
        name="clash_proxy",
        description="控制系统代理开关",
        params_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "开启或关闭"
                }
            },
            "required": ["action"]
        }
    )(clash_tools.proxy)

    registry.register(
        name="clash_version",
        description="获取Clash版本信息",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(clash_tools.version)

    # 网络诊断工具
    registry.register(
        name="network_dns_check",
        description="检查DNS污染",
        params_schema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "要检查的域名（默认google.com）"
                }
            },
            "required": []
        }
    )(network_tools.dns_check)

    registry.register(
        name="network_connectivity_test",
        description="测试网络连接",
        params_schema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "测试目标URL"
                },
                "use_proxy": {
                    "type": "boolean",
                    "description": "是否使用代理"
                }
            },
            "required": []
        }
    )(network_tools.connectivity_test)

    registry.register(
        name="network_proxy_test",
        description="测试代理连接",
        params_schema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "代理主机"
                },
                "port": {
                    "type": "integer",
                    "description": "代理端口"
                }
            },
            "required": []
        }
    )(network_tools.proxy_test)

    registry.register(
        name="network_latency_test",
        description="测试网络延迟",
        params_schema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "测试主机"
                }
            },
            "required": []
        }
    )(network_tools.latency_test)

    # 系统工具
    registry.register(
        name="system_port_check",
        description="检查端口占用",
        params_schema={
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "description": "端口号"
                }
            },
            "required": ["port"]
        }
    )(system_tools.port_check)

    registry.register(
        name="system_ip_forward",
        description="检查IP转发状态",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(system_tools.ip_forward_check)

    registry.register(
        name="system_firewall_check",
        description="检查防火墙规则",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(system_tools.firewall_check)

    registry.register(
        name="system_info",
        description="获取系统基本信息",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(system_tools.system_info)

    registry.register(
        name="system_memory",
        description="检查内存使用",
        params_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )(system_tools.memory_usage)

    registry.register(
        name="system_disk",
        description="检查磁盘使用",
        params_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "路径（默认/）"
                }
            },
            "required": []
        }
    )(system_tools.disk_usage)

    logger.info(f"已注册 {len(registry.tools)} 个工具")


class ClashAgent:
    """Clash Agent主类"""

    def __init__(self):
        logger.info("初始化Clash Agent...")

        # 注册所有工具
        register_all_tools()

        # 初始化LLM管理器
        self.llm_manager = LLMManager()

        if not self.llm_manager.is_available():
            logger.error("没有可用的LLM后端，请检查配置")
            raise RuntimeError("没有可用的LLM后端")

        # 初始化记忆系统
        self.memory = Memory()

        # 初始化ReAct引擎
        self.engine = ReActEngine(
            llm_manager=self.llm_manager,
            tool_registry=global_tool_registry,
            memory=self.memory
        )

        logger.info("Clash Agent初始化完成")

    def chat(self, user_input: str) -> str:
        """处理用户输入"""
        logger.info(f"收到用户输入: {user_input}")

        try:
            result = self.engine.run(user_input)
            return result.response
        except Exception as e:
            logger.error(f"处理失败: {e}")
            return f"处理失败: {e}"

    def interactive(self):
        """交互模式"""
        print("=" * 60)
        print("Clash Agent 交互模式")
        print("=" * 60)
        print("输入你的问题，按 Enter 发送，输入 'quit' 或 'exit' 退出")
        print("输入 'clear' 清空会话历史")
        print("=" * 60)

        while True:
            try:
                user_input = input("\n你: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "退出"]:
                    print("再见!")
                    break

                if user_input.lower() == "clear":
                    self.memory.clear_conversation()
                    print("会话历史已清空")
                    continue

                if user_input.lower() == "tools":
                    print("\n可用工具:")
                    for tool in global_tool_registry.list_tools():
                        print(f"  - {tool['name']}: {tool['description']}")
                    continue

                if user_input.lower() == "help":
                    print("\n命令:")
                    print("  quit/exit: 退出")
                    print("  clear: 清空会话历史")
                    print("  tools: 显示可用工具")
                    print("  help: 显示帮助")
                    continue

                print("\n思考中...")
                response = self.chat(user_input)
                print(f"\nAgent: {response}")

            except KeyboardInterrupt:
                print("\n\n已退出")
                break
            except Exception as e:
                print(f"\n错误: {e}")

    def status(self) -> dict:
        """获取状态信息"""
        stats = self.memory.get_statistics()
        return {
            "llm_adapters": self.llm_manager.list_adapters(),
            "tools_count": len(global_tool_registry.tools),
            "memory_stats": stats
        }


def main():
    parser = argparse.ArgumentParser(description="Clash Agent - Clash网关运维AI")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("-c", "--cmd", type=str, help="单次命令执行")
    parser.add_argument("--llm", type=str, choices=["local", "deepseek"], help="指定LLM后端")
    parser.add_argument("--status", action="store_true", help="显示状态信息")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    try:
        agent = ClashAgent()

        if args.status:
            status = agent.status()
            if args.json:
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                print("\n=== Clash Agent 状态 ===")
                print(f"LLM适配器: {', '.join(status['llm_adapters'])}")
                print(f"可用工具: {status['tools_count']} 个")
                print(f"总故障记录: {status['memory_stats']['total_faults']}")
                print(f"已解决故障: {status['memory_stats']['resolved_faults']}")
                print(f"经验知识: {status['memory_stats']['total_experiences']} 条")
            return

        if args.interactive:
            agent.interactive()
        elif args.cmd:
            result = agent.chat(args.cmd)
            if args.json:
                print(json.dumps({"response": result}, indent=2, ensure_ascii=False))
            else:
                print(result)
        else:
            # 默认进入交互模式
            agent.interactive()

    except KeyboardInterrupt:
        print("\n已退出")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
