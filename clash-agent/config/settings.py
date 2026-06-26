"""
Clash Agent 主配置文件
基于 nelvko/clash-for-linux-install 环境
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"


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
    "max_tokens": int(os.getenv("MAX_TOKENS", "2048")),

    # 重试配置
    "max_retries": int(os.getenv("LLM_MAX_RETRIES", "3")),
    "retry_base_delay": float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0")),  # 秒
    "retry_max_delay": float(os.getenv("LLM_RETRY_MAX_DELAY", "10.0")),  # 秒
    "timeout": int(os.getenv("LLM_TIMEOUT", "60")),  # 秒
}


# ==================== Clash配置（基于nelvko/clash-for-linux-install）====================
CLASH_CONFIG = {
    # 服务名称
    "service_name": os.getenv("CLASH_SERVICE_NAME", "mihomo"),

    # clashctl命令路径（默认已加入PATH）
    "clashctl_path": os.getenv("CLASHCTL_PATH", "clashctl"),

    # 面板配置
    "dashboard_port": int(os.getenv("DASHBOARD_PORT", "9090")),
    "dashboard_path": os.getenv("DASHBOARD_PATH", "/usr/local/clash/dashboard"),

    # 订阅配置
    "config_dir": os.getenv("CLASH_CONFIG_DIR", "/etc/clash"),
    "runtime_config": os.getenv("CLASH_RUNTIME_CONFIG", "/etc/clash/config.yaml"),
    "mixin_config": os.getenv("CLASH_MIXIN_CONFIG", "/etc/clash/mixin.yaml"),

    # 默认超时（秒）
    "command_timeout": int(os.getenv("CLASH_COMMAND_TIMEOUT", "30")),
}


# ==================== ReAct配置 ====================
REACT_CONFIG = {
    "max_iterations": int(os.getenv("MAX_ITERATIONS", "10")),
    "timeout_per_step": int(os.getenv("TIMEOUT_PER_STEP", "30")),
    "early_stop_on_failure": os.getenv("EARLY_STOP_ON_FAILURE", "true").lower() == "true",
}


# ==================== 记忆系统配置 ====================
MEMORY_CONFIG = {
    "db_path": str(DATA_DIR / "memory.db"),
    "max_conversation_turns": int(os.getenv("MAX_CONVERSATION_TURNS", "10")),
    "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
}


# ==================== 日志配置 ====================
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": str(LOG_DIR / "clash-agent.log"),
    "max_bytes": int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),  # 10MB
    "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
}
