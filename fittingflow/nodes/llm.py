from typing import Any, Dict, Optional
import json


def llm_node(
    data: Dict[str, Any],
    prompt_template: str,
    model: str = "gpt-3.5-turbo",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """LLM 节点，调用大语言模型"""
    try:
        # 格式化提示词
        prompt = prompt_template.format(**data)
        
        # 这里只是模拟，实际需要调用真实的 LLM API
        return {
            "prompt": prompt,
            "model": model,
            "response": f"LLM response to: {prompt[:50]}..."
        }
    except Exception as e:
        return {"error": str(e)}


def prompt_template_node(data: Dict[str, Any], template: str) -> Dict[str, Any]:
    """提示词模板节点"""
    try:
        prompt = template.format(**data)
        return {"prompt": prompt}
    except KeyError as e:
        return {"error": f"Missing key in template: {e}"}


def json_parser_node(data: Dict[str, Any], key: str = "text") -> Dict[str, Any]:
    """JSON 解析节点"""
    try:
        text = data.get(key, "")
        parsed = json.loads(text)
        return {"parsed": parsed}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}"}
    except Exception as e:
        return {"error": str(e)}
