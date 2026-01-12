#!/bin/bash
# EC2 배포 스크립트
# 이 스크립트는 EC2 인스턴스에서 직접 실행하거나 GitHub Actions에서 호출됩니다.

set -e

APP_DIR="$HOME/rag-app"
APP_NAME="rag-app"
APP_PORT=8000
PYTHON_VERSION="3.11"

echo "🚀 RAG 애플리케이션 배포 시작..."

# 디렉터리 확인
if [ ! -d "$APP_DIR" ]; then
    echo "📁 애플리케이션 디렉터리 생성: $APP_DIR"
    mkdir -p "$APP_DIR"
fi

cd "$APP_DIR"

# Git 저장소 확인 및 업데이트
if [ -d ".git" ]; then
    echo "🔄 최신 코드 가져오기..."
    git fetch origin
    git reset --hard origin/main || git reset --hard origin/master
else
    echo "❌ Git 저장소를 찾을 수 없습니다."
    exit 1
fi

# 가상 환경 설정
if [ ! -d "venv" ]; then
    echo "🐍 가상 환경 생성..."
    python${PYTHON_VERSION} -m venv venv || python3 -m venv venv
fi

echo "📦 의존성 설치..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다. env.example을 참고하여 생성하세요."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "📝 env.example을 .env로 복사했습니다. 환경 변수를 설정하세요."
    fi
fi

# 애플리케이션 재시작
echo "🔄 애플리케이션 재시작..."

# systemd 서비스가 있는지 확인
if systemctl list-unit-files | grep -q "$APP_NAME.service"; then
    if systemctl is-active --quiet $APP_NAME; then
        echo "🔄 systemd 서비스 재시작..."
        sudo systemctl restart $APP_NAME
    else
        echo "▶️ systemd 서비스 시작..."
        sudo systemctl start $APP_NAME
    fi
    sudo systemctl status $APP_NAME --no-pager || true
else
    echo "⚠️ systemd 서비스가 없습니다. 직접 실행합니다..."
    # 기존 프로세스 종료
    pkill -f "uvicorn app.main:app" || true
    sleep 2

    # 새로 시작
    nohup venv/bin/uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $APP_PORT \
        --workers 2 \
        > app.log 2>&1 &

    echo $! > app.pid
    echo "✅ 애플리케이션이 백그라운드에서 시작되었습니다. PID: $(cat app.pid)"
fi

# 헬스체크
echo "🏥 헬스체크..."
sleep 5

for i in {1..10}; do
    if curl -f http://localhost:$APP_PORT/health > /dev/null 2>&1; then
        echo "✅ 헬스체크 성공!"
        exit 0
    fi
    echo "⏳ 헬스체크 대기 중... ($i/10)"
    sleep 2
done

echo "❌ 헬스체크 실패!"
exit 1

