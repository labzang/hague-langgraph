# EC2 배포 가이드

이 문서는 GitHub Actions를 통한 EC2 자동 배포 설정 방법을 설명합니다.

## 📋 사전 준비사항

### 1. EC2 인스턴스 설정

- Ubuntu 24.04 LTS 이상 권장
- 최소 사양: 2GB RAM, 2 vCPU
- 보안 그룹에서 포트 22 (SSH), 80 (HTTP), 443 (HTTPS) 열기

### 2. GitHub Secrets 설정

GitHub 저장소의 Settings > Secrets and variables > Actions에서 다음 secrets를 추가하세요:

- `EC2_HOST`: EC2 인스턴스의 공개 IP 또는 도메인 (예: `ec2-xxx.compute.amazonaws.com`)
- `EC2_USER`: EC2 사용자명 (일반적으로 `ubuntu`)
- `EC2_SSH_KEY`: EC2 접속용 SSH 개인 키 전체 내용

#### SSH 키 생성 및 설정

```bash
# 로컬에서 SSH 키 생성 (이미 있다면 생략)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ec2_deploy_key

# EC2에 공개 키 추가
ssh-copy-id -i ~/.ssh/ec2_deploy_key.pub ubuntu@YOUR_EC2_HOST

# 개인 키 내용을 GitHub Secret에 추가
cat ~/.ssh/ec2_deploy_key
# 위 출력 전체를 EC2_SSH_KEY secret에 복사
```

### 3. EC2 인스턴스 초기 설정

EC2 인스턴스에 SSH로 접속한 후:

```bash
# 초기 설정 스크립트 실행
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git rag-app
cd rag-app
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh
```

또는 수동으로:

```bash
# 필수 패키지 설치
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git curl postgresql-client nginx

# Git 저장소 클론
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git rag-app
cd rag-app

# 가상 환경 생성 및 의존성 설치
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
nano .env  # 환경 변수 편집

# systemd 서비스 설정
sudo cp scripts/rag-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rag-app
```

## 🚀 배포 프로세스

### 자동 배포 (GitHub Actions)

1. `main` 또는 `master` 브랜치에 push하면 자동으로 배포됩니다.
2. GitHub Actions 탭에서 배포 진행 상황을 확인할 수 있습니다.

### 수동 배포

EC2 인스턴스에 SSH로 접속:

```bash
cd ~/rag-app
./scripts/deploy.sh
```

또는:

```bash
cd ~/rag-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rag-app
```

## 🔧 애플리케이션 관리

### systemd 서비스 명령어

```bash
# 서비스 시작
sudo systemctl start rag-app

# 서비스 중지
sudo systemctl stop rag-app

# 서비스 재시작
sudo systemctl restart rag-app

# 서비스 상태 확인
sudo systemctl status rag-app

# 로그 확인
sudo journalctl -u rag-app -f
```

### 환경 변수 설정

`.env` 파일을 편집:

```bash
cd ~/rag-app
nano .env
```

주요 환경 변수:
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `OPENAI_API_KEY`: OpenAI API 키 (선택사항)
- `LLM_PROVIDER`: LLM 제공자 (openai, korean_local, midm 등)
- `LOCAL_MODEL_DIR`: 로컬 모델 디렉터리 경로
- `USE_CHAT_SERVICE`: Chat Service 사용 여부
- `CHAT_MODEL_PATH`: QLoRA 모델 경로

### 로그 확인

```bash
# systemd 로그
sudo journalctl -u rag-app -f

# 애플리케이션 로그 (systemd 미사용 시)
tail -f ~/rag-app/app.log
```

## 🌐 Nginx 리버스 프록시 설정

Nginx를 사용하여 HTTPS를 설정하려면:

```bash
# Certbot 설치 (Let's Encrypt)
sudo apt-get install -y certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo systemctl enable certbot.timer
```

## 🔍 문제 해결

### 배포 실패 시

1. GitHub Actions 로그 확인
2. EC2에서 직접 배포 스크립트 실행:
   ```bash
   cd ~/rag-app
   ./scripts/deploy.sh
   ```

### 애플리케이션이 시작되지 않을 때

```bash
# 서비스 상태 확인
sudo systemctl status rag-app

# 로그 확인
sudo journalctl -u rag-app -n 50

# 수동 실행으로 에러 확인
cd ~/rag-app
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 포트 충돌

```bash
# 포트 사용 확인
sudo lsof -i :8000

# 프로세스 종료
sudo pkill -f "uvicorn app.main:app"
```

## 📝 참고사항

- 환경 변수는 `.env` 파일에 저장되며 Git에 커밋되지 않습니다.
- 대용량 모델 파일은 EC2에 직접 다운로드하거나 S3를 사용하세요.
- 데이터베이스는 별도의 RDS 인스턴스나 Neon 같은 관리형 서비스를 권장합니다.

