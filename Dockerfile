FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Playwright + ffmpeg）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 \
    xdg-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 复制项目文件
COPY backend/ /app/backend/
COPY frontend-vue/dist/ /app/frontend/

# 创建数据目录
RUN mkdir -p /app/data

# 设置环境变量
ENV CONFIG_PATH=/app/config.yaml
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "-m", "backend.main"]
