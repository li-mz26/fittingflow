FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# 复制项目文件
COPY pyproject.toml ./
COPY fittingflow ./fittingflow
COPY main.py ./
COPY static ./static

# 安装依赖
RUN uv sync --frozen --no-dev

# 生产阶段
FROM python:3.12-slim-bookworm

WORKDIR /app

# 从 builder 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/fittingflow /app/fittingflow
COPY --from=builder /app/main.py /app/main.py
COPY --from=builder /app/static /app/static

# 激活虚拟环境
ENV PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 8000

# 运行服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
