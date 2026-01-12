#!/bin/bash
# systemd 서비스 설치 스크립트
# EC2 인스턴스에서 한 번만 실행하면 됩니다.

set -e

APP_DIR="$HOME/rag-app"
SERVICE_NAME="rag-app"

echo "⚙️ systemd 서비스 설치 중..."

# 서비스 파일 복사
if [ ! -f "$APP_DIR/scripts/rag-app.service" ]; then
    echo "❌ rag-app.service 파일을 찾을 수 없습니다."
    exit 1
fi

# 서비스 파일의 경로를 현재 사용자 홈 디렉터리로 업데이트
sed "s|/home/ubuntu|$HOME|g" "$APP_DIR/scripts/rag-app.service" | sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null

# systemd 재로드
sudo systemctl daemon-reload

# 서비스 활성화
sudo systemctl enable $SERVICE_NAME

echo "✅ systemd 서비스 설치 완료!"
echo ""
echo "서비스 관리 명령어:"
echo "  시작:   sudo systemctl start $SERVICE_NAME"
echo "  중지:   sudo systemctl stop $SERVICE_NAME"
echo "  재시작: sudo systemctl restart $SERVICE_NAME"
echo "  상태:   sudo systemctl status $SERVICE_NAME"
echo "  로그:   sudo journalctl -u $SERVICE_NAME -f"

