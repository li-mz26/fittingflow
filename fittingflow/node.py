from typing import Any, Callable, Dict, Optional
from enum import Enum
from .context import Context


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Node:
    """工作流节点"""
    
    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.func = func
        self.name = name or func.__name__
        self.config = config or {}
        self.status = NodeStatus.PENDING
        self.error: Optional[Exception] = None
        self.input_data: Optional[Dict[str, Any]] = None
        self.output_data: Optional[Dict[str, Any]] = None
    
    async def execute(self, context: Context, input_data: Optional[Dict[str, Any]] = None) -> Any:
        """执行节点"""
        self.status = NodeStatus.RUNNING
        self.input_data = input_data or {}
        
        try:
            # 合并上下文数据和输入数据
            data = {**context.to_dict(), **self.input_data}
            
            # 执行节点函数
            if hasattr(self.func, "__code__") and self.func.__code__.co_argcount == 0:
                result = self.func()
            else:
                result = self.func(data)
            
            self.output_data = result if isinstance(result, dict) else {"result": result}
            self.status = NodeStatus.COMPLETED
            
            # 更新上下文
            context.update(self.output_data)
            
            return result
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.error = e
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "config": self.config,
            "input": self.input_data,
            "output": self.output_data,
            "error": str(self.error) if self.error else None
        }
