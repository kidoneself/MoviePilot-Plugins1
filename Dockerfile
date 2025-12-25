FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Playwright + Selenium + Chrome + ffmpeg）
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
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 安装 Google Chrome（用于 Selenium）
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器（用于迅雷等）
RUN playwright install chromium

# 安装 ChromeDriver（用于 Selenium）
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1-3) \
    && echo "Chrome version: $CHROME_VERSION" \
    && DRIVER_VERSION=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION%.*}" 2>/dev/null || echo "130.0.6723.91") \
    && echo "ChromeDriver version: $DRIVER_VERSION" \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${DRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip \
    && unzip -o /tmp/chromedriver.zip -d /tmp/ \
    && mkdir -p /root/.cache/selenium/chromedriver/linux64/${DRIVER_VERSION}/ \
    && mv /tmp/chromedriver-linux64/chromedriver /root/.cache/selenium/chromedriver/linux64/${DRIVER_VERSION}/ \
    && chmod +x /root/.cache/selenium/chromedriver/linux64/${DRIVER_VERSION}/chromedriver \
    && rm -rf /tmp/chromedriver* \
    && ln -s /root/.cache/selenium/chromedriver/linux64/${DRIVER_VERSION}/chromedriver /usr/local/bin/chromedriver

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
