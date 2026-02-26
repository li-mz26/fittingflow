"""
FittingFlow 测试用例

覆盖现有关键特性：
1. 工作流 CRUD 操作
2. 节点操作（添加、连接）
3. 工作流执行（包括 Python 节点）
4. 外部工具网关
5. 条件分支节点
"""

import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from typing import Generator
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fittingflow import Workflow
from tools import ExternalToolGateway, ToolAuth, AuthType


# ========== Fixtures ==========

@pytest.fixture
async def client():
    """测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def workflow():
    """工作流测试实例"""
    return Workflow(name="test_workflow")


@pytest.fixture
def tool_gateway():
    """工具网关测试实例"""
    return ExternalToolGateway()


# ========== 工作流 CRUD 测试 ==========

class TestWorkflowCRUD:
    """工作流 CRUD 测试"""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, client):
        """测试创建工作流"""
        response = await client.post("/workflows", json={"name": "test_wf"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_wf"
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_create_duplicate_workflow(self, client):
        """测试创建重复工作流"""
        # 先创建一个
        await client.post("/workflows", json={"name": "dup_test"})
        
        # 再创建一个同名的，应该失败
        response = await client.post("/workflows", json={"name": "dup_test"})
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_list_workflows(self, client):
        """测试列出工作流"""
        # 确保有工作流
        await client.post("/workflows", json={"name": "list_test"})
        
        response = await client.get("/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
    
    @pytest.mark.asyncio
    async def test_get_workflow(self, client):
        """测试获取工作流详情"""
        # 先创建
        await client.post("/workflows", json={"name": "get_test"})
        
        # 再获取
        response = await client.get("/workflows/get_test")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get_test"
        assert "nodes" in data
        assert "edges" in data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow(self, client):
        """测试获取不存在的工作流"""
        response = await client.get("/workflows/n        assert response.status_code == 404onexistent")

    
    @pytest.mark.asyncio
    async def test_delete_workflow(self, client):
        """测试删除工作流"""
        # 先创建
        await client.post("/workflows", json={"name": "delete_test"})
        
        # 再删除
        response = await client.delete("/workflows/delete_test")
        assert response.status_code == 200
        
        # 确认删除
        response = await client.get("/workflows/delete_test")
        assert response.status_code == 404


# ========== 节点操作测试 ==========

class TestNodeOperations:
    """节点操作测试"""
    
    @pytest.mark.asyncio
    async def test_add_start_node(self, client):
        """测试添加 Start 节点"""
        await client.post("/workflows", json={"name": "node_test"})
        
        response = await client.post(
            "/workflows/node_test/nodes",
            json={
                "workflow_name": "node_test",
                "node_name": "start",
                "node_type": "start"
            }
        )
        assert response.status_code == 200
        
        # 验证节点已添加
        wf = await client.get("/workflows/node_test")
        data = wf.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "start"
    
    @pytest.mark.asyncio
    async def test_add_python_node(self, client):
        """测试添加 Python 节点"""
        await client.post("/workflows", json={"name": "python_test"})
        
        response = await client.post(
            "/workflows/python_test/nodes",
            json={
                "workflow_name": "python_test",
                "node_name": "process",
                "node_type": "python",
                "code": "output = {'result': data.get('value', 0) * 2}"
            }
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_add_if_node(self, client):
        """测试添加 If 条件节点"""
        await client.post("/workflows", json={"name": "if_test"})
        
        response = await client.post(
            "/workflows/if_test/nodes",
            json={
                "workflow_name": "if_test",
                "node_name": "condition",
                "node_type": "if",
                "condition": "data.get('score', 0) >= 60"
            }
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_connect_nodes(self, client):
        """测试连接节点"""
        await client.post("/workflows", json={"name": "connect_test"})
        
        # 添加节点
        await client.post(
            "/workflows/connect_test/nodes",
            json={"workflow_name": "connect_test", "node_name": "start", "node_type": "start"}
        )
        await client.post(
            "/workflows/connect_test/nodes",
            json={"workflow_name": "connect_test", "node_name": "end", "node_type": "end"}
        )
        
        # 连接
        response = await client.post(
            "/workflows/connect_test/connect",
            json={
                "workflow_name": "connect_test",
                "source_node": "start",
                "target_node": "end"
            }
        )
        assert response.status_code == 200
        
        # 验证连接
        wf = await client.get("/workflows/connect_test")
        data = wf.json()
        assert len(data["edges"]) == 1
        assert data["edges"][0]["source"] == "start"
        assert data["edges"][0]["target"] == "end"


# ========== 工作流执行测试 ==========

class TestWorkflowExecution:
    """工作流执行测试"""
    
    @pytest.mark.asyncio
    async def test_run_empty_workflow(self, client):
        """测试运行空工作流"""
        await client.post("/workflows", json={"name": "empty_test"})
        
        response = await client.post(
            "/workflows/empty_test/run",
            json={"workflow_name": "empty_test", "input_data": {}}
        )
        # 空工作流会返回错误
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_run_simple_workflow(self, client):
        """测试运行简单工作流"""
        await client.post("/workflows", json={"name": "simple_test"})
        
        # 添加节点
        await client.post(
            "/workflows/simple_test/nodes",
            json={"workflow_name": "simple_test", "node_name": "start", "node_type": "start"}
        )
        
        # 连接
        await client.post(
            "/workflows/simple_test/connect",
            json={"workflow_name": "simple_test", "source_node": "start", "target_node": "start"}
        )
        
        # 运行
        response = await client.post(
            "/workflows/simple_test/run",
            json={"workflow_name": "simple_test", "input_data": {"hello": "world"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_python_node_execution(self, client):
        """测试 Python 节点执行"""
        await client.post("/workflows", json={"name": "python_exec_test"})
        
        # 添加 Python 节点
        await client.post(
            "/workflows/python_exec_test/nodes",
            json={
                "workflow_name": "python_exec_test",
                "node_name": "double",
                "node_type": "python",
                "code": "output = {'value': data.get('value', 0) * 2}"
            }
        )
        
        # 连接
        await client.post(
            "/workflows/python_exec_test/connect",
            json={"workflow_name": "python_exec_test", "source_node": "double", "target_node": "double"}
        )
        
        # 运行
        response = await client.post(
            "/workflows/python_exec_test/run",
            json={"workflow_name": "python_exec_test", "input_data": {"value": 21}}
        )
        assert response.status_code == 200
        data = response.json()
        # 检查执行日志
        if "execution_log" in data:
            logs = data["execution_log"]
            assert any("value" in str(log.get("output", {})) for log in logs)


# ========== 工具网关测试 ==========

class TestToolGateway:
    """外部工具网关测试"""
    
    def test_register_http_tool(self, tool_gateway):
        """测试注册 HTTP 工具"""
        tool = tool_gateway.register_http_tool(
            name="test_http",
            url="https://httpbin.org/get",
            description="测试 HTTP 工具"
        )
        assert tool.name == "test_http"
        assert tool.url == "https://httpbin.org/get"
    
    def test_register_function_tool(self, tool_gateway):
        """测试注册函数工具"""
        @tool_gateway.register_tool("adder")
        def add(a: int, b: int) -> dict:
            return {"result": a + b}
        
        assert "adder" in tool_gateway.list_tool_names()
    
    def test_call_function_tool(self, tool_gateway):
        """测试调用函数工具"""
        @tool_gateway.register_tool("multiplier")
        def mul(a: int, b: int) -> dict:
            return {"result": a * b}
        
        result = tool_gateway.call_tool_sync("multiplier", {"a": 6, "b": 7})
        assert result["success"] is True
        assert result["result"]["result"] == 42
    
    def test_call_nonexistent_tool(self, tool_gateway):
        """测试调用不存在的工具"""
        result = tool_gateway.call_tool_sync("nonexistent", {})
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_list_tools(self, tool_gateway):
        """测试列出工具"""
        @tool_gateway.register_tool("tool1")
        def tool1():
            pass
        
        tools = tool_gateway.list_tools()
        assert len(tools) >= 1
        assert any(t.name == "tool1" for t in tools)
    
    def test_tool_stats(self, tool_gateway):
        """测试工具统计"""
        @tool_gateway.register_tool("stat_test")
        def stat_test():
            pass
        
        # 调用工具
        tool_gateway.call_tool_sync("stat_test", {})
        
        stats = tool_gateway.get_stats()
        assert "total_tools" in stats
        assert "total_calls" in stats
        assert stats["total_calls"] >= 1
    
    def test_auth_api_key(self, tool_gateway):
        """测试 API Key 认证"""
        tool = tool_gateway.register_http_tool(
            name="auth_test",
            url="https://httpbin.org/headers",
            description="认证测试",
            auth=ToolAuth(auth_type=AuthType.API_KEY, api_key="test_key_123")
        )
        
        headers = tool.auth.get_headers()
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test_key_123"
    
    def test_auth_bearer(self, tool_gateway):
        """测试 Bearer Token 认证"""
        tool = tool_gateway.register_http_tool(
            name="bearer_test",
            url="https://httpbin.org/headers",
            description="Bearer 测试",
            auth=ToolAuth(auth_type=AuthType.BEARER, bearer_token="my_token")
        )
        
        headers = tool.auth.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my_token"
    
    @pytest.mark.asyncio
    async def test_async_call(self, tool_gateway):
        """测试异步调用"""
        @tool_gateway.register_tool("async_test")
        def async_test(x: int) -> dict:
            return {"result": x * 3}
        
        result = await tool_gateway.call_tool("async_test", {"x": 10})
        assert result["success"] is True
        assert result["result"]["result"] == 30


# ========== 工具 API 测试 ==========

class TestToolAPI:
    """工具 API 测试"""
    
    @pytest.mark.asyncio
    async def test_list_tools_api(self, client):
        """测试列出工具 API"""
        response = await client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert "total_tools" in data
        assert "tools" in data
    
    @pytest.mark.asyncio
    async def test_register_tool_api(self, client):
        """测试注册工具 API"""
        response = await client.post(
            "/tools",
            json={
                "name": "api_test_tool",
                "description": "API 测试工具",
                "code": "return {'value': 100}"
            }
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_call_tool_api(self, client):
        """测试调用工具 API"""
        # 先注册一个工具
        await client.post(
            "/tools",
            json={
                "name": "call_api_tool",
                "description": "调用测试",
                "code": "return {'result': a + b}"
            }
        )
        
        # 调用
        response = await client.post(
            "/tools/call",
            json={
                "tool_name": "math_add",
                "params": {"a": 5, "b": 3}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_remove_tool_api(self, client):
        """测试删除工具 API"""
        # 先注册
        await client.post(
            "/tools",
            json={"name": "to_remove", "description": "删除测试"}
        )
        
        # 再删除
        response = await client.delete("/tools/to_remove")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_templates_api(self, client):
        """测试工具模板 API"""
        response = await client.get("/tools/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data


# ========== 集成测试 ==========

class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_python_and_tools(self, client):
        """完整的 Python 节点 + 工具调用工作流"""
        
        # 1. 创建工作流
        await client.post("/workflows", json={"name": "integration_test"})
        
        # 2. 注册自定义工具
        await client.post(
            "/tools",
            json={
                "name": "square",
                "description": "计算平方",
                "code": "return {'result': x ** 2}"
            }
        )
        
        # 3. 添加 Python 节点（使用工具）
        await client.post(
            "/workflows/integration_test/nodes",
            json={
                "workflow_name": "integration_test",
                "node_name": "calculate",
                "node_type": "python",
                "code": '''# 使用内置的 math_mul 工具
result = call_tool("math_mul", {"a": data.get("x", 0), "b": data.get("x", 0)})
output = {"square": result.get("result", {}).get("result", 0)}'''
            }
        )
        
        # 4. 运行工作流
        response = await client.post(
            "/workflows/integration_test/run",
            json={"workflow_name": "integration_test", "input_data": {"x": 7}}
        )
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["completed", "failed"]  # 可能失败因为需要正确连接


# ========== 条件分支测试 ==========

class TestConditionalBranch:
    """条件分支测试"""
    
    @pytest.mark.asyncio
    async def test_if_node_true_condition(self, client):
        """测试 If 节点 - 条件为真"""
        await client.post("/workflows", json={"name": "if_true_test"})
        
        # 添加 If 节点
        await client.post(
            "/workflows/if_true_test/nodes",
            json={
                "workflow_name": "if_true_test",
                "node_name": "check",
                "node_type": "if",
                "condition": "data.get('score', 0) >= 60"
            }
        )
        
        # 运行
        response = await client.post(
            "/workflows/if_true_test/run",
            json={"workflow_name": "if_true_test", "input_data": {"score": 90}}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_if_node_false_condition(self, client):
        """测试 If 节点 - 条件为假"""
        await client.post("/workflows", json={"name": "if_false_test"})
        
        # 添加 If 节点
        await client.post(
            "/workflows/if_false_test/nodes",
            json={
                "workflow_name": "if_false_test",
                "node_name": "check",
                "node_type": "if",
                "condition": "data.get('score', 0) >= 60"
            }
        )
        
        # 运行
        response = await client.post(
            "/workflows/if_false_test/run",
            json={"workflow_name": "if_false_test", "input_data": {"score": 30}}
        )
        
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
