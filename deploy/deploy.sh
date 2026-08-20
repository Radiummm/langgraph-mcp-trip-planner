#!/bin/bash
set -e

# ============================================================
# 旅行规划助手 - 一键部署脚本
# 目标服务器: OpenCloudOS 9 / 2核2GB / 域名: your-domain.example
# ============================================================

APP_DIR="/opt/trip-planner"
REPO_URL=""  # 如果用 git 部署，填你的 repo 地址

echo "=========================================="
echo "  旅行规划助手 - 部署开始"
echo "=========================================="

# -------- 1. 系统依赖 --------
echo ""
echo "[1/6] 安装系统依赖..."
dnf install -y nginx python3.11 python3.11-pip python3.11-devel gcc git nodejs npm

# -------- 2. 创建目录结构 --------
echo ""
echo "[2/6] 创建项目目录..."
mkdir -p ${APP_DIR}/backend
mkdir -p ${APP_DIR}/frontend

# -------- 3. 部署后端 --------
echo ""
echo "[3/6] 部署后端..."

# 复制后端代码（假设代码已上传到服务器 /tmp/trip-planner-src）
# 如果用 git: git clone ${REPO_URL} /tmp/trip-planner-src
cp -r /tmp/trip-planner-src/backend/app ${APP_DIR}/backend/
cp -r /tmp/trip-planner-src/backend/data ${APP_DIR}/backend/
cp /tmp/trip-planner-src/backend/run.py ${APP_DIR}/backend/
cp /tmp/trip-planner-src/deploy/requirements-prod.txt ${APP_DIR}/backend/requirements.txt

# 创建 Python 虚拟环境
cd ${APP_DIR}/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 创建 .env 文件（需要手动填写 API Key）
if [ ! -f ${APP_DIR}/backend/.env ]; then
cat > ${APP_DIR}/backend/.env << 'EOF'
# LLM 配置 (DeepSeek)
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=你的DeepSeek_API_Key
LLM_BASE_URL=https://api.deepseek.com/v1

# 服务器配置
HOST=127.0.0.1
PORT=8000

# CORS（通过 Nginx 代理后前端同源，但保留以防直接调用）
CORS_ORIGINS=http://your-domain.example,http://localhost:5173

# 高德地图 API
AMAP_API_KEY=你的高德API_Key

# RAG 禁用（不装 PostgreSQL）
DATABASE_URL=
RAG_EMBEDDING_PROVIDER=local_hash
RAG_EMBEDDING_DIMENSIONS=512

# 日志
LOG_LEVEL=INFO
EOF
echo "⚠️  请编辑 ${APP_DIR}/backend/.env 填入真实的 API Key"
fi

# -------- 4. 部署前端 --------
echo ""
echo "[4/6] 构建前端..."

cd /tmp/trip-planner-src/frontend

# 设置生产环境 API 地址（通过 Nginx 代理，用相对路径）
cat > .env.production << 'EOF'
VITE_API_BASE_URL=
VITE_AMAP_WEB_KEY=
VITE_AMAP_WEB_JS_KEY=
EOF

npm install
npm run build

# 复制构建产物
cp -r dist ${APP_DIR}/frontend/

# -------- 5. 配置 Nginx --------
echo ""
echo "[5/6] 配置 Nginx..."

cp /tmp/trip-planner-src/deploy/nginx-trip-planner.conf /etc/nginx/conf.d/trip-planner.conf

# 删除默认站点（如果有冲突）
rm -f /etc/nginx/conf.d/default.conf

nginx -t
systemctl enable nginx
systemctl restart nginx

# -------- 6. 配置 systemd 服务 --------
echo ""
echo "[6/6] 配置后端服务..."

cp /tmp/trip-planner-src/deploy/trip-planner.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable trip-planner
systemctl start trip-planner

# -------- 完成 --------
echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://your-domain.example"
echo "  API 文档: http://your-domain.example/docs"
echo ""
echo "  后续操作:"
echo "  1. 编辑 ${APP_DIR}/backend/.env 填入 API Key"
echo "  2. 重启服务: systemctl restart trip-planner"
echo "  3. 查看日志: journalctl -u trip-planner -f"
echo ""
echo "  防火墙: 确保 80 端口已开放"
echo "=========================================="
