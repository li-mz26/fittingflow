# Workflow Tools - 工作流操作工具封装

from typing import Any, Dict, List, Optional
import httpx
import json

BASE_URL = "http://localhost:8000"


class WorkflowTools:
    """工作流操作工具集"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        try:
            resp = await self.client.get("/workflows")
            resp.raise_for_status()
            data = resp.json()
            return data.get("workflows", [])
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_workflow(self, name: str) -> Dict[str, Any]:
        """获取工作流详情"""
        try:
            resp = await self.client.get(f"/workflows/{name}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e), "name": name}
    
    async def create_workflow(self, name: str) -> Dict[str, Any]:
        """创建工作流"""
        try:
            resp = await self.client.post(
                "/workflows",
                json={"name": name}
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "detail": e.response.text}
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_workflow(self, name: str) -> Dict[str, Any]:
        """删除工作流"""
        try:
            resp = await self.client.delete(f"/workflows/{name}")
            resp.raise_for_status()
            return {"message": f"Workflow '{name}' deleted"}
        except Exception as e:
            return {"error": str(e)}
    
    async def add_node(
        self,
        workflow_name: str,
        node_name: str,
        node_type: str,
        code: Optional[str] = None,
        condition: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """添加节点到工作流"""
        try:
            body = {
                "workflow_name": workflow_name,
                "node_name": node_name,
                "node_type": node_type,
                "config": config or {"node_type": node_type}
            }
            if code:
                body["code"] = code
            if condition:
                body["config"]["condition"] = condition
                
            resp = await self.client.post(
                f"/workflows/{workflow_name}/nodes",
                json=body
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def connect_nodes(
        self,
        workflow_name: str,
        source_node: str,
        target_node: str
    ) -> Dict[str, Any]:
        """连接两个节点"""
        try:
            resp = await self.client.post(
                f"/workflows/{workflow_name}/connect",
                json={
                    "workflow_name": workflow_name,
                    "source_node": source_node,
                    "target_node": target_node
                }
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def run_workflow(
        self,
        workflow_name: str,
        input_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """运行工作流"""
        try:
            resp = await self.client.post(
                f"/workflows/{workflow_name}/run",
                json={
                    "workflow_name": workflow_name,
                    "input_data": input_data or {}
                }
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        await self.client.aclose()


# 同步版本工具
class WorkflowToolsSync:
    """同步版本的工作流操作工具集"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        try:
            resp = self.client.get("/workflows")
            resp.raise_for_status()
            data = resp.json()
            return data.get("workflows", [])
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_workflow(self, name: str) -> Dict[str, Any]:
        """获取工作流详情"""
        try:
            resp = self.client.get(f"/workflows/{name}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e), "name": name}
    
    def create_workflow(self, name: str) -> Dict[str, Any]:
        """创建工作流"""
        try:
            resp = self.client.post("/workflows", json={"name": name})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": str(e), "detail": e.response.text}
        except Exception as e:
            return {"error": str(e)}
    
    def delete_workflow(self, name: str) -> Dict[str, Any]:
        """删除工作流"""
        try:
            resp = self.client.delete(f"/workflows/{name}")
            resp.raise_for_status()
            return {"message": f"Workflow '{name}' deleted"}
        except Exception as e:
            return {"error": str(e)}
    
    def add_node(
        self,
        workflow_name: str,
        node_name: str,
        node_type: str,
        code: Optional[str] = None,
        condition: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """添加节点到工作流"""
        try:
            body = {
                "workflow_name": workflow_name,
                "node_name": node_name,
                "node_type": node_type,
                "config": config or {"node_type": node_type}
            }
            if code:
                body["code"] = code
            if condition:
                body["config"]["condition"] = condition
                
            resp = self.client.post(
                f"/workflows/{workflow_name}/nodes",
                json=body
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def connect_nodes(
        self,
        workflow_name: str,
        source_node: str,
        target_node: str
    ) -> Dict[str, Any]:
        """连接两个节点"""
        try:
            resp = self.client.post(
                f"/workflows/{workflow_name}/connect",
                json={
                    "workflow_name": workflow_name,
                    "source_node": source_node,
                    "target_node": target_node
                }
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run_workflow(
        self,
        workflow_name: str,
        input_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """运行工作流"""
        try:
            resp = self.client.post(
                f"/workflows/{workflow_name}/run",
                json={
                    "workflow_name": workflow_name,
                    "input_data": input_data or {}
                }
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        self.client.close()


# 工具函数描述（用于 Agent）
TOOLS_DESCRIPTION = """
可用的工作流操作工具：

1. list_workflows() - 列出所有工作流
   返回：工作流列表 [{"name": str, "nodes": [...], "edges": [...]}]

2. get_workflow(name: str) - 获取工作流详情
   参数：name - 工作流名称
   返回：工作流详细信息

3. create_workflow(name: str) - 创建工作流
   参数：name - 新工作流名称
   返回：创建结果

4. delete_workflow(name: str) - 删除工作流
   参数：name - 工作流名称
   返回：删除结果

5. add_node(workflow_name, node_name, node_type, code=None, condition=None, config=None) - 添加节点
   参数：
   - workflow_name: 工作流名称
   - node_name: 节点名称
   - node_type: 节点类型 (start, process, python, if, end)
   - code: Python 代码（仅 python 类型需要）
   - condition: 条件表达式（仅 if 类型需要，如 "data.get('score', 0) > 60"）
   - config: 额外配置
   返回：添加结果

6. connect_nodes(workflow_name, source_node, target_node) - 连接节点
   参数：
   - workflow_name: 工作流名称
   - source_node: 源节点名称
   - target_node: 目标节点名称
   返回：连接结果

7. run_workflow(workflow_name, input_data=None) - 运行工作流
   参数：
   - workflow_name: 工作流名称
   - input_data: 输入数据字典
   返回：运行结果
"""

PYTHON_CODE_TEMPLATE = """
编写 Python 节点代码的指南：

1. 输入数据通过 `data` 变量获取，它是字典类型
2. 执行结果必须赋值给 `output` 变量
3. 可以导入标准库模块

示例代码：

# 示例 1：简单的数据处理
output = {
    "sum": data.get("a", 0) + data.get("b", 0),
    "product": data.get("a", 0) * data.get("b", 0)
}

# 示例 2：条件判断
score = data.get("score", 0)
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 60:
    grade = "C"
else:
    grade = "D"
output = {"grade": grade, "passed": score >= 60}

# 示例 3：字符串处理
text = data.get("text", "")
output = {
    "word_count": len(text.split()),
    "char_count": len(text),
    "uppercase": text.upper()
}

# 示例 4：列表处理
items = data.get("items", [])
output = {
    "count": len(items),
    "sum": sum(items),
    "average": sum(items) / len(items) if items else 0,
    "max": max(items) if items else None
}
"""
