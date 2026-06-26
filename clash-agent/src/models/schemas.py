"""
数据模型定义
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import json


class FaultStatus(Enum):
    """故障状态"""
    PENDING = "pending"
    RESOLVED = "resolved"
    FAILED = "failed"


class OperationType(Enum):
    """操作类型"""
    CLASH_ON = "clash_on"
    CLASH_OFF = "clash_off"
    CLASH_STATUS = "clash_status"
    CLASH_RESTART = "clash_restart"
    CLASH_UPDATE = "clash_update"
    CLASH_TUN = "clash_tun"
    CLASH_UI = "clash_ui"
    CLASH_SECRET = "clash_secret"
    CLASH_PROXY = "clash_proxy"
    CLASH_SUB = "clash_sub"
    CLASH_MIXIN = "clash_mixin"
    NETWORK_DNS = "network_dns_check"
    NETWORK_CONNECTIVITY = "network_connectivity_test"
    SYSTEM_PORT = "system_port_check"
    SYSTEM_IP_FORWARD = "system_ip_forward"
    SYSTEM_FIREWALL = "system_firewall_check"
    OTHER = "other"


@dataclass
class ReActStep:
    """ReAct单次循环步骤"""
    step_id: int
    reasoning: str
    action: Optional[str] = None
    action_params: dict = field(default_factory=dict)
    observation: str = ""
    reflection: str = ""
    is_complete: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReActStep":
        return cls(**data)


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    params_schema: dict
    func: callable

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "params": self.params_schema
        }


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "error": self.error
        }

    def __str__(self) -> str:
        if self.success:
            return self.stdout if self.stdout else "执行成功"
        return self.error or self.stderr or "执行失败"


@dataclass
class FaultRecord:
    """故障记录"""
    id: Optional[int] = None
    timestamp: str = ""
    symptom: str = ""
    root_cause: str = ""
    solution: str = ""
    tools_used: str = ""
    iteration_count: int = 0
    status: str = FaultStatus.PENDING.value
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FaultRecord":
        return cls(**data)


@dataclass
class OperationLog:
    """运维日志"""
    id: Optional[int] = None
    timestamp: str = ""
    operation_type: str = ""
    command: str = ""
    result: str = ""
    success: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OperationLog":
        return cls(**data)


@dataclass
class ExperienceKnowledge:
    """经验知识"""
    id: Optional[int] = None
    fault_pattern: str = ""
    symptoms: str = ""
    root_cause_analysis: str = ""
    solution: str = ""
    effectiveness_rating: int = 0
    created_at: str = ""
    usage_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExperienceKnowledge":
        return cls(**data)


@dataclass
class ReActResult:
    """ReAct执行结果"""
    response: str
    steps: list[ReActStep]
    iterations: int
    success: bool
    final_state: str = ""

    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "steps": [s.to_dict() for s in self.steps],
            "iterations": self.iterations,
            "success": self.success,
            "final_state": self.final_state
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ConversationMessage:
    """会话消息"""
    role: str  # system/user/assistant
    content: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        return cls(**data)
