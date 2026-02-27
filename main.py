from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn
import json
import os
from fittingflow import Workflow, Node, Context
from tools import ExternalToolGateway, ToolAuth, AuthType

app = FastAPI(title="FittingFlow", version="0.1.0")

# 内存存储工作流
workflows: Dict[str, Workflow] = {}

# 外部工具网关
tool_gateway = ExternalToolGateway()

# 注册一些常用工具
def register_builtin_tools():
    """注册内置工具"""
    
    # HTTP 请求工具（模板）
    tool_gateway.register_http_tool(
        name="http_get",
        url="",
        description="HTTP GET 请求",
        category="http"
    )
    
    tool_gateway.register_http_tool(
        name="http_post", 
        url="",
        method="POST",
        description="HTTP POST 请求",
        category="http"
    )
    
    # 字符串处理工具
    @tool_gateway.register_tool("str_upper")
    def str_upper(text: str) -> dict:
        return {"result": text.upper()}
    
    @tool_gateway.register_tool("str_lower")
    def str_lower(text: str) -> dict:
        return {"result": text.lower()}
    
    @tool_gateway.register_tool("str_len")
    def str_len(text: str) -> dict:
        return {"result": len(text)}
    
    @tool_gateway.register_tool("str_split")
    def str_split(text: str, separator: str = " ") -> dict:
        return {"result": text.split(separator)}
    
    # 数学工具
    @tool_gateway.register_tool("math_add")
    def math_add(a: float, b: float) -> dict:
        return {"result": a + b}
    
    @tool_gateway.register_tool("math_sub")
    def math_sub(a: float, b: float) -> dict:
        return {"result": a - b}
    
    @tool_gateway.register_tool("math_mul")
    def math_mul(a: float, b: float) -> dict:
        return {"result": a * b}
    
    @tool_gateway.register_tool("math_div")
    def math_div(a: float, b: float) -> dict:
        if b == 0:
            return {"error": "Division by zero"}
        return {"result": a / b}
    
    @tool_gateway.register_tool("math_pow")
    def math_pow(base: float, exp: float) -> dict:
        return {"result": base ** exp}
    
    # JSON 工具
    @tool_gateway.register_tool("json_parse")
    def json_parse(text: str) -> dict:
        import json
        try:
            return {"result": json.loads(text)}
        except json.JSONDecodeError as e:
            return {"error": str(e)}
    
    @tool_gateway.register_tool("json_stringify")
    def json_stringify(obj: dict, indent: int = 2) -> dict:
        import json
        return {"result": json.dumps(obj, indent=indent)}

# 启动时注册工具
register_builtin_tools()

# 静态文件
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


class CreateWorkflowRequest(BaseModel):
    name: str


class AddNodeRequest(BaseModel):
    workflow_name: str
    node_name: str
    node_type: str
    config: Optional[Dict[str, Any]] = None
    code: Optional[str] = None  # Python 代码
    condition: Optional[str] = None  # If 条件表达式


class ConnectNodesRequest(BaseModel):
    workflow_name: str
    source_node: str
    target_node: str


class RunWorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Optional[Dict[str, Any]] = None


class ToolRequest(BaseModel):
    name: str
    description: str = ""
    url: str = ""
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    auth_type: str = "none"
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    code: Optional[str] = None  # Python 函数代码


class ToolCallRequest(BaseModel):
    tool_name: str
    params: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"name": "FittingFlow", "version": "0.1.0"}


@app.post("/workflows")
def create_workflow(request: CreateWorkflowRequest):
    """创建工作流"""
    if request.name in workflows:
        raise HTTPException(status_code=400, detail="Workflow already exists")
    workflow = Workflow(name=request.name)
    workflows[request.name] = workflow
    return {"name": request.name, "message": "Workflow created"}


@app.get("/workflows")
def list_workflows():
    """列出所有工作流"""
    return {"workflows": [wf.to_dict() for wf in workflows.values()]}


@app.get("/workflows/{name}")
def get_workflow(name: str):
    """获取工作流详情"""
    if name not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows[name].to_dict()


@app.post("/workflows/{name}/nodes")
def add_node(name: str, request: AddNodeRequest):
    """添加节点到工作流"""
    if name not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[name]
    
    # 根据节点类型创建不同的节点函数
    if request.node_type == "python":
        # Python 代码执行节点
        code = request.code or request.config.get("code", "") if request.config else ""
        default_code = '''# data 是输入数据字典
# 将结果赋值给 output 变量
# 可以通过 tools.call_tool_sync("tool_name", {"param": "value"}) 调用外部工具

output = {"result": data}
'''
        actual_code = code if code else default_code
        
        # 获取全局工具网关
        gateway = tool_gateway
        
        def python_node(data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # 创建同步调用函数
                def call_tool(tool_name: str, params: dict = None):
                    return gateway.call_tool_sync(tool_name, params)
                
                local_vars = {
                    "data": data,
                    "output": {},
                    "tools": gateway,
                    "call_tool": call_tool
                }
                
                exec(actual_code, {}, local_vars)
                return local_vars.get("output", {})
            except Exception as e:
                return {"error": str(e), "output": {}}
        
        node_config = {"node_type": "python", "code": actual_code}
        workflow.add_node(python_node, name=request.node_name, config=node_config)
        
    elif request.node_type == "start":
        # 起始节点
        def start_node(data: Dict[str, Any]) -> Dict[str, Any]:
            return data or {}
        workflow.add_node(start_node, name=request.node_name, config={"node_type": "start"})
        
    elif request.node_type == "end":
        # 结束节点
        def end_node(data: Dict[str, Any]) -> Dict[str, Any]:
            return {"final_output": data}
        workflow.add_node(end_node, name=request.node_name, config={"node_type": "end"})
        
    elif request.node_type == "if":
        # 条件分支节点
        condition = request.condition or (request.config.get("condition", "True") if request.config else "True")
        
        def if_node(data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                local_vars = {"data": data}
                result = eval(condition, {"__builtins__": {}}, local_vars)
                return {
                    "condition_met": bool(result),
                    "condition": condition,
                    "input": data
                }
            except Exception as e:
                return {
                    "condition_met": False,
                    "condition": condition,
                    "error": str(e),
                    "input": data
                }
        
        node_config = {"node_type": "if", "condition": condition}
        workflow.add_node(if_node, name=request.node_name, config=node_config)
    
    return {"message": "Node added", "node": request.node_name}


@app.post("/workflows/{name}/connect")
def connect_nodes(name: str, request: ConnectNodesRequest):
    """连接节点"""
    if name not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[name]
    workflow.connect(request.source_node, request.target_node)
    return {"message": "Nodes connected"}


@app.post("/workflows/{name}/run")
async def run_workflow(name: str, request: RunWorkflowRequest):
    """运行工作流"""
    if name not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows[name]
    result = await workflow.run(request.input_data)
    return result


@app.delete("/workflows/{name}")
def delete_workflow(name: str):
    """删除工作流"""
    if name not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    del workflows[name]
    return {"message": "Workflow deleted"}


# ========== 工具网关 API ==========

@app.get("/tools")
def list_tools():
    """列出所有工具"""
    return tool_gateway.get_stats()


@app.post("/tools")
def register_tool(request: ToolRequest):
    """注册工具"""
    if request.code:
        # Python 函数工具
        try:
            local_vars = {}
            exec(f"def tool_func(): return {request.code}", {}, local_vars)
            func = local_vars["tool_func"]
            tool_gateway.register_function_tool(
                name=request.name,
                func=func,
                description=request.description
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to register function: {str(e)}")
    else:
        # HTTP 工具
        auth = ToolAuth()
        if request.auth_type == "api_key":
            auth = ToolAuth(auth_type=AuthType.API_KEY, api_key=request.api_key)
        elif request.auth_type == "bearer":
            auth = ToolAuth(auth_type=AuthType.BEARER, bearer_token=request.bearer_token)
        
        tool_gateway.register_http_tool(
            name=request.name,
            url=request.url,
            description=request.description,
            method=request.method.upper(),
            headers=request.headers or {},
            auth=auth
        )
    
    return {"message": f"Tool '{request.name}' registered"}


@app.delete("/tools/{name}")
def remove_tool(name: str):
    """删除工具"""
    if tool_gateway.remove_tool(name):
        return {"message": f"Tool '{name}' removed"}
    raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")


@app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """调用工具"""
    result = await tool_gateway.call_tool(request.tool_name, request.params)
    return result


@app.get("/tools/templates")
def list_templates():
    """列出工具模板"""
    from tools import TOOL_TEMPLATES
    return {"templates": TOOL_TEMPLATES}


# ========== Agent API ==========

class AgentMessage(BaseModel):
    role: str
    content: str

class AgentChatRequest(BaseModel):
    messages: List[AgentMessage]
    workflow_context: Optional[str] = None
    stream: bool = False


@app.get("/agent/status")
def agent_status():
    """获取 Agent 配置状态"""
    import os
    api_key = os.getenv("AGENT_API_KEY", "")
    return {
        "configured": bool(api_key),
        "model": os.getenv("AGENT_MODEL", "gpt-4"),
        "api_base": os.getenv("AGENT_API_BASE", "https://api.openai.com/v1")
    }


@app.post("/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """Agent 对话接口"""
    import os
    if not os.getenv("AGENT_API_KEY"):
        raise HTTPException(
            status_code=503, 
            detail="Agent not configured. Please set AGENT_API_KEY in .env file."
        )
    
    # 简单的模拟响应
    last_message = request.messages[-1].content if request.messages else ""
    
    response = {
        "responses": [{
            "content": f"收到消息: {last_message}\n\nAgent 功能需要配置 OpenAI 兼容的 API 才能正常使用。"
        }]
    }
    
    return response


@app.get("/agent/skill")
def get_agent_skill():
    """获取 Agent Skill 描述"""
    return {
        "name": "Workflow Builder",
        "description": "AI-powered workflow creation assistant",
        "tools": [
            {"name": "create_workflow", "description": "Create a new workflow"},
            {"name": "add_node", "description": "Add a node to workflow"},
            {"name": "connect_nodes", "description": "Connect two nodes"},
            {"name": "run_workflow", "description": "Run a workflow"},
            {"name": "get_workflow", "description": "Get workflow details"},
            {"name": "list_workflows", "description": "List all workflows"},
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
