# FittingFlow

极简版的工作流编排系统，灵感来自 Dify。

## 核心概念

- **Workflow**: 工作流，由多个节点组成
- **Node**: 节点，执行特定任务
- **Edge**: 边，连接节点，定义执行顺序
- **Context**: 上下文，在节点间传递数据

## 快速开始

### 使用 uv (推荐)

```bash
# 安装依赖
uv sync

# 启动服务
uv run python main.py
# 或
make run
```

### 使用 pip

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

## 可用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装依赖 |
| `make dev` | 安装开发依赖 |
| `make run` | 启动服务 |
| `make example` | 运行示例 |
| `make test` | 运行测试 |
| `make format` | 格式化代码 |
| `make lint` | 代码检查 |

## 示例

创建一个简单的工作流：

```python
from fittingflow import Workflow

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

或者运行内置示例：

```bash
make example
```
