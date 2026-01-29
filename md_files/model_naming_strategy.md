# 모델 네이밍 전략 및 구조 개선

## 🎯 현재 문제점

### 이름 충돌
- **`app/model/`** = AI 모델 파일들 (KoELECTRA, EXAONE, Midm - 총 7.6GB)
- **`app/services/verdict_agent/base_model.py`** = Pydantic 데이터 모델들

## 💡 권장 해결책

### Option 1: AI 모델 폴더명 변경 (권장) ✅

```bash
# Before
app/model/                    # AI 모델 파일들
app/services/verdict_agent/base_model.py  # Pydantic 모델들

# After
app/models/                   # AI 모델 파일들 (복수형)
app/schemas/                  # Pydantic 모델들 (새 위치)
```

**장점:**
- 업계 표준 관례 준수 (`models/` 복수형)
- 명확한 역할 구분
- 확장성 우수

### Option 2: Pydantic 모델 폴더 변경

```bash
# Before
app/model/                    # AI 모델 파일들
app/services/verdict_agent/base_model.py  # Pydantic 모델들

# After
app/model/                    # AI 모델 파일들 (유지)
app/schemas/                  # Pydantic 모델들 (새 위치)
```

## 🚀 구현 계획 (Option 1 권장)

### Step 1: AI 모델 폴더 이름 변경
```bash
mv app/model/ app/models/
```

### Step 2: Pydantic 모델들 통합
```bash
mkdir app/schemas/
mv app/services/verdict_agent/base_model.py app/schemas/email_models.py
mv app/services/verdict_agent/state_model.py app/schemas/session_models.py
mv app/services/verdict_agent/vector_model.py app/schemas/vector_models.py
```

### Step 3: Import 경로 업데이트
```python
# Before
from app.services.verdict_agent.base_model import EmailInput, GatewayResponse

# After
from app.schemas.email_models import EmailInput, GatewayResponse
```

## 📁 최종 구조

```
app/
├── models/                   # 🔄 AI 모델 파일들 (이름 변경)
│   ├── spam/                # KoELECTRA 스팸 모델
│   ├── exaone-2.4b/         # EXAONE 모델
│   ├── midm/                # Midm 모델
│   └── customer_service/    # 고객서비스 모델
│
├── schemas/                  # 🆕 Pydantic 데이터 모델들
│   ├── __init__.py
│   ├── email_models.py      # 이메일 관련 모델
│   ├── session_models.py    # 세션 관련 모델
│   └── vector_models.py     # 벡터 관련 모델
│
├── agents/                  # 에이전트들
├── orchestrator/            # 오케스트레이터
├── services/                # 서비스들
└── ...
```

## 🔧 업데이트 필요한 파일들

### 1. 설정 파일들
- `app/config.py` - 모델 경로 업데이트
- `app/core/llm/providers/*.py` - 모델 경로 참조

### 2. 에이전트들
- `app/agents/analysis/spam_detector.py` - 모델 경로
- `app/agents/analysis/verdict_agent.py` - 모델 경로

### 3. 서비스들
- `app/services/spam_classifier/inference.py` - 모델 경로
- `app/services/verdict_agent/graph.py` - 스키마 import

### 4. 라우터들
- `app/routers/mcp_router.py` - 스키마 import
- `app/routers/chat_router.py` - 스키마 import

## ✅ 이점

### 1. 명확한 구분
- **`app/models/`** = 물리적 AI 모델 파일들
- **`app/schemas/`** = 논리적 데이터 구조 정의

### 2. 업계 표준 준수
- AI/ML 프로젝트에서 일반적으로 사용하는 구조
- 새로운 개발자가 쉽게 이해 가능

### 3. 확장성
- 새로운 AI 모델 추가 시 `models/` 하위에 자연스럽게 배치
- 새로운 데이터 스키마 추가 시 `schemas/` 하위에 체계적으로 관리

### 4. 유지보수성
- 각 영역의 책임이 명확히 분리됨
- 모델 파일과 스키마 정의가 독립적으로 관리됨

## 🎯 권장사항

**Option 1을 강력 권장합니다:**
1. `app/model/` → `app/models/` (복수형으로 변경)
2. Pydantic 모델들을 `app/schemas/`로 통합
3. 관련 import 경로 모두 업데이트

이렇게 하면 **명확하고 확장 가능한 구조**가 완성됩니다! 🚀
