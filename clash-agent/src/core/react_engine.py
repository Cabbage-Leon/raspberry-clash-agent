"""
ReAct引擎 - 核心思考-行动-观察-反思循环
"""

import json
from typing import Optional
from dataclasses import asdict

from config.settings import REACT_CONFIG
from config.prompts import SYSTEM_PROMPT, TOOL_RESULT_PROMPT
from src.core.llm_adapter import LLMManager
from src.core.tool_registry import ToolRegistry, global_tool_registry
from src.core.memory import Memory
from src.models.schemas import ReActStep, ReActResult
from src.utils.logger import get_logger

logger = get_logger()


class ReActEngine:
    """ReAct核心引擎"""

    def __init__(
        self,
        llm_manager: LLMManager,
        tool_registry: ToolRegistry,
        memory: Memory
    ):
        self.llm = llm_manager
        self.tools = tool_registry
        self.memory = memory
        self.max_iterations = REACT_CONFIG["max_iterations"]
        self.early_stop = REACT_CONFIG["early_stop_on_failure"]

    def run(self, user_input: str) -> ReActResult:
        """
        执行ReAct循环

        Args:
            user_input: 用户输入

        Returns:
            ReActResult对象
        """
        logger.info(f"开始处理用户请求: {user_input}")

        # 添加用户消息到记忆
        self.memory.add_conversation("user", user_input)

        # 构建初始消息列表
        messages = [{"role": "user", "content": user_input}]

        # 构建系统提示词
        system_msg = self._build_system_prompt()
        messages.insert(0, {"role": "system", "content": system_msg})

        steps = []
        final_response = None
        consecutive_failures = 0

        for i in range(self.max_iterations):
            step_num = i + 1
            logger.info(f"=== ReAct循环第 {step_num} 步 ===")

            # 1. Reasoning + Acting: 调用LLM获取下一步行动
            try:
                llm_output = self.llm.chat(messages)
                logger.debug(f"LLM输出: {llm_output[:500]}...")
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                final_response = f"LLM调用失败: {e}"
                break

            # 解析LLM输出
            try:
                step_data = json.loads(llm_output)
            except json.JSONDecodeError:
                logger.error(f"LLM输出格式错误，非JSON: {llm_output[:200]}")
                # 尝试提取JSON
                try:
                    start = llm_output.find("{")
                    end = llm_output.rfind("}") + 1
                    if start >= 0 and end > start:
                        step_data = json.loads(llm_output[start:end])
                    else:
                        final_response = "无法解析LLM响应格式"
                        break
                except:
                    final_response = "无法解析LLM响应格式"
                    break

            # 创建步骤对象
            step = ReActStep(
                step_id=step_num,
                reasoning=step_data.get("reasoning", ""),
                action=step_data.get("action"),
                action_params=step_data.get("action_params", {}),
                observation="",
                reflection=step_data.get("reflection", ""),
                is_complete=False
            )

            logger.info(f"推理: {step.reasoning[:100]}...")
            logger.info(f"行动: {step.action}, 参数: {step.action_params}")

            # 2. Acting: 执行工具或生成回复
            if step.action == "respond" or step.action is None:
                # 直接回复用户
                step.is_complete = True
                final_response = step.action_params.get("content", step.reasoning)
                logger.info(f"任务完成（直接回复）: {final_response[:100]}...")
            else:
                # 执行工具
                tool_result = self.execute_tool(step.action, step.action_params)
                step.observation = str(tool_result)

                logger.info(f"工具执行结果: {str(tool_result)[:200]}...")

                # 3. Observation: 将结果加入上下文
                messages.append({"role": "assistant", "content": llm_output})
                messages.append({
                    "role": "user",
                    "content": f"工具执行结果：{step.observation}\n\n请判断任务是否完成，是否需要继续操作。"
                })

                # 4. Reflection: 判断是否完成
                try:
                    reflection_result = self.llm.chat(messages)
                    reflection_data = json.loads(reflection_result)

                    step.is_complete = reflection_data.get("is_complete", False)
                    step.reflection = reflection_data.get("observation", "")

                    if step.is_complete:
                        final_response = reflection_data.get("response", "任务已完成")
                        logger.info(f"任务完成: {final_response[:100]}...")

                        # 检查工具执行是否实际成功
                        if isinstance(tool_result, dict):
                            if not tool_result.get("success", True):
                                consecutive_failures += 1
                                if self.early_stop and consecutive_failures >= 2:
                                    final_response = f"工具执行失败，已连续失败{consecutive_failures}次，终止循环"
                                    step.is_complete = False
                                    logger.warning(final_response)
                                    break
                            else:
                                consecutive_failures = 0
                    else:
                        consecutive_failures = 0

                except Exception as e:
                    logger.error(f"反思阶段失败: {e}")
                    step.reflection = f"反思失败: {e}"

            steps.append(step)

            if step.is_complete:
                break

        # 如果达到最大迭代次数仍未完成
        if final_response is None:
            final_response = f"已达到最大迭代次数({self.max_iterations})，任务未能完成"

        # 添加助手回复到记忆
        self.memory.add_conversation("assistant", final_response)

        logger.info(f"ReAct循环结束，共 {len(steps)} 步")

        return ReActResult(
            response=final_response,
            steps=steps,
            iterations=len(steps),
            success=steps[-1].is_complete if steps else False,
            final_state="completed" if steps and steps[-1].is_complete else "max_iterations" if len(steps) >= self.max_iterations else "failed"
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        memory_context = self.memory.get_context_for_prompt()
        tools_description = self.tools.get_description()

        return SYSTEM_PROMPT.format(
            available_tools_description=tools_description,
            memory_context=memory_context
        )

    def execute_tool(self, tool_name: str, params: dict) -> dict:
        """
        执行工具

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            工具执行结果
        """
        if not self.tools.has_tool(tool_name):
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}"
            }

        try:
            result = self.tools.execute(tool_name, **params)
            return result
        except Exception as e:
            logger.error(f"工具执行异常: {tool_name}, {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def diagnose(self, user_input: str) -> dict:
        """
        快速诊断（不进入完整ReAct循环）

        Args:
            user_input: 用户描述的症状

        Returns:
            诊断结果
        """
        from config.prompts import INITIAL_DIAGNOSIS_PROMPT

        messages = [
            {"role": "system", "content": "你是一个专业的Clash网关运维助手。"},
            {"role": "user", "content": INITIAL_DIAGNOSIS_PROMPT.format(user_input=user_input)}
        ]

        try:
            result = self.llm.chat(messages)
            diagnosis = json.loads(result)
            return {
                "success": True,
                "diagnosis": diagnosis
            }
        except Exception as e:
            logger.error(f"诊断失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
