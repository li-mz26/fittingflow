"""
Agent API - 处理 AI Agent 对话和工具调用
"""
import os
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from pydantic import BaseModel

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class AgentMessage(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[Dict]] = None


class AgentChatRequest(BaseModel):
    messages: List[AgentMessage]
    workflow_context: Optional[str] = None
    stream: bool = False


class WorkflowSkill:
    """内置工作流创建 Skill"""
    
    SYSTEM_PROMPT = """你是 FittingFlow 工作流助手，专门帮助用户创建工作流。

当前工作流技能：

1. **创建工作流**
   - 询问用户工作流名称和用途
   - 建议合适的工作流结构

2. **添加节点**
   - start: 起始节点
   - end: 结束节点  
   - process: 处理节点
   - python: Python代码执行节点
   - if: 条件分支节点

3. **连接节点**
   - 定义节点执行顺序
   - 创建条件分支

4. **运行和调试**
   - 测试工作流
   - 查看执行结果

可用工具：
- create_workflow(name): 创建工作流
- add_node(workflow_name, node_name, node_type, code=None): 添加节点
- connect_nodes(workflow_name, source, target): 连接节点
- run_workflow(workflow_name, input_data): 运行工作流
- get_workflow(name): 获取工作流详情
- list_workflows(): 列出所有工作流

Python节点代码模板：
```python
# data 是输入数据字典
# 将结果赋值给 output 变量

output = {
    "sum": data.get("a", 0) + data.get("b", 0),
    "product": data.get("a", 0) * data.get("b", 0)
}
```

If节点条件模板：
```
data.get('score', 0) > 60
data.get('status') == 'success'
len(data.get('items', [])) > 0
```

回复格式要求：
1. 首先解释你的理解和计划
2. 如果需要用工具，说明要调用什么工具
3. 给用户提供清晰的下一步建议"""

    def __init__(self, workflow_tools):
        self.tools = workflow_tools
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_workflow",
                    "description": "创建一个新工作流",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "工作流名称"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_node",
                    "description": "向工作流添加节点",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_name": {"type": "string", "description": "工作流名称"},
                            "node_name": {"type": "string", "description": "节点名称"},
                            "node_type": {"type": "string", "enum": ["start", "end", "process", "python", "if"]},
                            "code": {"type": "string", "description": "Python代码（python类型必需）"},
                            "condition": {"type": "string", "description": "条件表达式（if类型必需）"}
                        },
                        "required": ["workflow_name", "node_name", "node_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "connect_nodes",
                    "description": "连接两个节点",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_name": {"type": "string", "description": "工作流名称"},
                            "source_node": {"type": "string", "description": "源节点名称"},
                            "target_node": {"type": "string", "description": "目标节点名称"}
                        },
                        "required": ["workflow_name", "source_node", "target_node"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_workflow",
                    "description": "运行工作流",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_name": {"type": "string", "description": "工作流名称"},
                            "input_data": {"type": "object", "description": "输入数据"}
                        },
                        "required": ["workflow_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_workflow",
                    "description": "获取工作流详情",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "工作流名称"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_workflows",
                    "description": "列出所有工作流",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            if tool_name == "create_workflow":
                return self.tools.create_workflow(params["name"])
            elif tool_name == "add_node":
                return self.tools.add_node(
                    workflow_name=params["workflow_name"],
                    node_name=params["node_name"],
                    node_type=params["node_type"],
                    code=params.get("code"),
                    condition=params.get("condition")
                )
            elif tool_name == "connect_nodes":
                return self.tools.connect_nodes(
                    workflow_name=params["workflow_name"],
                    source_node=params["source_node"],
                    target_node=params["target_node"]
                )
            elif tool_name == "run_workflow":
                # 使用线程池运行异步代码
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                def run_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(self.tools.run_workflow(
                            workflow_name=params["workflow_name"],
                            input_data=params.get("input_data", {})
                        ))
                    finally:
                        loop.close()
                
                with ThreadPoolExecutor() as executor:
                    return executor.submit(run_async).result()
            elif tool_name == "get_workflow":
                return self.tools.get_workflow(params["name"])
            elif tool_name == "list_workflows":
                return {"workflows": self.tools.list_workflows()}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}


class OpenAICompatibleAgent:
    """OpenAI 兼容的 Agent 实现"""
    
    def __init__(self):
        self.api_key = os.getenv("AGENT_API_KEY", "")
        self.api_base = os.getenv("AGENT_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("AGENT_MODEL", "gpt-4")
        
        self.client = None
        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base
                )
            except ImportError:
                print("Warning: openai package not installed")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.client is not None and bool(self.api_key)
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """与 LLM 对话"""
        if not self.is_configured():
            yield json.dumps({
                "error": "Agent not configured. Please set AGENT_API_KEY in .env file."
            })
            return
        
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "stream": stream
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            if stream:
                async for chunk in await self.client.chat.completions.create(**params):
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield json.dumps({"content": delta.content}) + "\n"
                    if delta.tool_calls:
                        yield json.dumps({"tool_calls": [tc.model_dump() for tc in delta.tool_calls]}) + "\n"
            else:
                response = await self.client.chat.completions.create(**params)
                msg = response.choices[0].message
                result = {"content": msg.content or ""}
                if msg.tool_calls:
                    result["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
                yield json.dumps(result)
                
        except Exception as e:
            yield json.dumps({"error": str(e)})


class AgentAPI:
    """Agent API 处理器"""
    
    def __init__(self, workflow_tools):
        self.skill = WorkflowSkill(workflow_tools)
        self.agent = OpenAICompatibleAgent()
    
    def is_configured(self) -> bool:
        return self.agent.is_configured()
    
    async def chat(
        self, 
        messages: List[AgentMessage],
        workflow_context: Optional[str] = None,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """处理对话请求"""
        # 构建系统提示
        system_prompt = self.skill.SYSTEM_PROMPT
        if workflow_context:
            system_prompt += f"\n\n当前工作流上下文：\n{workflow_context}"
        
        # 构建消息列表
        chat_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            chat_messages.append({"role": msg.role, "content": msg.content})
        
        # 获取工具
        tools = self.skill.get_available_tools()
        
        # 调用 LLM
        async for chunk in self.agent.chat(chat_messages, tools=tools, stream=stream):
            data = json.loads(chunk)
            
            # 处理工具调用
            if "tool_calls" in data:
                for tc in data["tool_calls"]:
                    if tc.get("function"):
                        func = tc["function"]
                        tool_name = func.get("name", "")
                        try:
                            params = json.loads(func.get("arguments", "{}"))
                        except:
                            params = {}
                        
                        # 执行工具
                        result = self.skill.execute_tool(tool_name, params)
                        
                        # 返回工具结果
                        yield json.dumps({
                            "tool_result": {
                                "tool": tool_name,
                                "params": params,
                                "result": result
                            }
                        }) + "\n"
            
            if "content" in data or "error" in data:
                yield chunk + ("\n" if stream else "")


# 全局 agent api 实例
_agent_api = None

def get_agent_api(workflow_tools):
    """获取 Agent API 实例（单例）"""
    global _agent_api
    if _agent_api is None:
        _agent_api = AgentAPI(workflow_tools)
    return _agent_api
