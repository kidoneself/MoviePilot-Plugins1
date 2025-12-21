FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# 创建数据目录
RUN mkdir -p /app/data

# 设置环境变量
ENV CONFIG_PATH=/app/config.yaml
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "-m", "backend.main"]
