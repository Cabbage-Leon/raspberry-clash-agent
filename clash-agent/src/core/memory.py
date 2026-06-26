"""
记忆系统 - 短期会话记忆 + 长期SQLite持久化
"""

import sqlite3
from typing import Optional, list
from datetime import datetime
from pathlib import Path
from collections import deque

from config.settings import MEMORY_CONFIG
from src.models.schemas import (
    FaultRecord, OperationLog, ExperienceKnowledge,
    ConversationMessage, FaultStatus
)
from src.utils.logger import get_logger

logger = get_logger()


class Memory:
    """记忆系统 - 短期+长期双重记忆"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or MEMORY_CONFIG["db_path"]
        self.max_conversation_turns = MEMORY_CONFIG["max_conversation_turns"]

        # 短期记忆：会话缓冲区
        self.conversation_buffer: deque[ConversationMessage] = deque(
            maxlen=self.max_conversation_turns * 2  # user + assistant
        )

        # 初始化数据库
        self._init_db()

    def _init_db(self):
        """初始化SQLite数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 故障记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fault_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symptom TEXT NOT NULL,
                root_cause TEXT,
                solution TEXT,
                tools_used TEXT,
                iteration_count INTEGER,
                status TEXT DEFAULT 'pending',
                resolved INTEGER DEFAULT 0
            )
        """)

        # 运维日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                operation_type TEXT NOT NULL,
                command TEXT,
                result TEXT,
                success INTEGER
            )
        """)

        # 经验知识表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fault_pattern TEXT NOT NULL,
                symptoms TEXT,
                root_cause_analysis TEXT,
                solution TEXT,
                effectiveness_rating INTEGER DEFAULT 3,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"记忆数据库初始化完成: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==================== 短期记忆操作 ====================

    def add_conversation(self, role: str, content: str):
        """添加会话消息"""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        self.conversation_buffer.append(message)

    def get_conversation_history(self) -> list[ConversationMessage]:
        """获取会话历史"""
        return list(self.conversation_buffer)

    def get_context_for_prompt(self) -> str:
        """构建用于LLM提示的上下文"""
        history = self.get_conversation_history()
        if not history:
            return "暂无会话历史"

        lines = ["## 最近的会话历史:\n"]
        for msg in history[-6:]:  # 最近3轮对话
            role_name = "用户" if msg.role == "user" else "助手"
            lines.append(f"**{role_name}**: {msg.content[:200]}")

        # 添加相关故障经验
        lines.append("\n## 相关故障经验:")
        last_user_msg = ""
        for msg in reversed(history):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        if last_user_msg:
            experiences = self.retrieve_relevant_memory(last_user_msg, limit=2)
            if experiences:
                for exp in experiences:
                    lines.append(f"- [{exp['fault_pattern']}] {exp['solution'][:100]}...")
            else:
                lines.append("- 暂无相关经验")

        return "\n".join(lines)

    def clear_conversation(self):
        """清空会话记忆"""
        self.conversation_buffer.clear()

    # ==================== 长期记忆操作 ====================

    def add_fault_record(self, record: FaultRecord) -> int:
        """添加故障记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fault_records
            (symptom, root_cause, solution, tools_used, iteration_count, status, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.symptom, record.root_cause, record.solution,
            record.tools_used, record.iteration_count, record.status, record.resolved
        ))
        fault_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return fault_id

    def update_fault_record(self, fault_id: int, **kwargs):
        """更新故障记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        for key, value in kwargs.items():
            cursor.execute(
                f"UPDATE fault_records SET {key} = ? WHERE id = ?",
                (value, fault_id)
            )
        conn.commit()
        conn.close()

    def add_operation_log(self, log: OperationLog):
        """添加运维日志"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO operation_logs (operation_type, command, result, success)
            VALUES (?, ?, ?, ?)
        """, (log.operation_type, log.command, log.result, log.success))
        conn.commit()
        conn.close()

    def add_experience(self, experience: ExperienceKnowledge):
        """添加经验知识"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO experience_knowledge
            (fault_pattern, symptoms, root_cause_analysis, solution, effectiveness_rating)
            VALUES (?, ?, ?, ?, ?)
        """, (
            experience.fault_pattern, experience.symptoms,
            experience.root_cause_analysis, experience.solution,
            experience.effectiveness_rating
        ))
        conn.commit()
        conn.close()

    def retrieve_relevant_memory(self, symptom: str, limit: int = 3) -> list[dict]:
        """根据症状检索相关记忆"""
        conn = self._get_connection()
        cursor = conn.cursor()

        keywords = symptom.split()[:3]  # 取前3个关键词

        # 构建模糊查询
        conditions = " OR ".join(["fault_pattern LIKE ? OR symptoms LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords for _ in range(2)]

        cursor.execute(f"""
            SELECT * FROM experience_knowledge
            WHERE {conditions}
            ORDER BY (usage_count + effectiveness_rating) DESC
            LIMIT ?
        """, params + [limit])

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def increment_experience_usage(self, experience_id: int):
        """增加经验使用次数"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE experience_knowledge SET usage_count = usage_count + 1 WHERE id = ?",
            (experience_id,)
        )
        conn.commit()
        conn.close()

    def get_recent_faults(self, limit: int = 10) -> list[dict]:
        """获取最近的故障记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM fault_records
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_statistics(self) -> dict:
        """获取记忆统计"""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}

        # 总故障数
        cursor.execute("SELECT COUNT(*) FROM fault_records")
        stats["total_faults"] = cursor.fetchone()[0]

        # 已解决故障数
        cursor.execute("SELECT COUNT(*) FROM fault_records WHERE resolved = 1")
        stats["resolved_faults"] = cursor.fetchone()[0]

        # 总经验数
        cursor.execute("SELECT COUNT(*) FROM experience_knowledge")
        stats["total_experiences"] = cursor.fetchone()[0]

        # 最近7天的故障数
        cursor.execute("""
            SELECT COUNT(*) FROM fault_records
            WHERE timestamp >= datetime('now', '-7 days')
        """)
        stats["faults_last_7_days"] = cursor.fetchone()[0]

        conn.close()
        return stats
