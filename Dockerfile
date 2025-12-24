FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Playwright + ffmpeg）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    xdg-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器（只安装浏览器，不执行install-deps）
RUN playwright install chromium

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
