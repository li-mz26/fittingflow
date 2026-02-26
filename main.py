from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uvicorn
import json
import os
from fittingflow import Workflow, Node, Context

app = FastAPI(title="FittingFlow", version="0.1.0")

# 内存存储工作流
workflows: Dict[str, Workflow] = {}

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


class ConnectNodesRequest(BaseModel):
    workflow_name: str
    source_node: str
    target_node: str


class RunWorkflowRequest(BaseModel):
    workflow_name: str
    input_data: Optional[Dict[str, Any]] = None


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
    
    # 创建简单的节点函数
    def generic_node(data: Dict[str, Any]) -> Dict[str, Any]:
        return {**data, "_node_type": request.node_type}
    
    workflow.add_node(generic_node, name=request.node_name, config=request.config)
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
