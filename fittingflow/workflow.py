from typing import Any, Callable, Dict, List, Optional
from collections import deque
from .node import Node, NodeStatus
from .context import Context


class Workflow:
    """工作流编排器"""
    
    def __init__(self, name: str = "workflow"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[str]] = {}  # source -> [targets]
        self.reverse_edges: Dict[str, List[str]] = {}  # target -> [sources]
        self.start_node: Optional[str] = None
    
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
        """执行工作流"""
        context = Context()
        if input_data:
            context.update(input_data)
        
        execution_order = self.topological_sort()
        
        node_outputs: Dict[str, Any] = {}
        
        for node_name in execution_order:
            node = self.nodes[node_name]
            
            # 收集所有前置节点的输出
            inputs = {}
            if node_name in self.reverse_edges:
                for source_name in self.reverse_edges[node_name]:
                    if source_name in node_outputs:
                        source_output = node_outputs[source_name]
                        if isinstance(source_output, dict):
                            inputs.update(source_output)
                        else:
                            inputs[source_name] = source_output
            
            # 执行节点
            result = await node.execute(context, inputs)
            node_outputs[node_name] = result
        
        return {
            "workflow": self.name,
            "status": "completed",
            "context": context.to_dict(),
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [{"source": s, "target": t} for s in self.edges for t in self.edges[s]]
        }
