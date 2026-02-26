from fittingflow import Workflow
import asyncio


async def main():
    # 创建工作流
    workflow = Workflow(name="example")
    
    # 添加节点
    @workflow.node()
    def start(data):
        print("📥 Start node")
        return {"message": "Hello, FittingFlow!"}
    
    @workflow.node()
    def process(data):
        print("⚙️ Process node")
        msg = data.get("message", "")
        return {
            "original": msg,
            "uppercase": msg.upper(),
            "length": len(msg)
        }
    
    @workflow.node()
    def end(data):
        print("📤 End node")
        return {"final_result": data}
    
    # 连接节点
    workflow.connect(start, process)
    workflow.connect(process, end)
    
    # 运行工作流
    print("🚀 Running workflow...")
    result = await workflow.run()
    
    print("\n✅ Workflow completed!")
    print(f"   Final result: {result['context']}")
    
    print("\n📊 Node details:")
    for name, node in result['nodes'].items():
        print(f"   - {name}: {node['status']}")


if __name__ == "__main__":
    asyncio.run(main())
