#!/bin/bash
# 安装 uv

set -e

echo "Installing uv..."

# 官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

echo ""
echo "uv installed successfully!"
echo ""
echo "Please restart your shell or run:"
echo "  source $HOME/.local/bin/env"
echo ""
echo "Then you can run:"
echo "  make install"
