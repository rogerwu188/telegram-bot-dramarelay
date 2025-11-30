#!/bin/bash
# Railway 部署前安装脚本

set -e

echo "🔧 Installing Python dependencies..."

# 确保使用正确的 Python 和 pip
if command -v python3.11 &> /dev/null; then
    PYTHON=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON=python3
else
    echo "❌ Python not found!"
    exit 1
fi

echo "✅ Using Python: $PYTHON"
$PYTHON --version

# 安装依赖
echo "📦 Installing requirements..."
$PYTHON -m ensurepip --default-pip || true
$PYTHON -m pip install --upgrade pip setuptools wheel
$PYTHON -m pip install -r requirements.txt

# 安装 Playwright
echo "🎭 Installing Playwright..."
$PYTHON -m playwright install chromium || echo "⚠️  Playwright install skipped"
$PYTHON -m playwright install-deps chromium || echo "⚠️  Playwright deps skipped"

echo "✅ Setup complete!"
