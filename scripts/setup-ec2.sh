#!/bin/bash
# EC2 인스턴스 초기 설정 스크립트
# 이 스크립트는 EC2 인스턴스에 처음 한 번만 실행합니다.

set -e

echo "🔧 EC2 인스턴스 초기 설정 시작..."

# 시스템 업데이트
echo "📦 시스템 패키지 업데이트..."
sudo apt-get update
sudo apt-get upgrade -y

# 필수 패키지 설치
echo "📦 필수 패키지 설치..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    postgresql-client \
    nginx \
    supervisor

# Python 3.11이 없으면 기본 python3 사용
if ! command -v python3.11 &> /dev/null; then
    echo "⚠️ Python 3.11을 찾을 수 없습니다. 기본 python3를 사용합니다."
    PYTHON_CMD=python3
else
    PYTHON_CMD=python3.11
fi

# Git 저장소 클론 (처음 한 번만)
APP_DIR="$HOME/rag-app"
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Git 저장소 클론..."
    # GitHub 저장소 URL을 환경 변수나 직접 입력으로 받아야 함
    read -p "GitHub 저장소 URL을 입력하세요: " REPO_URL
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

# 가상 환경 생성
if [ ! -d "venv" ]; then
    echo "🐍 가상 환경 생성..."
    $PYTHON_CMD -m venv venv
fi

# 의존성 설치
echo "📦 의존성 설치..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 환경 변수 파일 설정
if [ ! -f ".env" ]; then
    echo "📝 .env 파일 생성..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "⚠️ .env 파일을 생성했습니다. 환경 변수를 설정하세요!"
        echo "   nano $APP_DIR/.env"
    fi
fi

# systemd 서비스 설정
echo "⚙️ systemd 서비스 설정..."
sudo cp scripts/rag-app.service /etc/systemd/system/rag-app.service
sudo systemctl daemon-reload
sudo systemctl enable rag-app

# Nginx 설정 (선택사항)
echo "🌐 Nginx 설정..."
sudo tee /etc/nginx/sites-available/rag-app > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/rag-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 방화벽 설정 (UFW)
echo "🔥 방화벽 설정..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "✅ 초기 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. .env 파일을 편집하여 환경 변수를 설정하세요:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. 애플리케이션을 시작하세요:"
echo "   sudo systemctl start rag-app"
echo "   sudo systemctl status rag-app"

