# ============================================================
# 螺栓预紧力机器学习预测系统 - Dockerfile
# 支持 ARM64 和 AMD64 架构
# ============================================================

# 使用跨平台基础镜像
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# 运行时镜像
# ============================================================
FROM python:3.11-slim

# 元数据
LABEL maintainer="Alkaid-SOP System"
LABEL version="1.0.0"
LABEL description="螺栓预紧力机器学习预测系统"

# 设置工作目录
WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从builder复制已安装的Python包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/trained_models /app/data

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/config/config.yaml

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["python", "main.py"]
