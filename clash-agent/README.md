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

## 开发路线 / Roadmap

### 第一阶段：MVP 闭环（已完成 ✅）
- [x] ReAct 核心引擎（思考→行动→观察→反思）
- [x] 工具注册与执行系统（17+ 运维工具）
- [x] 四大故障场景自愈
- [x] 基础记忆系统（短期 + 长期 SQLite）
- [x] Web UI 可视化控制台
- [x] 实时日志 WebSocket 推送

---

### 第二阶段：能力增强（开发中 🚧）

#### 2.1 工具能力扩展
- [ ] **插件化工具发现**
  - [ ] `tools/plugins/` 插件目录自动扫描
  - [ ] 工具模块动态导入与注册
  - [ ] 插件元数据（名称、描述、版本、权限）
  - [ ] 插件加载/卸载/热重载

- [ ] **Shell 工具箱（Agent 自写工具）**
  - [ ] `create_tool` 元工具：Agent 用 Python 写新工具
  - [ ] 动态编译与注册
  - [ ] 沙箱执行环境（权限限制）
  - [ ] 工具持久化存储

- [ ] **MCP 工具接入**
  - [ ] MCP 协议客户端实现
  - [ ] 外部 MCP Server 工具发现
  - [ ] 动态工具列表同步

#### 2.2 任务规划能力
- [ ] **复杂任务拆解**
  - [ ] 任务分解与子任务规划
  - [ ] 多步骤执行顺序管理
  - [ ] 子任务结果汇总

- [ ] **定时巡检与主动预警**
  - [ ] 定时任务调度器
  - [ ] 健康检查任务（节点可用性、网络、内存、磁盘）
  - [ ] 异常自动告警与自愈触发

#### 2.3 优化与增强
- [ ] 节点智能优选与劣质节点自动剔除
- [ ] 记忆检索相似度匹配（从关键词到向量）
- [ ] 对话历史压缩与摘要

---

### 第三阶段：多 Agent 协作（规划中 📋）

- [ ] **协调者 Agent（Orchestrator）**
  - [ ] 任务分析与专家分配
  - [ ] 子任务结果汇总
  - [ ] 冲突检测与协调

- [ ] **专家 Agent 分工**
  - [ ] 网络专家 Agent（DNS、测速、代理测试）
  - [ ] 系统专家 Agent（进程、资源、日志）
  - [ ] 配置专家 Agent（订阅、规则、面板）

- [ ] Agent 间通信协议
- [ ] 多 Agent 协作对话历史管理

---

### 第四阶段：自进化能力（远期 🔮）

- [ ] **自我反思与改进**
  - [ ] 失败任务自动复盘
  - [ ] 提示词自动优化
  - [ ] 工具参数自动调优

- [ ] **经验知识库自动增长**
  - [ ] 成功案例自动提取经验
  - [ ] 失败案例自动记录根因
  - [ ] 经验有效性评分与排序

- [ ] **自适应策略选择**
  - [ ] 根据故障类型自动选择修复策略
  - [ ] 多方案尝试与最优方案记忆

---

### 第五阶段：高阶智能化（远期 🔮）

- [ ] 智能流量调度与线路择优切换
- [ ] 优选 IP / CDN 测速与自动切换
- [ ] 月度运维报表自动生成
- [ ] Web 控制面板 2.0（拖拽式、可视化工作流）

## 相关项目

- [nelvko/clash-for-linux-install](https://github.com/nelvko/clash-for-linux-install) - Clash 安装脚本
- [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) - Mihomo 内核

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue。
