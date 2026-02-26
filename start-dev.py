#!/usr/bin/env python3
import sys
import subprocess
import os


def check_and_install(package):
    """检查并安装包"""
    try:
        __import__(package)
        return True
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True


def main():
    print("🚀 Starting FittingFlow in dev mode...")
    
    # 检查必要的包
    packages = ["fastapi", "uvicorn", "pydantic"]
    for pkg in packages:
        check_and_install(pkg.replace("-", "_"))
    
    # 启动 uvicorn
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("\n✅ Server starting at http://localhost:8000")
    print("   Press Ctrl+C to stop\n")
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == "__main__":
    main()
