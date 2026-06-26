"""
工具注册表 - 管理所有可用的运维工具
"""

from typing import Optional, Callable, Any
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    params_schema: dict
    func: Callable


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        params_schema: dict = None
    ) -> Callable:
        """
        工具注册装饰器

        Args:
            name: 工具名称
            description: 工具描述
            params_schema: 参数JSON Schema
        """
        def decorator(func: Callable) -> Callable:
            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                params_schema=params_schema or {},
                func=func
            )
            logger.debug(f"注册工具: {name}")
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具"""
        return self.tools.get(name)

    def execute(self, name: str, **kwargs) -> Any:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            logger.error(f"工具不存在: {name}")
            return {"success": False, "error": f"Tool not found: {name}"}

        try:
            logger.info(f"执行工具: {name}, 参数: {kwargs}")
            result = tool.func(**kwargs)
            return result
        except TypeError as e:
            # 参数错误
            logger.error(f"工具参数错误: {name}, {e}")
            return {"success": False, "error": f"Invalid parameters: {e}"}
        except Exception as e:
            # 其他执行错误
            logger.error(f"工具执行失败: {name}, {e}")
            return {"success": False, "error": str(e)}

    def list_tools(self) -> list[dict]:
        """列出所有工具"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "params": list(t.params_schema.get("properties", {}).keys())
            }
            for t in self.tools.values()
        ]

    def get_description(self) -> str:
        """获取所有工具的描述文本"""
        if not self.tools:
            return "暂无可用工具"

        lines = []
        for tool in self.tools.values():
            params = ", ".join(tool.params_schema.get("properties", {}).keys()) or "无参数"
            lines.append(f"- {tool.name}: {tool.description} (参数: {params})")
        return "\n".join(lines)

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self.tools


# 全局工具注册表实例
global_tool_registry = ToolRegistry()
