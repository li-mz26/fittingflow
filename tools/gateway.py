"""
外部工具接口网关 (External Tool Gateway)

统一管理外部工具调用，使得 Python 脚本节点可以方便地引用来扩展外部能力。

功能特性：
1. 工具注册与管理
2. 同步/异步调用
3. 认证支持 (API Key, Bearer Token, Basic Auth)
4. 工具模板快速创建
5. 工具调用日志与监控
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import httpx
import json


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"


@dataclass
class ToolAuth:
    """工具认证配置"""
    auth_type: AuthType = AuthType.NONE
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    def get_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {}
        if self.auth_type == AuthType.API_KEY and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_type == AuthType.BEARER and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.auth_type == AuthType.BASIC and self.username:
            import base64
            creds = base64.b64encode(f"{self.username}:{self.password or ''}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"
        return headers


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    category: str = "general"
    
    # HTTP 配置
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    
    # 认证
    auth: ToolAuth = field(default_factory=ToolAuth)
    
    # 请求模板
    request_template: str = ""  # JSON 模板
    response_mapping: Dict[str, str] = field(default_factory=dict)  # 响应字段映射
    
    # Python 函数（用于自定义工具）
    func: Optional[Callable] = None
    
    # 调用统计
    call_count: int = 0
    last_called: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "method": self.method,
            "url": self.url,
            "call_count": self.call_count,
            "last_called": self.last_called
        }


class ExternalToolGateway:
    """
    外部工具接口网关
    
    使用示例：
    
    gateway = ExternalToolGateway()
    
    # 注册 HTTP 工具
    gateway.register_http_tool(
        name="weather",
        url="https://api.weather.example.com/current",
        description="获取天气信息"
    )
    
    # 注册 Python 函数工具
    @gateway.register_tool("calculator")
    def calculator(a: int, b: int, operation: str = "add") -> Dict[str, Any]:
        if operation == "add":
            return {"result": a + b}
        elif operation == "sub":
            return {"result": a - b}
        elif operation == "mul":
            return {"result": a * b}
        elif operation == "div":
            return {"result": a / b if b != 0 else "error"}
        return {"error": "unknown operation"}
    
    # 调用工具
    result = await gateway.call_tool("weather", {"city": "Beijing"})
    result = gateway.call_tool_sync("calculator", {"a": 10, "b": 5, "operation": "add"})
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._setup_builtin_tools()
    
    def _setup_builtin_tools(self):
        """设置内置工具"""
        # 注册一些常用模板
        self.register_http_tool(
            name="http_get",
            url="",
            description="HTTP GET 请求模板",
            category="template"
        )
        self.register_http_tool(
            name="http_post",
            url="",
            method="POST",
            description="HTTP POST 请求模板",
            category="template"
        )
    
    def register_http_tool(
        self,
        name: str,
        url: str,
        description: str = "",
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[ToolAuth] = None,
        request_template: str = "",
        response_mapping: Optional[Dict[str, str]] = None,
        category: str = "http",
        timeout: float = 30.0
    ) -> Tool:
        """注册 HTTP 工具"""
        tool = Tool(
            name=name,
            description=description,
            url=url,
            method=method.upper(),
            headers=headers or {},
            auth=auth or ToolAuth(),
            request_template=request_template,
            response_mapping=response_mapping or {},
            category=category,
            timeout=timeout
        )
        self.tools[name] = tool
        return tool
    
    def register_tool(self, name: str = None, description: str = "", category: str = "function"):
        """装饰器方式注册 Python 函数工具"""
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or ""
            
            tool = Tool(
                name=tool_name,
                description=tool_desc,
                category=category,
                func=func
            )
            self.tools[tool_name] = tool
            return func
        return decorator
    
    def register_function_tool(
        self,
        name: str,
        func: Callable,
        description: str = ""
    ) -> Tool:
        """注册 Python 函数工具"""
        tool = Tool(
            name=name,
            description=description or func.__doc__ or "",
            category="function",
            func=func
        )
        self.tools[name] = tool
        return tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """列出工具"""
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())
    
    def list_tool_names(self) -> List[str]:
        """列出工具名称"""
        return list(self.tools.keys())
    
    async def call_tool(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        异步调用工具
        
        Args:
            name: 工具名称
            params: 工具参数
            timeout: 超时时间（秒）
        
        Returns:
            工具执行结果
        """
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found", "available_tools": self.list_tool_names()}
        
        # 更新调用统计
        tool.call_count += 1
        tool.last_called = time.time()
        
        params = params or {}
        
        # 调用函数工具
        if tool.func:
            try:
                # 同步函数
                if asyncio.iscoroutinefunction(tool.func):
                    result = await tool.func(**params)
                else:
                    result = tool.func(**params)
                
                return {
                    "success": True,
                    "tool": name,
                    "result": result
                }
            except Exception as e:
                return {
                    "success": False,
                    "tool": name,
                    "error": str(e)
                }
        
        # 调用 HTTP 工具
        try:
            # 准备请求
            url = tool.url
            headers = {**tool.headers, **tool.auth.get_headers()}
            
            # 处理请求模板
            body = None
            if tool.request_template and params:
                try:
                    body = json.dumps(json.loads(tool.request_template) | params)
                except:
                    body = json.dumps(params)
            elif tool.method in ["POST", "PUT", "PATCH"]:
                body = json.dumps(params)
            
            # 构建 URL（支持参数替换）
            if params and "{" in url:
                try:
                    url = url.format(**params)
                except:
                    pass
            
            # 发送请求
            timeout_val = timeout or tool.timeout
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                response = await client.request(
                    method=tool.method,
                    url=url,
                    headers=headers,
                    content=body
                )
                response.raise_for_status()
                
                # 处理响应
                try:
                    data = response.json()
                    
                    # 应用响应映射
                    if tool.response_mapping:
                        result = {}
                        for key, path in tool.response_mapping.items():
                            # 简单的路径解析
                            parts = path.split(".")
                            val = data
                            for p in parts:
                                val = val.get(p, {})
                            result[key] = val
                        data = result
                    
                    return {
                        "success": True,
                        "tool": name,
                        "result": data,
                        "status_code": response.status_code
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "tool": name,
                        "result": response.text,
                        "status_code": response.status_code
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "tool": name,
                "error": "Request timeout"
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "tool": name,
                "error": f"HTTP error: {e.response.status_code}",
                "detail": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "tool": name,
                "error": str(e)
            }
    
    def call_tool_sync(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """同步调用工具"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.call_tool(name, params, timeout))
    
    def remove_tool(self, name: str) -> bool:
        """移除工具"""
        if name in self.tools:
            del self.tools[name]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工具调用统计"""
        tools_data = []
        total_calls = 0
        
        for tool in self.tools.values():
            tools_data.append(tool.to_dict())
            total_calls += tool.call_count
        
        return {
            "total_tools": len(self.tools),
            "total_calls": total_calls,
            "tools": tools_data
        }
    
    def create_from_openapi(
        self,
        spec: Dict[str, Any],
        base_url: str = "",
        auth: Optional[ToolAuth] = None
    ) -> List[Tool]:
        """从 OpenAPI 规范创建工具"""
        tools = []
        base = base_url or spec.get("servers", [{}])[0].get("url", "")
        
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue
                
                tool_name = details.get("operationId", f"{method}_{path.replace('/', '_')}")
                description = details.get("summary", details.get("description", ""))
                
                tool = self.register_http_tool(
                    name=tool_name,
                    url=base + path,
                    description=description,
                    method=method.upper(),
                    auth=auth or ToolAuth()
                )
                tools.append(tool)
        
        return tools


# 全局工具网关实例
_global_gateway: Optional[ExternalToolGateway] = None


def get_gateway() -> ExternalToolGateway:
    """获取全局工具网关实例"""
    global _global_gateway
    if _global_gateway is None:
        _global_gateway = ExternalToolGateway()
    return _global_gateway


# 预定义工具模板
TOOL_TEMPLATES = {
    "http_request": {
        "name": "",
        "url": "",
        "method": "GET",
        "description": "",
        "headers": {},
        "timeout": 30.0
    },
    "weather": {
        "name": "weather",
        "url": "https://api.weatherapi.com/v1/current.json",
        "method": "GET",
        "description": "获取指定城市的天气信息",
        "params": {
            "key": "YOUR_API_KEY",
            "q": "{{city}}",
            "lang": "zh"
        }
    },
    "search": {
        "name": "search",
        "url": "https://api.search.example.com/search",
        "method": "GET",
        "description": "网络搜索",
        "params": {
            "q": "{{query}}",
            "limit": 10
        }
    },
    "translate": {
        "name": "translate",
        "url": "https://api.translate.example.com",
        "method": "POST",
        "description": "文本翻译",
        "body": {
            "text": "{{text}}",
            "source": "{{source_lang}}",
            "target": "{{target_lang}}"
        }
    },
    "calculator": {
        "name": "calculator",
        "description": "数学计算器",
        "function": """
def calculator(a: float, b: float, operation: str = "add") -> dict:
    operations = {
        "add": a + b,
        "sub": a - b,
        "mul": a * b,
        "div": a / b if b != 0 else "Error: division by zero"
    }
    return {"result": operations.get(operation, "Unknown operation")}
"""
    }
}


if __name__ == "__main__":
    # 测试代码
    gateway = ExternalToolGateway()
    
    # 注册一个计算器工具
    @gateway.register_tool("calc")
    def calc(a: int, b: int, op: str = "add") -> dict:
        ops = {"add": a + b, "sub": a - b, "mul": a * b}
        return {"result": ops.get(op, "unknown")}
    
    # 列出工具
    print("可用工具:", gateway.list_tool_names())
    
    # 调用工具
    result = gateway.call_tool_sync("calc", {"a": 10, "b": 5, "op": "add"})
    print("计算结果:", result)
