# Clash Agent

> 树莓派 Clash 全屋网关运维 AI Agent - 基于 ReAct 架构的自动化运维智能体

## 项目简介

Clash Agent 是一款专为树莓派 Clash/Mihomo 网关设计的 **垂直领域 AI 运维智能体**。基于自研轻量级 ReAct 架构，实现故障自动诊断、自动修复、自动校验，彻底告别人工运维。

### 核心特性

- **自研 ReAct 架构**：思考 → 行动 → 观察 → 反思四阶段闭环
- **本地 LLM**：支持 Qwen/Ollama 本地离线推理，保护隐私
- **17+ 运维工具**：服务控制、订阅管理、网络诊断、系统检查
- **长期记忆**：SQLite 持久化存储，故障经验积累
- **Web 可视化**：实时监控、工具执行、智能对话、日志查看

## 系统要求

- Python 3.10+
- 树莓派 ARM64 / Linux / macOS / Windows
- Clash/Mihomo 环境（基于 nelvko/clash-for-linux-install）
- 可选：Ollama 本地 LLM 或 DeepSeek API

## 快速开始

### 1. 安装依赖

```bash
cd clash-agent
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 配置 LLM 和 Clash 相关参数
```

主要配置项：

```env
# LLM 配置
LOCAL_LLM_ENABLED=true
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=qwen2:1.8b
# DEEPSEEK_API_KEY=your-api-key

# Clash 配置
CLASH_SERVICE_NAME=mihomo
CLASHCTL_PATH=clashctl
```

### 3. 启动服务

```bash
# Web UI 模式（推荐）
python main.py --web --port 5000

# CLI 交互模式
python main.py -i

# 单次命令
python main.py --cmd "节点超时怎么办"
```

访问 `http://localhost:5000` 打开 Web 控制台。

## 功能演示

### Web 控制台

```
┌─────────────────────────────────────────────────────────────┐
│  Clash Agent Web UI                                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 仪表盘   │ │ 工具管理  │ │ 智能对话  │ │ 运行日志  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 支持的故障场景

| 场景 | 自动处理 |
|------|----------|
| 节点超时 | 检查服务状态 → 更新订阅 → 重启服务 |
| 面板打不开 | 检查端口 → 验证密钥 → 修复配置 |
| 订阅失效 | 更新订阅链接 → 重启服务 |
| 代理不工作 | 检查服务 → 验证IP转发 → 检查防火墙 |
| DNS 污染 | DNS 检查 → 修复解析 |

### 对话示例

```
你: 节点全部超时了怎么办
Agent: 正在检查 Clash 服务状态...
[clash_status] 服务运行正常
[network_connectivity_test] 外网连接正常
[network_dns_check] 发现 DNS 污染
[clash_update] 正在更新订阅...
订阅更新成功，共获取 15 个节点
[clash_restart] 服务已重启
验证：节点连接正常，故障已修复 ✓
```

## 项目架构

```
clash-agent/
├── config/                 # 配置模块
│   ├── settings.py        # 主配置
│   └── prompts.py         # ReAct 提示词
├── src/
│   ├── core/             # 核心模块
│   │   ├── react_engine.py    # ReAct 引擎
│   │   ├── llm_adapter.py     # LLM 适配器
│   │   ├── tool_registry.py   # 工具注册表
│   │   └── memory.py          # 记忆系统
│   ├── tools/            # 运维工具集
│   │   ├── clash_tools.py     # Clash 运维
│   │   ├── network_tools.py   # 网络诊断
│   │   └── system_tools.py    # 系统工具
│   ├── models/           # 数据模型
│   └── utils/            # 工具函数
├── web/                  # Web 可视化
│   ├── templates/        # HTML 模板
│   └── static/           # CSS/JS
├── data/                 # 数据目录
│   ├── memory.db         # SQLite 记忆库
│   └── logs/             # 日志文件
├── main.py               # CLI 入口
└── web_server.py         # Web 入口
```

## 工具列表

### Clash 运维工具

| 工具 | 功能 |
|------|------|
| `clash_status` | 检查服务状态 |
| `clash_on` | 开启代理 |
| `clash_off` | 关闭代理 |
| `clash_restart` | 重启服务 |
| `clash_update` | 更新订阅 |
| `clash_ui` | 获取面板信息 |
| `clash_secret` | 管理密钥 |
| `clash_tun` | TUN 模式控制 |
| `clash_proxy` | 系统代理开关 |
| `clash_version` | 版本信息 |

### 网络诊断工具

| 工具 | 功能 |
|------|------|
| `network_dns_check` | DNS 污染检查 |
| `network_connectivity_test` | 网络连接测试 |
| `network_proxy_test` | 代理连接测试 |
| `network_latency_test` | 延迟测试 |

### 系统工具

| 工具 | 功能 |
|------|------|
| `system_port_check` | 端口占用检查 |
| `system_ip_forward` | IP 转发检查 |
| `system_firewall_check` | 防火墙规则检查 |
| `system_info` | 系统信息 |
| `system_memory` | 内存使用 |
| `system_disk` | 磁盘使用 |

## 技术方案

### ReAct 循环

```
┌────────────────────────────────────────────────────────────┐
│                      ReAct 循环                             │
│                                                            │
│   Reasoning ──→ Acting ──→ Observation ──→ Reflection     │
│       ↑                                            │       │
│       └────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────┘
```

### LLM 支持

| 模式 | 说明 |
|------|------|
| 本地 Ollama | Qwen2:1.8B / 其他模型，完全离线 |
| DeepSeek API | 云端增强，可选 |

### 记忆系统

- **短期记忆**：会话上下文缓冲
- **长期记忆**：SQLite 持久化
  - 故障记录表
  - 运维日志表
  - 经验知识表

## 开发路线

- [x] 第一阶段：MVP 闭环
  - [x] ReAct 核心引擎
  - [x] 工具注册与执行
  - [x] 四大故障自愈
  - [x] 基础记忆系统
  - [x] Web UI

- [ ] 第二阶段：能力增强
  - [ ] 复杂任务拆解
  - [ ] 定时巡检
  - [ ] 节点智能优选

- [ ] 第三阶段：高阶智能化
  - [ ] 流量调度
  - [ ] 月度报表
  - [ ] Web 控制面板

## 相关项目

- [nelvko/clash-for-linux-install](https://github.com/nelvko/clash-for-linux-install) - Clash 安装脚本
- [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) - Mihomo 内核

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
