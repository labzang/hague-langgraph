# EC2 배포 위치 전략 가이드

## 📍 권장 배치 위치

### 프로덕션 환경: `/opt/rag-app` (권장)

**이유:**
- ✅ Linux Filesystem Hierarchy Standard (FHS)에 따른 표준 위치
- ✅ 시스템 레벨 애플리케이션에 적합
- ✅ 사용자 데이터와 분리되어 관리 용이
- ✅ 프로덕션 환경의 모범 사례

**설정 방법:**
```bash
# EC2에서 실행
sudo mkdir -p /opt/rag-app
sudo chown ubuntu:ubuntu /opt/rag-app
cd /opt/rag-app
git clone https://github.com/YOUR_REPO.git .
```

### 개발/테스트 환경: `/home/ubuntu/rag-app` (현재)

**이유:**
- ✅ 사용자 권한으로 관리 가능
- ✅ 빠른 설정 및 테스트
- ✅ sudo 권한 불필요

## 🔄 위치 변경 방법

### 옵션 1: `/opt/rag-app`로 변경 (권장)

1. **systemd 서비스 파일 수정**
   - `scripts/rag-app.service`의 경로를 `/opt/rag-app`로 변경

2. **배포 스크립트 수정**
   - `scripts/deploy.sh`의 `APP_DIR`을 `/opt/rag-app`로 변경

3. **GitHub Actions 워크플로우 수정**
   - `.github/workflows/deploy.yml`의 경로 변경

### 옵션 2: 현재 위치 유지 (`/home/ubuntu/rag-app`)

- 현재 설정 그대로 사용 가능
- 프로덕션 환경이 아닌 경우 충분히 적합

## 💻 CPU 기반 EC2 고려사항

### 1. 모델 로딩 전략
- GPU가 없으므로 경량 모델 사용 권장
- CPU 최적화된 모델 선택 (예: `sentence-transformers`의 CPU 최적화 버전)
- 모델 크기 제한 (2-4GB 이하 권장)

### 2. 메모리 관리
- 모델을 메모리에 한 번만 로드하고 재사용
- 워커 수 조정 (CPU 코어 수에 맞춤)

### 3. 성능 최적화
```python
# uvicorn workers 설정
# CPU 코어 수에 맞춰 조정 (일반적으로 코어 수 - 1)
workers = 2  # 2-4 코어 EC2의 경우
```

## 📋 디렉토리 구조 권장사항

```
/opt/rag-app/              # 또는 /home/ubuntu/rag-app/
├── app/                    # 애플리케이션 코드
├── venv/                   # 가상 환경
├── .env                    # 환경 변수 (Git에 커밋하지 않음)
├── requirements.txt        # Python 의존성
├── scripts/                # 배포 스크립트
├── logs/                   # 로그 파일 (선택사항)
└── models/                 # 모델 파일 (선택사항, S3 사용 권장)
```

## 🔐 권한 설정

### `/opt/rag-app` 사용 시:
```bash
sudo mkdir -p /opt/rag-app
sudo chown -R ubuntu:ubuntu /opt/rag-app
sudo chmod 755 /opt/rag-app
```

### systemd 서비스:
- `User=ubuntu`로 설정하여 ubuntu 사용자 권한으로 실행
- 애플리케이션 파일에 대한 읽기/쓰기 권한 필요

## 🚀 빠른 시작 (현재 설정 유지)

현재 `/home/ubuntu/rag-app` 설정을 그대로 사용하려면:

```bash
# EC2에 SSH 접속
ssh -i "labzang.pem" ubuntu@ec2-3-35-233-152.ap-northeast-2.compute.amazonaws.com

# 홈 디렉토리로 이동
cd ~

# 프로젝트 클론
git clone https://github.com/YOUR_REPO.git rag-app
cd rag-app

# 초기 설정
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh
```

## 📝 결론

- **개발/테스트**: `/home/ubuntu/rag-app` 유지 (현재 설정)
- **프로덕션**: `/opt/rag-app`로 변경 권장

현재 설정으로도 충분히 작동하지만, 프로덕션 환경에서는 `/opt/rag-app`로 변경하는 것을 권장합니다.
