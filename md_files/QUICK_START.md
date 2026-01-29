# 🚀 빠른 시작 가이드

이 가이드는 GitHub Actions를 통한 EC2 자동 배포를 빠르게 설정하는 방법을 설명합니다.

## 📋 사전 준비

1. ✅ EC2 인스턴스 실행 중
2. ✅ SSH 접속 가능 (PEM 키 파일 보유)
3. ✅ GitHub 저장소 준비 완료

## 🔧 1단계: EC2 초기 설정

EC2 인스턴스에 SSH로 접속:

```bash
ssh -i "labzang.pem" ubuntu@ec2-3-34-188-206.ap-northeast-2.compute.amazonaws.com
```

초기 설정 스크립트 실행:

```bash
# 저장소 클론 (처음 한 번만)
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git rag-app
cd rag-app

# 초기 설정
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh
```

또는 수동 설정:

```bash
# 필수 패키지 설치
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git curl postgresql-client nginx

# 가상 환경 생성
cd ~/rag-app
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
nano .env  # 환경 변수 편집

# systemd 서비스 설치
chmod +x scripts/install-systemd.sh
./scripts/install-systemd.sh
sudo systemctl start rag-app
```

## 🔐 2단계: GitHub Secrets 설정

GitHub 저장소의 **Settings** > **Secrets and variables** > **Actions**에서:

### EC2_HOST
```
ec2-3-34-188-206.ap-northeast-2.compute.amazonaws.com
```

### EC2_USER
```
ubuntu
```

### EC2_SSH_KEY
PEM 키 파일 전체 내용:

```bash
# Windows PowerShell
Get-Content labzang.pem | Out-String

# Linux/Mac
cat labzang.pem
```

출력된 전체 내용을 복사하여 `EC2_SSH_KEY` Secret에 붙여넣기.

자세한 내용은 [.github/SECRETS_SETUP.md](.github/SECRETS_SETUP.md) 참고.

## 🚀 3단계: 배포 테스트

### 자동 배포 (권장)

`main` 또는 `master` 브랜치에 push:

```bash
git add .
git commit -m "Setup CI/CD"
git push origin main
```

GitHub Actions가 자동으로 배포를 시작합니다.

### 수동 배포 테스트

GitHub 저장소의 **Actions** 탭에서:
1. **Deploy to EC2** 워크플로우 선택
2. **Run workflow** 클릭
3. 브랜치 선택 후 실행

## ✅ 배포 확인

배포가 완료되면:

```bash
# EC2에서 확인
curl http://localhost:8000/health

# 또는 브라우저에서
http://YOUR_EC2_IP/health
```

## 🔍 문제 해결

### 배포 실패 시

1. GitHub Actions 로그 확인
2. EC2에서 직접 확인:
   ```bash
   ssh -i "labzang.pem" ubuntu@YOUR_EC2_HOST
   cd ~/rag-app
   ./scripts/deploy.sh
   ```

### 서비스 상태 확인

```bash
# EC2에서 실행
sudo systemctl status rag-app
sudo journalctl -u rag-app -f
```

## 📚 추가 문서

- [DEPLOYMENT.md](DEPLOYMENT.md) - 상세한 배포 가이드
- [.github/SECRETS_SETUP.md](.github/SECRETS_SETUP.md) - Secrets 설정 상세 가이드

