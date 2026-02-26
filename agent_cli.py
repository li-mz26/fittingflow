#!/usr/bin/env python3
"""
FittingFlow Agent CLI

命令行工具用于与 AI Agent 交互
"""

import os
import sys
import argparse
import asyncio
from typing import Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import WorkflowToolsSync, ReActWorkflowAgent, KimiWorkflowAgent


def print_banner():
    print("""
╔════════════════════════════════════════╗
║     🤖 FittingFlow Agent CLI           ║
║                                        ║
║  AI-powered Workflow Management Tool   ║
╚════════════════════════════════════════╝
""")


def interactive_mode(agent: ReActWorkflowAgent):
    """交互模式"""
    print_banner()
    print("输入 'help' 查看帮助，'quit' 退出\n")
    
    while True:
        try:
            user_input = input("\n📝 > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 再见！")
                break
            
            if user_input.lower() in ["help", "h"]:
                print_help()
                continue
            
            if user_input.lower() == "list":
                # 直接列出工作流
                tools = WorkflowToolsSync()
                workflows = tools.list_workflows()
                print("\n📋 工作流列表：")
                for wf in workflows:
                    if "error" in wf:
                        print(f"  ❌ 错误: {wf['error']}")
                    else:
                        print(f"  • {wf.get('name', 'unnamed')} ({len(wf.get('nodes', []))} 节点)")
                tools.close()
                continue
            
            # 使用 Agent 处理
            print("\n🤔 Agent 思考中...\n")
            result = agent.run(user_input)
            print(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def print_help():
    """打印帮助信息"""
    help_text = """
📚 使用帮助

自然语言指令示例：
  • 创建一个名为 'my_workflow' 的工作流
  • 在 my_workflow 中添加一个 start 节点
  • 添加一个 Python 节点，计算两个数的和
  • 连接 start 节点到 python 节点
  • 运行 my_workflow 并传入 {"a": 10, "b": 20}
  • 删除 test_workflow

特殊命令：
  • list    - 列出所有工作流
  • help    - 显示此帮助
  • quit    - 退出程序

Python 节点代码示例：
  输入 data 是一个字典，输出必须赋值给 output
  
  output = {
      "sum": data.get("a", 0) + data.get("b", 0),
      "product": data.get("a", 0) * data.get("b", 0)
  }
"""
    print(help_text)


def main():
    parser = argparse.ArgumentParser(description="FittingFlow Agent CLI")
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("KIMI_API_KEY"),
        help="Kimi API Key (也可以通过 KIMI_API_KEY 环境变量设置)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="kimi-coding/k2p5",
        help="使用的模型 (默认: kimi-coding/k2p5)"
    )
    parser.add_argument(
        "--command",
        "-c",
        type=str,
        help="直接执行一条命令然后退出"
    )
    
    args = parser.parse_args()
    
    # 检查 API key
    if not args.api_key:
        print("❌ 错误：需要提供 API Key")
        print("可以通过 --api-key 参数或 KIMI_API_KEY 环境变量设置")
        print("\n或者使用交互式工具模式（不使用 AI）：")
        print("  python -c \"from agent import WorkflowToolsSync; t=WorkflowToolsSync(); print(t.list_workflows())\"")
        sys.exit(1)
    
    # 创建 Agent
    try:
        agent = KimiWorkflowAgent(
            api_key=args.api_key,
            model=args.model
        )
    except ImportError as e:
        print(f"❌ 错误: {e}")
        print("请安装依赖: pip install openai")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 创建 Agent 失败: {e}")
        sys.exit(1)
    
    # 执行命令或进入交互模式
    if args.command:
        print("🤔 Agent 思考中...\n")
        result = agent.run(args.command)
        print(result)
    else:
        interactive_mode(agent)
    
    # 清理
    agent.close()


if __name__ == "__main__":
    main()
