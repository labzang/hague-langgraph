# GitHub Secrets 설정 가이드

이 문서는 GitHub Actions를 통한 EC2 배포를 위해 필요한 GitHub Secrets 설정 방법을 설명합니다.

## 🔐 필요한 Secrets

다음 3개의 Secrets를 GitHub 저장소에 추가해야 합니다:

1. `EC2_HOST` - EC2 인스턴스의 호스트 주소
2. `EC2_USER` - EC2 사용자명
3. `EC2_SSH_KEY` - EC2 접속용 SSH 개인 키

## 📝 설정 방법

### 1. GitHub 저장소에서 Secrets 추가

1. GitHub 저장소로 이동
2. **Settings** > **Secrets and variables** > **Actions** 클릭
3. **New repository secret** 버튼 클릭
4. 아래 정보를 하나씩 추가:

### 2. EC2_HOST 설정

**Name:** `EC2_HOST`
**Value:** EC2 인스턴스의 공개 IP 또는 도메인

예시:
```
ec2-3-34-188-206.ap-northeast-2.compute.amazonaws.com
```

또는 공개 IP:
```
3.34.188.206
```

### 3. EC2_USER 설정

**Name:** `EC2_USER`
**Value:** EC2 사용자명 (일반적으로 `ubuntu`)

예시:
```
ubuntu
```

### 4. EC2_SSH_KEY 설정

**Name:** `EC2_SSH_KEY`
**Value:** SSH 개인 키 파일의 전체 내용

#### SSH 키 준비 방법

**방법 1: 기존 PEM 키 사용 (AWS EC2 기본 키)**

로컬에서 PEM 키 파일을 열어 전체 내용을 복사:

```bash
# Windows (PowerShell)
Get-Content labzang.pem | Out-String

# Linux/Mac
cat labzang.pem
```

출력된 전체 내용(-----BEGIN RSA PRIVATE KEY----- 부터 -----END RSA PRIVATE KEY----- 까지)을 복사하여 `EC2_SSH_KEY` Secret에 붙여넣기.

**방법 2: 새로운 SSH 키 생성 (권장)**

더 안전한 방법으로 새로운 배포 전용 키를 생성:

```bash
# 로컬에서 실행
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ec2_deploy_key -N ""

# 공개 키를 EC2에 추가
ssh-copy-id -i ~/.ssh/ec2_deploy_key.pub ubuntu@YOUR_EC2_HOST

# 개인 키 내용 확인
cat ~/.ssh/ec2_deploy_key
```

출력된 개인 키 전체 내용을 `EC2_SSH_KEY` Secret에 추가.

## ✅ 설정 확인

Secrets가 올바르게 설정되었는지 확인:

1. GitHub 저장소의 **Settings** > **Secrets and variables** > **Actions**에서 3개의 Secrets가 모두 있는지 확인
2. `main` 또는 `master` 브랜치에 push하여 배포가 자동으로 시작되는지 확인
3. **Actions** 탭에서 워크플로우 실행 상태 확인

## 🔒 보안 주의사항

- ⚠️ **절대로** SSH 키를 Git 저장소에 커밋하지 마세요
- ⚠️ Secrets는 GitHub에서만 관리하고, 로컬에 저장하지 마세요
- ⚠️ SSH 키 파일(`.pem`)은 `.gitignore`에 포함되어 있는지 확인하세요
- ✅ 정기적으로 SSH 키를 로테이션하세요
- ✅ 최소 권한 원칙을 따르세요 (배포 전용 사용자 계정 사용 권장)

## 🧪 테스트

Secrets 설정 후 수동으로 배포를 테스트:

1. GitHub 저장소의 **Actions** 탭으로 이동
2. 왼쪽 사이드바에서 **Deploy to EC2** 워크플로우 선택
3. **Run workflow** 버튼 클릭
4. 브랜치 선택 후 **Run workflow** 클릭
5. 실행 로그를 확인하여 성공 여부 확인

## 📞 문제 해결

### SSH 연결 실패

- EC2 보안 그룹에서 포트 22 (SSH)가 열려있는지 확인
- SSH 키 권한이 올바른지 확인 (600)
- EC2_HOST가 올바른지 확인

### 배포 실패

- EC2에 Python 3.11이 설치되어 있는지 확인
- Git 저장소가 올바르게 클론되었는지 확인
- 환경 변수(.env)가 올바르게 설정되었는지 확인

