# 使用 Python 3.11 官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Playwright 需要）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器和依赖（使用官方脚本）
RUN playwright install --with-deps chromium

# 复制应用代码
COPY . .

# 创建截图目录
RUN mkdir -p /tmp/screenshots

# 运行 bot
CMD ["python", "bot.py"]
