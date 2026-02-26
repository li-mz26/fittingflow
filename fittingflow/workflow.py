from typing import Any, Callable, Dict, List, Optional
from collections import deque
from .node import Node, NodeStatus
from .context import Context


class WorkflowStatus:
    """工作流运行状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败


class Workflow:
    """工作流编排器"""
    
    def __init__(self, name: str = "workflow"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[str]] = {}  # source -> [targets]
        self.reverse_edges: Dict[str, List[str]] = {}  # target -> [sources]
        self.start_node: Optional[str] = None
        self.status: str = WorkflowStatus.PENDING
        self.last_run_time: Optional[float] = None
        self.last_error: Optional[str] = None
    
    def node(self, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """装饰器，添加节点到工作流"""
        def decorator(func: Callable):
            node_name = name or func.__name__
            node = Node(func, node_name, config)
            self.nodes[node_name] = node
            
            if self.start_node is None:
                self.start_node = node_name
            
            return node
        return decorator
    
    def add_node(self, func: Callable, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Node:
        """直接添加节点"""
        node_name = name or func.__name__
        node = Node(func, node_name, config)
        self.nodes[node_name] = node
        
        if self.start_node is None:
            self.start_node = node_name
        
        return node
    
    def connect(self, source: str | Node, target: str | Node):
        """连接两个节点"""
        source_name = source.name if isinstance(source, Node) else source
        target_name = target.name if isinstance(target, Node) else target
        
        if source_name not in self.nodes:
            raise ValueError(f"Node '{source_name}' not found")
        if target_name not in self.nodes:
            raise ValueError(f"Node '{target_name}' not found")
        
        if source_name not in self.edges:
            self.edges[source_name] = []
        if target_name not in self.edges[source_name]:
            self.edges[source_name].append(target_name)
        
        if target_name not in self.reverse_edges:
            self.reverse_edges[target_name] = []
        if source_name not in self.reverse_edges[target_name]:
            self.reverse_edges[target_name].append(source_name)
    
    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        in_degree = {name: 0 for name in self.nodes}
        
        for sources in self.reverse_edges.values():
            for source in sources:
                for name in self.nodes:
                    if name == source:
                        continue
        
        # 正确计算入度
        in_degree = {name: 0 for name in self.nodes}
        for source in self.edges:
            for target in self.edges[source]:
                in_degree[target] += 1
        
        queue = deque()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)
        
        result = []
        while queue:
            node_name = queue.popleft()
            result.append(node_name)
            
            if node_name in self.edges:
                for target in self.edges[node_name]:
                    in_degree[target] -= 1
                    if in_degree[target] == 0:
                        queue.append(target)
        
        if len(result) != len(self.nodes):
            raise ValueError("Workflow has a cycle")
        
        return result
    
    async def run(self, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行工作流（支持条件分支）"""
        import time
        
        # 设置运行状态
        self.status = WorkflowStatus.RUNNING
        self.last_run_time = time.time()
        self.last_error = None
        
        context = Context()
        if input_data:
            context.update(input_data)
        
        # 找到起始节点
        if not self.start_node or self.start_node not in self.nodes:
            self.status = WorkflowStatus.FAILED
            self.last_error = "No start node defined"
            return {
                "workflow": self.name,
                "status": self.status,
                "error": self.last_error
            }
        
        # 执行队列和已执行节点
        executed_nodes: Dict[str, Any] = {}
        execution_log: List[Dict] = []
        
        # BFS 执行，但支持条件分支
        queue = deque([self.start_node])
        visited = set()
        
        while queue:
            node_name = queue.popleft()
            
            if node_name in visited:
                continue
            
            if node_name not in self.nodes:
                continue
            
            node = self.nodes[node_name]
            
            # 收集所有前置节点的输出
            inputs = {}
            if node_name in self.reverse_edges:
                for source_name in self.reverse_edges[node_name]:
                    if source_name in executed_nodes:
                        source_output = executed_nodes[source_name]
                        if isinstance(source_output, dict):
                            inputs.update(source_output)
                        else:
                            inputs[source_name] = source_output
            
            # 执行节点
            try:
                result = await node.execute(context, inputs)
                executed_nodes[node_name] = result
                visited.add(node_name)
                
                # 记录执行日志
                log_entry = {
                    "node": node_name,
                    "type": node.config.get("node_type", "unknown"),
                    "status": "completed",
                    "output": result
                }
                
                # 处理条件分支
                if node.config.get("node_type") == "if" and node_name in self.edges:
                    condition_met = result.get("condition_met", False)
                    # 获取该节点的所有下游节点
                    targets = self.edges[node_name]
                    if len(targets) >= 2:
                        # 第一个连接是 True 分支，第二个是 False 分支
                        if condition_met:
                            queue.append(targets[0])
                            log_entry["branch"] = "true"
                        else:
                            queue.append(targets[1])
                            log_entry["branch"] = "false"
                    elif len(targets) == 1:
                        queue.append(targets[0])
                elif node_name in self.edges:
                    # 普通节点，添加所有下游节点
                    for target in self.edges[node_name]:
                        queue.append(target)
                
                execution_log.append(log_entry)
                
            except Exception as e:
                execution_log.append({
                    "node": node_name,
                    "status": "failed",
                    "error": str(e)
                })
                self.status = WorkflowStatus.FAILED
                self.last_error = str(e)
                return {
                    "workflow": self.name,
                    "status": self.status,
                    "error": str(e),
                    "execution_log": execution_log,
                    "nodes": {name: node.to_dict() for name, node in self.nodes.items()}
                }
        
        self.status = WorkflowStatus.COMPLETED
        return {
            "workflow": self.name,
            "status": self.status,
            "context": context.to_dict(),
            "execution_log": execution_log,
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [{"source": s, "target": t} for s in self.edges for t in self.edges[s]],
            "status": self.status,
            "last_run_time": self.last_run_time,
            "last_error": self.last_error
        }
