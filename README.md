# FittingFlow

极简版的工作流编排系统，灵感来自 Dify。

## 核心概念

- **Workflow**: 工作流，由多个节点组成
- **Node**: 节点，执行特定任务
- **Edge**: 边，连接节点，定义执行顺序
- **Context**: 上下文，在节点间传递数据

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

## 示例

创建一个简单的工作流：

```python
from fittingflow import Workflow, Node

# 创建工作流
workflow = Workflow()

# 添加节点
@workflow.node()
def start(data):
    return {"message": "Hello, FittingFlow!"}

@workflow.node()
def process(data):
    return {"result": data["message"].upper()}

# 连接节点
workflow.connect(start, process)

# 执行工作流
result = workflow.run()
print(result)
```
