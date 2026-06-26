# 树莓派Clash全屋网关运维AI Agent——实施计划

## 一、项目概述

### 1.1 项目定位
搭建**垂直领域专用、树莓派本地离线、轻量自研 ReAct 架构**的AI运维智能体，专注Clash/Mihomo网关自愈运维，实现全自动无人值守。

### 1.2 核心目标
- 故障自动诊断 → 根因定位
- 自动匹配修复策略 → 执行运维工具
- 自动校验修复结果 → 失败自动重试
- 长期记忆运维日志 → 沉淀故障经验

### 1.3 技术选型
| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 适配树莓派ARM64，工具生态丰富 |
| LLM推理 | 本地Qwen-1.8B / DeepSeek API | 本地离线+可选云端增强 |
| Agent架构 | 手写ReAct | 无重型框架依赖，彻底理解核心 |
| 持久化 | SQLite | 轻量、跨平台、零配置 |

---

## 二、ReAct 架构详细设计

### 2.1 ReAct 核心循环原理

ReAct = **Reasoning** + **Acting** + **Observation** + **Reflection** 四阶段闭环：

```
┌─────────────────────────────────────────────────────────────┐
│                     ReAct 循环                               │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐              │
│  │ Reasoning │ → │  Acting  │ → │ Observation│             │
│  │  (思考)   │    │  (行动)  │    │   (观察)   │              │
│  └──────────┘    └──────────┘    └───────────┘              │
│       ↑                                       │              │
│       │           ┌───────────┐               │              │
│       └────────── │ Reflection│ ←────────────┘              │
│                   │   (反思)   │                             │
│                   └───────────┘                              │
│                        ↓                                     │
│              ┌─────────────────┐                             │
│              │   任务完成?      │                             │
│              └─────────────────┘                             │
│                   ↓ 是                                       │
│              ┌─────────────┐                                  │
│              │   输出结果   │                                  │
│              └─────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 各阶段职责

| 阶段 | 输入 | 输出 | 说明 |
|------|------|------|------|
| **Reasoning** | 用户问题 + 记忆上下文 | 推理链 + 下一步行动计划 | 调用LLM进行因果推理 |
| **Acting** | 行动计划 | 具体工具调用 + 参数 | 执行工具或调用LLM生成响应 |
| **Observation** | 工具执行结果 | 观察结果摘要 | 格式化工具返回 |
| **Reflection** | 观察结果 | 反思判断 | 判断任务是否完成、是否需要重试 |

### 2.3 单次循环数据结构

```python
@dataclass
class ReActStep:
    step_id: int              # 循环步数
    reasoning: str            # 当前推理
    action: Optional[str]     # 要执行的动作(工具名或"respond")
    action_params: dict       # 动作参数
    observation: str         # 执行结果观察
    reflection: str           # 反思判断
    is_complete: bool         # 是否已完成
```

### 2.4 最大循环次数
- **MAX_ITERATIONS = 10**：防止无限循环
- **早期终止条件**：任务明确完成或失败

---

## 三、项目架构

### 3.1 目录结构

```
clash-agent/                    # AI Agent主目录（与clash-for-linux-install独立）
├── config/
│   ├── settings.py             # 主配置（LLM、Clash路径、超时等）
│   └── prompts.py              # ReAct提示词模板
├── src/
│   ├── core/
│   │   ├── react_engine.py    # ReAct核心循环引擎
│   │   ├── llm_adapter.py      # LLM统一适配器（本地+API）
│   │   ├── tool_registry.py    # 工具注册表
│   │   └── memory.py           # 记忆系统（短期+长期）
│   ├── tools/
│   │   ├── clash_tools.py     # Clash运维工具集（封装clashctl命令）
│   │   ├── network_tools.py    # 网络诊断工具
│   │   └── system_tools.py     # 系统工具
│   ├── models/
│   │   └── schemas.py          # 数据模型定义
│   └── utils/
│       ├── logger.py           # 日志工具
│       └── helpers.py          # 辅助函数
├── data/
│   ├── memory.db               # SQLite记忆数据库
│   └── logs/                   # 日志目录
├── main.py                     # 主入口
├── requirements.txt           # 依赖
└── .env.example               # 环境变量示例

# 注意：clash-agent与nelvko/clash-for-linux-install独立部署
# clash-agent通过调用clashctl等命令与Clash系统交互
```

### 3.2 核心模块依赖关系

```
                    ┌─────────────┐
                    │   main.py   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ react_engine │ ←──┐
                    │  (ReAct核心)  │    │
                    └──────┬──────┘    │
                           │           │
              ┌────────────┼───────────┴────────────┐
              │            │                        │
       ┌──────▼──────┐ ┌───▼────┐           ┌──────▼──────┐
       │ llm_adapter │ │ tool_  │           │   memory    │
       │ (LLM适配器)  │ │registry│           │  (记忆系统) │
       └──────┬──────┘ └───┬────┘           └──────┬──────┘
              │            │                      │
       ┌──────▼──────┐ ┌───▼────┐           ┌──────▼──────┐
       │ 本地LLM/    │ │ clash_ │           │  SQLite     │
       │ DeepSeek API│ │ tools │           │  记忆库     │
       └─────────────┘ └───┬────┘           └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ clashctl命令 │ ←── 调用系统已安装的clash-for-linux-install
                    └─────────────┘
```

### 3.3 与clash-for-linux-install的集成关系

```
┌──────────────────────────────────────────────────────────────────┐
│                     树莓派系统环境                                │
│                                                                  │
│  ┌─────────────────────┐      ┌─────────────────────────────┐  │
│  │ nelvko/clash-for-   │      │     clash-agent (本项目)     │  │
│  │ linux-install       │      │                             │  │
│  │                     │      │  ┌───────────────────────┐  │  │
│  │  - clashctl         │◄─────┼──│  ReAct Engine          │  │  │
│  │  - clashon/off      │      │  │    ↓                   │  │  │
│  │  - clashtun         │      │  │  Tool Registry         │  │  │
│  │  - clashupdate      │      │  │    ↓                   │  │  │
│  │  - ...              │      │  │  clash_tools.py        │  │  │
│  │                     │      │  │    ↓                   │  │  │
│  │  - mihomo.service   │      │  │  subprocess calls      │  │  │
│  │  - config files     │      │  │    ↓                   │  │  │
│  └─────────────────────┘      │  │  clashctl/clashon/...  │  │  │
│                               │  └───────────────────────┘  │  │
│                               │                             │  │
│                               │  ┌───────────────────────┐  │  │
│                               │  │  Local LLM (Qwen)     │  │  │
│                               │  │  or DeepSeek API     │  │  │
│                               │  └───────────────────────┘  │  │
│                               └─────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**关键集成点：**
- clash-agent通过`subprocess`调用`clashctl`、`clashon`、`clashoff`等已安装命令
- 不修改clash-for-linux-install的任何文件，纯外部调用
- 状态检查通过`clashctl status`获取
- 服务管理通过`clashon`/`clashoff`/`clashctl restart`执行

---

## 四、LLM适配器设计（支持双模式）

### 4.1 抽象接口

```python
class BaseLLMAdapter(ABC):
    """LLM适配器抽象基类"""

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """同步对话接口"""
        pass

    @abstractmethod
    async def achat(self, messages: list[dict], **kwargs) -> str:
        """异步对话接口"""
        pass
```

### 4.2 本地LLM适配器（Qwen-1.8B）

```python
class LocalLLMAdapter(BaseLLMAdapter):
    """本地LLM适配器 - 支持Ollama/API格式"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2:1.8b"

    def chat(self, messages: list[dict], **kwargs) -> str:
        # 调用Ollama兼容API
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages}
        )
        return response.json()["message"]["content"]
```

### 4.3 DeepSeek API适配器

```python
class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek API适配器"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, messages: list[dict], **kwargs) -> str:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": messages
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

### 4.4 统一调度器

```python
class LLMManager:
    """LLM管理器 - 支持多后端自动切换"""

    def __init__(self, config: dict):
        self.adapters = {}
        # 初始化本地LLM（如果可用）
        if config.get("local_enabled"):
            self.adapters["local"] = LocalLLMAdapter(config["local_url"])
        # 初始化DeepSeek（如果配置了API Key）
        if config.get("deepseek_api_key"):
            self.adapters["deepseek"] = DeepSeekAdapter(config["deepseek_api_key"])

    def chat(self, messages: list[dict]) -> str:
        # 优先使用本地（离线），失败后切换DeepSeek
        for name in ["local", "deepseek"]:
            if name in self.adapters:
                try:
                    return self.adapters[name].chat(messages)
                except Exception:
                    continue
        raise RuntimeError("所有LLM后端均不可用")
```

---

## 五、ReAct提示词模板

### 5.1 系统提示词

```python
SYSTEM_PROMPT = """你是一个专业的Clash/Mihomo网关运维AI Agent。

## 你的职责
- 诊断Clash网关故障并给出修复方案
- 执行运维命令并验证结果
- 保持专业的技术沟通

## 可用工具
{available_tools_description}

## 记忆上下文
{memory_context}

## 输出格式
你必须按照以下JSON格式输出思考过程：

{
    "reasoning": "分析用户问题的推理过程",
    "action": "要执行的动作（工具名或'respond'）",
    "action_params": {{"tool_param": "value"}},
    "reflection": "对当前状态的反思判断"
}

## 关键原则
1. 先理解问题，再选择工具
2. 每个动作都要有明确的推理依据
3. 工具执行后必须验证结果
4. 无法解决时，明确告知用户
"""
```

### 5.2 工具调用结果处理

```python
TOOL_RESULT_PROMPT = """工具执行结果：
{tool_result}

请判断：
1. 任务是否完成？
2. 是否需要进一步操作？
3. 如果失败，原因是什么？

输出JSON格式：
{
    "observation": "对结果的客观描述",
    "is_complete": true/false,
    "next_action": "下一步动作或'respond'",
    "next_params": {{}}
}
"""
```

---

## 六、Clash运维工具集

### 6.1 工具注册机制

```python
@dataclass
class Tool:
    name: str
    description: str
    params_schema: dict  # JSON Schema格式
    func: callable

class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, params_schema: dict):
        def decorator(func):
            self.tools[name] = Tool(name, description, params_schema, func)
            return func
        return decorator

    def get_tool(self, name: str) -> Tool:
        return self.tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "params": t.params_schema}
            for t in self.tools.values()
        ]
```

### 6.2 核心工具清单（基于nelvko/clash-for-linux-install）

| 工具名 | 功能 | 底层命令 | 参数 |
|--------|------|----------|------|
| `clash_on` | 开启Clash代理 | `clashon` | - |
| `clash_off` | 关闭Clash代理 | `clashoff` | - |
| `clash_status` | 查看Clash服务状态 | `clashctl status` | - |
| `clash_restart` | 重启Clash服务 | `clashctl restart` | - |
| `clash_ui` | 获取面板访问信息 | `clashctl ui` | - |
| `clash_secret` | 查看/设置Web密钥 | `clashctl secret [SECRET]` | `secret: str (可选)` |
| `clash_update` | 更新订阅 | `clashctl update [url]` | `url: str (可选)` |
| `clash_tun` | TUN模式控制 | `clashtun [on\|off]` | `action: str (on/off)` |
| `clash_mixin` | Mixin配置管理 | `clashctl mixin [-e\|-r]` | `action: str (edit/view/runtime)` |
| `clash_proxy` | 系统代理开关 | `clashctl proxy [on\|off]` | `action: str (on/off)` |
| `clash_sub` | 订阅管理 | `clashctl sub [profile]` | `profile: str (可选)` |
| `clash_lang` | 切换语言 | `clashctl lang [zh\|en]` | `lang: str (zh/en)` |
| `network_dns_check` | DNS污染检查 | `dig +short <domain>` | `domain: str` |
| `network_connectivity_test` | 网络连接测试 | `curl -I <target>` | `target: str` |
| `system_port_check` | 端口占用检查 | `ss -tlnp \| grep <port>` | `port: int` |
| `system_ip_forward` | IP转发状态检查 | `sysctl net.ipv4.ip_forward` | - |
| `system_firewall_check` | 防火墙规则检查 | `iptables -L -n` | - |

### 6.3 工具实现示例

```python
import subprocess
import re
from typing import Optional

def _run_clash_command(command: str, timeout: int = 30) -> dict:
    """执行clash命令的通用封装"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clash_status() -> dict:
    """检查Clash服务状态"""
    return _run_clash_command("clashctl status")

def clash_on() -> dict:
    """开启Clash代理"""
    return _run_clash_command("clashon")

def clash_off() -> dict:
    """关闭Clash代理"""
    return _run_clash_command("clashoff")

def clash_restart() -> dict:
    """重启Clash服务"""
    # 先关闭再开启
    off_result = _run_clash_command("clashoff")
    if not off_result["success"]:
        return off_result
    time.sleep(1)
    return _run_clash_command("clashon")

def clash_update(subscription_url: Optional[str] = None) -> dict:
    """更新订阅"""
    if subscription_url:
        cmd = f"clashctl update {subscription_url}"
    else:
        cmd = "clashctl update"
    return _run_clash_command(cmd)

def clash_tun(action: str = "on") -> dict:
    """TUN模式控制"""
    if action not in ["on", "off"]:
        return {"success": False, "error": "action must be 'on' or 'off'"}
    return _run_clash_command(f"clashtun {action}")

def network_dns_check(domain: str = "google.com") -> dict:
    """检查DNS污染"""
    result = _run_clash_command(f"dig +short {domain}", timeout=5)
    if result["success"]:
        ips = result["stdout"].strip().split("\n") if result["stdout"] else []
        return {
            "domain": domain,
            "resolved_ips": ips,
            "count": len(ips),
            "is_resolved": len(ips) > 0
        }
    return result

def network_connectivity_test(target: str = "https://www.google.com") -> dict:
    """测试网络连接"""
    result = _run_clash_command(f"curl -I -s -o /dev/null -w '%{{http_code}}' {target}", timeout=10)
    try:
        return {
            "target": target,
            "http_code": int(result["stdout"]) if result["success"] else None,
            "reachable": result["stdout"] == "200" if result["success"] else False
        }
    except:
        return {"success": False, "error": "Failed to parse response"}
```

### 6.4 故障诊断决策树

```
用户报告故障
    │
    ├─→ "节点超时" / "节点全部超时"
    │       ├─→ clash_status (检查服务)
    │       ├─→ network_connectivity_test (测试外网)
    │       ├─→ network_dns_check (检查DNS)
    │       └─→ clash_update → clash_restart (修复流程)
    │
    ├─→ "面板打不开" / "UI加载失败"
    │       ├─→ clash_status (检查服务)
    │       ├─→ clash_ui (获取面板地址)
    │       ├─→ system_port_check 9090 (检查端口)
    │       └─→ clash_secret (检查密钥)
    │
    ├─→ "订阅失效"
    │       ├─→ clash_update <new_url> (更新订阅)
    │       └─→ clash_restart (重启服务)
    │
    ├─→ "代理不工作"
    │       ├─→ clash_status (检查状态)
    │       ├─→ clash_on (确保开启)
    │       ├─→ system_ip_forward (检查转发)
    │       └─→ system_firewall_check (检查防火墙)
    │
    └─→ "TUN模式异常"
            ├─→ clash_tun "off" → clash_tun "on" (重启TUN)
            └─→ clash_restart (重启服务)
```

---

## 七、记忆系统设计

### 7.1 双层记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                    记忆系统                              │
│                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐     │
│  │    短期记忆          │  │    长期记忆          │     │
│  │  (ConversationBuffer)│  │   (SQLite持久化)     │     │
│  │                     │  │                      │     │
│  │  - 当前会话上下文    │  │  - 历史故障记录       │     │
│  │  - 最近N条对话      │  │  - 成功修复案例       │     │
│  │  - 当前任务状态     │  │  - 运维经验沉淀       │     │
│  │                     │  │  - 设备配置快照       │     │
│  └─────────────────────┘  └─────────────────────┘     │
│            ↓                          ↓                  │
│  ┌─────────────────────────────────────────────┐        │
│  │              上下文注入模块                   │        │
│  │   将记忆注入LLM提示词，实现"经验引导推理"      │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 7.2 SQLite数据库结构

```sql
-- 故障记录表
CREATE TABLE fault_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    symptom TEXT NOT NULL,           -- 故障现象
    root_cause TEXT,                 -- 根因
    solution TEXT,                   -- 解决方案
    tools_used TEXT,                 -- 使用的工具序列
    iteration_count INTEGER,         -- 修复尝试次数
    status TEXT DEFAULT 'pending',   -- pending/resolved/failed
    resolved BOOLEAN DEFAULT FALSE
);

-- 运维日志表
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    operation_type TEXT NOT NULL,    -- 操作类型
    command TEXT,                     -- 执行命令
    result TEXT,                      -- 执行结果
    success BOOLEAN
);

-- 经验知识表
CREATE TABLE experience_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fault_pattern TEXT NOT NULL,     -- 故障模式
    symptoms TEXT,                    -- 症状描述
    root_cause_analysis TEXT,        -- 根因分析
    solution TEXT,                    -- 解决方案
    effectiveness_rating INTEGER,    -- 有效性评分 1-5
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0    -- 被使用次数
);
```

### 7.3 记忆检索

```python
def retrieve_relevant_memory(symptom: str, limit: int = 3) -> list[dict]:
    """根据症状检索相关记忆"""
    # 使用简单关键词匹配
    keywords = symptom.split()
    results = db.execute("""
        SELECT * FROM experience_knowledge
        WHERE fault_pattern LIKE ?
           OR symptoms LIKE ?
        ORDER BY (usage_count + effectiveness_rating) DESC
        LIMIT ?
    """, [f"%{keyword}%" for keyword in keywords[:3]] + [limit])
    return results
```

---

## 八、ReAct引擎核心实现

### 8.1 引擎主循环

```python
class ReActEngine:
    """ReAct核心引擎"""

    def __init__(self, llm_manager: LLMManager, tool_registry: ToolRegistry, memory: Memory):
        self.llm = llm_manager
        self.tools = tool_registry
        self.memory = memory
        self.max_iterations = 10

    def run(self, user_input: str) -> dict:
        """执行ReAct循环"""
        messages = [{"role": "user", "content": user_input}]

        # 构建初始上下文（注入记忆）
        memory_context = self.memory.get_context_for_prompt()
        system_msg = SYSTEM_PROMPT.format(
            available_tools_description=self.tools.get_description(),
            memory_context=memory_context
        )
        messages.insert(0, {"role": "system", "content": system_msg})

        steps = []
        final_response = None

        for i in range(self.max_iterations):
            # 1. Reasoning + Acting
            llm_output = self.llm.chat(messages)
            step_data = json.loads(llm_output)

            step = ReActStep(
                step_id=i + 1,
                reasoning=step_data["reasoning"],
                action=step_data["action"],
                action_params=step_data.get("action_params", {}),
                observation="",
                reflection=step_data["reflection"],
                is_complete=False
            )

            # 2. Acting - 执行工具或生成回复
            if step.action == "respond":
                final_response = step.action_params.get("content", "")
                step.is_complete = True
            else:
                tool_result = self.execute_tool(step.action, step.action_params)
                step.observation = str(tool_result)

                # 3. Observation - 将结果加入上下文
                messages.append({"role": "assistant", "content": llm_output})
                messages.append({"role": "user", "content": f"工具执行结果：{step.observation}"})

                # 4. Reflection - 判断是否完成
                reflection_prompt = TOOL_RESULT_PROMPT.format(tool_result=step.observation)
                reflection_result = self.llm.chat(messages + [{"role": "user", "content": reflection_prompt}])
                reflection_data = json.loads(reflection_result)

                step.is_complete = reflection_data["is_complete"]
                if step.is_complete:
                    final_response = reflection_data.get("response", "任务完成")

            steps.append(step)

            if step.is_complete:
                break

        return {
            "response": final_response,
            "steps": steps,
            "iterations": len(steps),
            "success": step.is_complete
        }
```

---

## 九、配置文件

### 9.1 settings.py

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==================== LLM配置 ====================
LLM_CONFIG = {
    # 本地LLM配置（Ollama）
    "local_enabled": os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true",
    "local_url": os.getenv("LOCAL_LLM_URL", "http://localhost:11434"),
    "local_model": os.getenv("LOCAL_LLM_MODEL", "qwen2:1.8b"),

    # DeepSeek API配置
    "deepseek_enabled": bool(os.getenv("DEEPSEEK_API_KEY")),
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),

    # 推理参数
    "temperature": 0.0,  # 运维场景用确定性输出
    "max_tokens": 2048,
}

# ==================== Clash配置（基于nelvko/clash-for-linux-install）====================
CLASH_CONFIG = {
    # 服务名称
    "service_name": "mihomo",  # 或 clash，取决于安装时选择

    # clashctl命令路径（默认已加入PATH）
    "clashctl_path": "clashctl",

    # 面板配置
    "dashboard_port": 9090,
    "dashboard_path": "/usr/local/clash/dashboard",

    # 订阅配置
    "config_dir": "/etc/clash",
    "runtime_config": "/etc/clash/config.yaml",
    "mixin_config": "/etc/clash/mixin.yaml",

    # 默认超时
    "command_timeout": 30,
}

# ==================== ReAct配置 ====================
REACT_CONFIG = {
    "max_iterations": 10,
    "timeout_per_step": 30,
    "early_stop_on_failure": True,
}

# ==================== 记忆系统配置 ====================
MEMORY_CONFIG = {
    "db_path": "data/memory.db",
    "max_conversation_turns": 10,  # 短期记忆保留轮数
    "similarity_threshold": 0.7,     # 经验检索相似度阈值
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": "data/logs/clash-agent.log",
    "max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}

# ==================== 环境变量说明 ====================
# LLM相关：
#   LOCAL_LLM_ENABLED=true/false
#   LOCAL_LLM_URL=http://localhost:11434
#   LOCAL_LLM_MODEL=qwen2:1.8b
#   DEEPSEEK_API_KEY=your-api-key
#
# 日志相关：
#   LOG_LEVEL=DEBUG/INFO/WARNING/ERROR
```

---

## 十、依赖

### requirements.txt

```
# 核心依赖
requests>=2.31.0
sqlite3 (内置)

# 异步支持（可选）
aiohttp>=3.9.0

# 配置管理
pyyaml>=6.0

# 日志
python-dotenv>=1.0.0
```

---

## 十一、用户交互接口

### 11.1 CLI主入口

```bash
# 进入交互模式
python main.py --interactive
python main.py -i

# 单次命令执行
python main.py --cmd "节点全部超时怎么办"

# 指定LLM后端
python main.py --llm local     # 强制本地LLM
python main.py --llm deepseek   # 强制DeepSeek API

# 查看状态
python main.py --status

# 后台常驻模式
python main.py --daemon
```

### 11.2 典型对话示例

```
用户: 节点全部超时了怎么办
Agent: 我来检查一下Clash服务状态...
[执行 clash_status]
服务正在运行，但节点超时。
[执行 network_connectivity_test]
发现DNS污染，解析被干扰。
[执行 clash_subscription_update]
正在更新订阅...
订阅更新成功，共获取15个节点。
[执行 clash_restart]
服务已重启。
验证：节点连接正常，故障已修复。
```

---

## 十二、验证步骤

1. **依赖安装**: `pip install -r requirements.txt`
2. **Ollama本地LLM**: `ollama run qwen2:1.8b`（如使用本地模式）
3. **配置检查**: 确认Clash路径和服务名正确
4. **单元测试**: `python -m pytest tests/`
5. **手动验证**: `python main.py -i` 进入交互测试

---

## 十三、与现有项目的关系

本项目是完全独立的新项目，**不依赖**现有工作区的白酒五步法则监控系统。但项目结构参考了现有代码的：
- 配置管理方式（`config/settings.py`）
- 日志规范
- 目录结构组织

新项目将创建在 `/workspace/clash-agent/` 目录下，与现有代码完全隔离。
