from typing import Any, Dict
from ..node import Node


def start_node(data: Dict[str, Any]) -> Dict[str, Any]:
    """起始节点，透传输入数据"""
    return data or {}


def end_node(data: Dict[str, Any]) -> Dict[str, Any]:
    """结束节点，返回最终结果"""
    return {"final_output": data}


def template_node(data: Dict[str, Any], template: str) -> Dict[str, Any]:
    """模板节点，使用模板格式化数据"""
    try:
        result = template.format(**data)
        return {"text": result}
    except KeyError as e:
        return {"error": f"Missing key: {e}"}


def code_node(data: Dict[str, Any], code: str) -> Dict[str, Any]:
    """代码节点，执行 Python 代码"""
    try:
        # 安全的执行环境
        local_vars = {"data": data}
        exec(code, {}, local_vars)
        return local_vars.get("output", {})
    except Exception as e:
        return {"error": str(e)}


def if_node(data: Dict[str, Any], condition: str) -> Dict[str, Any]:
    """条件节点，判断条件"""
    try:
        local_vars = {"data": data}
        result = eval(condition, {}, local_vars)
        return {"condition_met": bool(result)}
    except Exception as e:
        return {"error": str(e), "condition_met": False}
