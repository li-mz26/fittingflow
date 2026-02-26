from typing import Any, Dict


class Context:
    """工作流上下文，用于在节点间传递数据"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
    
    def update(self, data: Dict[str, Any]) -> None:
        self._data.update(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy()
    
    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)
