.PHONY: install dev run example test format lint clean docker-build docker-up docker-down

# 安装 uv (如果未安装)
install-uv:
	@if ! command -v uv &> /dev/null; then \
		echo "Installing uv..."; \
		./scripts/install-uv.sh; \
	else \
		echo "uv is already installed"; \
	fi

# 安装依赖
install: install-uv
	uv sync

# 安装开发依赖
dev: install-uv
	uv sync --dev

# 运行服务
run:
	uv run python main.py

# 运行示例
example:
	uv run python example.py

# 运行测试
test:
	uv run pytest

# 格式化代码
format:
	uv run black .
	uv run ruff check --fix .

# 代码检查
lint:
	uv run ruff check .
	uv run black --check .

# Docker 构建
docker-build:
	docker build -t fittingflow:latest .

# Docker 启动
docker-up:
	docker-compose up -d

# Docker 停止
docker-down:
	docker-compose down

# Docker 查看日志
docker-logs:
	docker-compose logs -f

# 清理
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf .pytest_cache
