"""
辅助函数
"""

import subprocess
from typing import Optional
from dataclasses import asdict

from src.models.schemas import CommandResult
from src.utils.logger import get_logger

logger = get_logger()


def run_command(
    command: str,
    timeout: int = 30,
    shell: bool = True,
    capture_output: bool = True
) -> CommandResult:
    """
    执行系统命令的通用封装

    Args:
        command: 要执行的命令
        timeout: 超时时间（秒）
        shell: 是否使用shell执行
        capture_output: 是否捕获输出

    Returns:
        CommandResult对象
    """
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return CommandResult(
            success=result.returncode == 0,
            stdout=result.stdout.strip() if result.stdout else "",
            stderr=result.stderr.strip() if result.stderr else "",
            returncode=result.returncode
        )
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时: {command}")
        return CommandResult(
            success=False,
            error="Command timeout",
            returncode=-1
        )
    except Exception as e:
        logger.error(f"命令执行异常: {command}, error: {e}")
        return CommandResult(
            success=False,
            error=str(e),
            returncode=-1
        )


def format_dict(data: dict, indent: int = 2) -> str:
    """格式化字典为可读字符串"""
    if not data:
        return "无"
    items = []
    for key, value in data.items():
        items.append(f"{' ' * indent}{key}: {value}")
    return "\n".join(items)


def format_list(items: list, indent: int = 2) -> str:
    """格式化列表为可读字符串"""
    if not items:
        return "无"
    return "\n".join(f"{' ' * indent}- {item}" for item in items)


def parse_bool(value: str) -> bool:
    """解析布尔值"""
    return value.lower() in ("true", "1", "yes", "on")


def safe_get(data: dict, key: str, default: any = None) -> any:
    """安全获取字典值"""
    return data.get(key, default)


def dict_to_dataclass(data: dict, dataclass_type):
    """字典转换为dataclass"""
    try:
        return dataclass_type(**data)
    except Exception as e:
        logger.warning(f"字典转dataclass失败: {e}")
        return None
