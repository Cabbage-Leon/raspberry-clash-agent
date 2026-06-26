"""
ReAct引擎 - 核心思考-行动-观察循环
优化版：每轮仅一次LLM调用，支持实时回调
"""

import json
import time
from typing import Optional, Callable
from dataclasses import asdict

from config.settings import REACT_CONFIG
from config.prompts import SYSTEM_PROMPT
from src.core.llm_adapter import LLMManager
from src.core.tool_registry import ToolRegistry, global_tool_registry
from src.core.memory import Memory
from src.models.schemas import ReActStep, ReActResult
from src.utils.logger import get_logger

logger = get_logger()


class ReActEngine:
    """ReAct核心引擎 - 优化版"""

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
        self.step_callbacks: list[Callable] = []

    def add_step_callback(self, callback: Callable):
        """添加步骤回调，每步完成时调用"""
        self.step_callbacks.append(callback)

    def _fire_callback(self, event: str, data: dict):
        """触发回调"""
        for cb in self.step_callbacks:
            try:
                cb(event, data)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    def run(self, user_input: str) -> ReActResult:
        """
        执行ReAct循环（同步版本）

        优化点：
        - 每轮只调用一次LLM
        - 合并推理和反思判断
        - 支持实时回调推送
        """
        logger.info(f"开始处理用户请求: {user_input}")

        self.memory.add_conversation("user", user_input)

        messages = [{"role": "user", "content": user_input}]

        system_msg = self._build_system_prompt()
        messages.insert(0, {"role": "system", "content": system_msg})

        steps = []
        final_response = None
        consecutive_failures = 0

        self._fire_callback("start", {"user_input": user_input})

        for i in range(self.max_iterations):
            step_num = i + 1
            logger.info(f"=== ReAct循环第 {step_num} 步 ===")

            self._fire_callback("step_start", {"step": step_num})

            try:
                llm_output = self.llm.chat(messages)
                logger.debug(f"LLM输出: {llm_output[:500]}...")
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                final_response = f"LLM调用失败: {e}"
                self._fire_callback("error", {"message": final_response})
                break

            step_data = self._parse_llm_output(llm_output)
            if step_data is None:
                final_response = "无法解析LLM响应格式"
                self._fire_callback("error", {"message": final_response})
                break

            step = ReActStep(
                step_id=step_num,
                reasoning=step_data.get("reasoning", ""),
                action=step_data.get("action"),
                action_params=step_data.get("action_params", {}),
                observation="",
                reflection="",
                is_complete=step_data.get("is_complete", False)
            )

            logger.info(f"推理: {step.reasoning[:100]}...")
            logger.info(f"行动: {step.action}, 参数: {step.action_params}")

            self._fire_callback("reasoning", {
                "step": step_num,
                "reasoning": step.reasoning,
                "action": step.action,
                "action_params": step.action_params
            })

            if step.action == "respond" or step.is_complete:
                step.is_complete = True
                final_response = step.action_params.get("content") or step_data.get("response") or step.reasoning
                step.reflection = "任务完成，给出最终回复"
                logger.info(f"任务完成: {final_response[:100]}...")
                self._fire_callback("complete", {
                    "step": step_num,
                    "response": final_response
                })
            else:
                self._fire_callback("tool_start", {
                    "step": step_num,
                    "tool": step.action,
                    "params": step.action_params
                })

                tool_result = self.execute_tool(step.action, step.action_params)
                step.observation = str(tool_result)

                logger.info(f"工具执行结果: {str(tool_result)[:200]}...")

                self._fire_callback("tool_result", {
                    "step": step_num,
                    "tool": step.action,
                    "result": tool_result
                })

                is_success = True
                if isinstance(tool_result, dict):
                    is_success = tool_result.get("success", True)
                    if not is_success:
                        consecutive_failures += 1
                        if self.early_stop and consecutive_failures >= 3:
                            final_response = f"工具连续失败{consecutive_failures}次，终止执行。最后错误: {tool_result.get('error', '未知错误')}"
                            step.is_complete = False
                            step.reflection = f"连续失败{consecutive_failures}次，提前终止"
                            logger.warning(final_response)
                            steps.append(step)
                            self._fire_callback("error", {"message": final_response})
                            break
                    else:
                        consecutive_failures = 0

                step.reflection = "工具执行完成，将根据结果决定下一步" if is_success else "工具执行失败，需要调整策略"

                messages.append({"role": "assistant", "content": llm_output})
                messages.append({
                    "role": "user",
                    "content": f"工具 {step.action} 执行结果：\n{step.observation}\n\n请根据结果决定下一步行动。"
                })

            steps.append(step)

            if step.is_complete:
                break

        if final_response is None:
            final_response = f"已达到最大迭代次数({self.max_iterations})，任务未能完成"
            self._fire_callback("max_iterations", {"message": final_response})

        self.memory.add_conversation("assistant", final_response)

        logger.info(f"ReAct循环结束，共 {len(steps)} 步")

        self._fire_callback("end", {
            "iterations": len(steps),
            "success": steps[-1].is_complete if steps else False,
            "response": final_response
        })

        return ReActResult(
            response=final_response,
            steps=steps,
            iterations=len(steps),
            success=steps[-1].is_complete if steps else False,
            final_state="completed" if steps and steps[-1].is_complete else "max_iterations" if len(steps) >= self.max_iterations else "failed"
        )

    def _parse_llm_output(self, llm_output: str) -> Optional[dict]:
        """解析LLM输出，支持多种格式"""
        if not llm_output or not llm_output.strip():
            logger.error("LLM返回空响应")
            return None

        try:
            return json.loads(llm_output)
        except json.JSONDecodeError:
            pass

        try:
            start = llm_output.find("{")
            end = llm_output.rfind("}") + 1
            if start >= 0 and end > start:
                extracted = llm_output[start:end]
                return json.loads(extracted)
        except Exception:
            pass

        try:
            lines = llm_output.strip().split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("{"):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip().startswith("}") and in_json:
                    break
            if json_lines:
                return json.loads("\n".join(json_lines))
        except Exception:
            pass

        logger.error(f"无法解析LLM输出: {llm_output[:300]}")
        return None

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        memory_context = self.memory.get_context_for_prompt()
        tools_description = self.tools.get_description()

        return SYSTEM_PROMPT.format(
            available_tools_description=tools_description,
            memory_context=memory_context
        )

    def execute_tool(self, tool_name: str, params: dict) -> dict:
        """执行工具"""
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
        """快速诊断（不进入完整ReAct循环）"""
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
