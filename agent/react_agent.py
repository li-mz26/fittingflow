"""
ReAct Agent - 用于操作 FittingFlow 工作流的 AI Agent

支持的功能：
- 查看、创建、编辑工作流
- 添加各种类型的节点
- 编写 Python 节点代码
- 连接节点构建工作流
- 运行和调试工作流
"""

import json
import asyncio
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from .workflow_tools import WorkflowToolsSync, TOOLS_DESCRIPTION, PYTHON_CODE_TEMPLATE


@dataclass
class ThoughtAction:
    """ReAct 的思考-行动结构"""
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: Optional[str] = None


class ReActWorkflowAgent:
    """
    ReAct Agent - 通过推理和行动循环来操作工作流
    
    使用方法：
        agent = ReActWorkflowAgent()
        result = agent.run("创建一个计算两个数之和的工作流")
    """
    
    def __init__(self, max_iterations: int = 10):
        self.tools = WorkflowToolsSync()
        self.max_iterations = max_iterations
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 注册工具函数
        self.tool_map: Dict[str, Callable] = {
            "list_workflows": self.tools.list_workflows,
            "get_workflow": self.tools.get_workflow,
            "create_workflow": self.tools.create_workflow,
            "delete_workflow": self.tools.delete_workflow,
            "add_node": self.tools.add_node,
            "connect_nodes": self.tools.connect_nodes,
            "run_workflow": self.tools.run_workflow,
        }
    
    def _generate_system_prompt(self) -> str:
        """生成系统提示词"""
        return f"""你是一个 FittingFlow 工作流管理 Agent。你的任务是通过调用工具来帮助用户创建、编辑和调试工作流。

{TOOLS_DESCRIPTION}

{PYTHON_CODE_TEMPLATE}

重要规则：
1. 如果节点类型是 "python"，必须提供 code 参数
2. 如果节点类型是 "if"，必须提供 condition 参数
3. 节点名称要唯一，建议使用有意义的名字
4. 连接节点前确保两个节点都已存在
5. 运行工作流前确保工作流结构完整（有 start 和 end 节点）
6. 遇到错误时尝试修复或提供替代方案

你的回复格式必须是 JSON：
{{
    "thought": "你的思考过程",
    "action": "工具名称 或 'finish'",
    "action_input": {{"参数名": "参数值"}}
}}

当任务完成时，action 设为 "finish"，并在 thought 中总结结果。
"""
    
    def _call_tool(self, action: str, action_input: Dict[str, Any]) -> str:
        """调用工具"""
        if action == "finish":
            return "Task completed"
        
        if action not in self.tool_map:
            return f"Error: Unknown action '{action}'. Available actions: {list(self.tool_map.keys())}"
        
        try:
            result = self.tool_map[action](**action_input)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _parse_response(self, response: str) -> ThoughtAction:
        """解析 LLM 的响应"""
        try:
            # 尝试提取 JSON
            start_idx = response.find("{")
            end_idx = response.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                data = json.loads(json_str)
                return ThoughtAction(
                    thought=data.get("thought", ""),
                    action=data.get("action", ""),
                    action_input=data.get("action_input", {}),
                    observation=None
                )
        except json.JSONDecodeError:
            pass
        
        # 如果解析失败，返回原始内容作为 thought
        return ThoughtAction(
            thought=response,
            action="finish",
            action_input={},
            observation=None
        )
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        调用 LLM - 这是一个占位符，需要接入实际的 LLM API
        可以在这里接入 OpenAI、Claude 或其他模型
        """
        # 这里应该调用实际的 LLM API
        # 暂时返回一个模拟响应
        raise NotImplementedError(
            "需要实现 LLM 调用。请继承此类并重写 _call_llm 方法，"
            "或使用提供的 OpenAI/Claude 实现。"
        )
    
    def run(self, user_input: str, context: Optional[str] = None) -> str:
        """
        运行 Agent 处理用户输入
        
        Args:
            user_input: 用户的自然语言指令
            context: 可选的上下文信息
        
        Returns:
            Agent 的执行结果
        """
        messages = [
            {"role": "system", "content": self._generate_system_prompt()},
        ]
        
        if context:
            messages.append({"role": "user", "content": f"上下文：{context}"})
        
        messages.append({"role": "user", "content": user_input})
        
        iteration = 0
        full_log = []
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # 调用 LLM
            try:
                response = self._call_llm(messages)
            except NotImplementedError:
                return "错误：LLM 未配置。请继承 ReActWorkflowAgent 类并实现 _call_llm 方法。"
            
            # 解析响应
            ta = self._parse_response(response)
            
            full_log.append({
                "iteration": iteration,
                "thought": ta.thought,
                "action": ta.action,
                "action_input": ta.action_input
            })
            
            # 执行动作
            observation = self._call_tool(ta.action, ta.action_input)
            
            full_log[-1]["observation"] = observation
            
            # 如果任务完成
            if ta.action == "finish":
                result = f"## 任务完成\n\n{ta.thought}\n\n### 执行日志\n```json\n{json.dumps(full_log, ensure_ascii=False, indent=2)}\n```"
                return result
            
            # 更新对话历史
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}\n\n基于以上观察，请继续下一步操作。"
            })
        
        return f"达到最大迭代次数 ({self.max_iterations})。最后状态：\n```json\n{json.dumps(full_log, ensure_ascii=False, indent=2)}\n```"
    
    def close(self):
        """关闭资源"""
        self.tools.close()


# OpenAI 实现示例
class OpenAIWorkflowAgent(ReActWorkflowAgent):
    """使用 OpenAI API 的 ReAct Agent"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", max_iterations: int = 10):
        super().__init__(max_iterations)
        self.api_key = api_key
        self.model = model
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content


# Kimi 实现示例
class KimiWorkflowAgent(ReActWorkflowAgent):
    """使用 Kimi API 的 ReAct Agent"""
    
    def __init__(self, api_key: str, model: str = "kimi-coding/k2p5", max_iterations: int = 10):
        super().__init__(max_iterations)
        self.api_key = api_key
        self.model = model
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.moonshot.cn/v1"
            )
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 Kimi API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content


# 简单的命令行交互
if __name__ == "__main__":
    print("FittingFlow ReAct Agent")
    print("=" * 50)
    print()
    print("使用示例：")
    print("1. 创建一个名为 'calculator' 的工作流")
    print("2. 在 workflow_name 中添加两个 Python 节点，一个做加法，一个做乘法")
    print("3. 帮我调试 test_workflow")
    print()
    
    # 这里需要配置 API key
    # agent = KimiWorkflowAgent(api_key="your-api-key")
    # result = agent.run("创建一个计算两个数之和的工作流")
    # print(result)
