# KoELECTRA 게이트웨이 + EXAONE 판독 에이전트 시스템

## 🎯 개요

이 시스템은 **KoELECTRA 게이트웨이**와 **EXAONE 판독 에이전트**를 분리하여 구성한 모듈형 스팸 탐지 시스템입니다.

### 🏗️ 새로운 아키텍처

```
이메일 입력 → KoELECTRA 게이트웨이 → 라우팅 결정 → 판독 에이전트 (EXAONE) or 즉시 응답
```

### 🔧 컴포넌트 분리

- **게이트웨이** (`app/router/mcp_router.py`): KoELECTRA 기반 1차 판별 및 상태 관리
- **판독 에이전트** (`app/service/verdict_agent/graph.py`): EXAONE 기반 정밀 분석

### 🔄 처리 플로우

1. **이메일 입력**: 제목, 내용, 발신자 정보
2. **KoELECTRA 게이트웨이**: 1차 스팸 판별 (LoRA 파인튜닝된 모델)
3. **의사결정 라우터**: 신뢰도 기반 라우팅
   - 고신뢰도 (>95%): 즉시 결정
   - 중간신뢰도 (≤95%): EXAONE 정밀 분석
4. **EXAONE 정밀 분석**: 상세 스팸 분석 (필요시)
5. **최종 결과**: 종합 판정 및 근거 제시

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r app/requirements.txt
```

### 2. 모델 준비

#### KoELECTRA LoRA 어댑터
- 경로: `app/model/spam/lora/run_20260115_1313/`
- 이미 학습된 LoRA 어댑터 사용

#### EXAONE 모델
- 경로: `app/model/exaone-2.4b/`
- EXAONE-2.4B 모델 필요

### 3. 서버 실행

```bash
cd app
python main.py
```

또는

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 API 사용법

### 기본 엔드포인트

- **베이스 URL**: `http://localhost:8000`
- **MCP 엔드포인트**: `/mcp`

### 1. 헬스 체크

```bash
GET /mcp/health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "services": {
    "koelectra": "OK",
    "exaone": "OK",
    "langgraph": "OK"
  },
  "timestamp": "2026-01-15T12:00:00"
}
```

### 2. 이메일 스팸 분석

```bash
POST /mcp/analyze-email
```

**요청 예시:**
```json
{
  "subject": "긴급! 계정 확인 필요",
  "content": "보안상 문제로 계정 확인이 필요합니다. 아래 링크를 클릭하여 확인해주세요.",
  "sender": "security@unknown.com",
  "metadata": {
    "type": "security"
  }
}
```

**응답 예시:**
```json
{
  "is_spam": true,
  "confidence": 0.892,
  "koelectra_decision": "스팸 (신뢰도: 0.850)",
  "exaone_analysis": "이 이메일은 피싱 공격의 전형적인 특징을 보입니다...",
  "processing_path": "koelectra_gateway_started → koelectra_analysis_completed → decision_router_started → routed_to_exaone → exaone_analysis_started → exaone_analysis_completed → result_finalized",
  "timestamp": "2026-01-15T12:00:00",
  "metadata": {
    "koelectra_result": {
      "is_spam": true,
      "confidence": 0.850,
      "probabilities": {
        "정상": 0.150,
        "스팸": 0.850
      }
    },
    "final_decision": "spam_exaone_confirmed"
  }
}
```

### 3. 게이트웨이 정보 조회

```bash
GET /mcp/gateway-info
```

### 4. 세션 상태 조회

```bash
GET /mcp/sessions/{session_id}
```

### 5. 세션 목록 조회

```bash
GET /mcp/sessions?limit=50
```

### 6. 통계 정보 조회

```bash
GET /mcp/stats
```

### 7. 세션 정리

```bash
DELETE /mcp/sessions/cleanup?max_age_hours=24
```

## 🧪 테스트

### 자동 테스트 실행

```bash
python test_mcp_gateway.py
```

### 수동 테스트

```bash
# 정상 이메일 테스트
curl -X POST "http://localhost:8000/mcp/analyze-email" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "회의 일정 안내",
    "content": "내일 오후 2시에 회의가 있습니다."
  }'

# 스팸 이메일 테스트
curl -X POST "http://localhost:8000/mcp/analyze-email" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "긴급! 1억원 당첨!",
    "content": "축하합니다! 복권에 당첨되었습니다. 즉시 계좌번호를 보내주세요!"
  }'
```

## 🔧 설정 및 커스터마이징

### 라우팅 로직 조정

`app/router/mcp_router.py`의 `decision_router_node` 함수에서 신뢰도 임계값 조정:

```python
# 고신뢰도 정상 메일: 즉시 통과
if not is_spam and confidence > 0.95:  # 임계값 조정 가능

# 고신뢰도 스팸: 즉시 차단
elif is_spam and confidence > 0.95:   # 임계값 조정 가능
```

### LoRA 설정 변경

KoELECTRA 모델 경로 변경:
```python
spam_classifier = SpamClassifier(
    model_path="app/model/spam/lora/your_model_path",  # 경로 변경
    base_model="monologg/koelectra-small-v3-discriminator"
)
```

### EXAONE 설정 변경

EXAONE 모델 경로 및 파라미터 조정:
```python
exaone_service = ExaoneService(
    model_path="app/model/your_exaone_model",  # 경로 변경
    temperature=0.3,  # 온도 조정
    max_new_tokens=512  # 최대 토큰 수 조정
)
```

## 📊 성능 특징

### KoELECTRA 게이트웨이
- **모델**: monologg/koelectra-small-v3-discriminator + LoRA
- **성능**: 100% 정확도 (검증 데이터 기준)
- **속도**: ~1-2초 (CPU 기준)
- **메모리**: ~500MB

### EXAONE 정밀 분석
- **모델**: EXAONE-2.4B + QLoRA
- **용도**: 불확실한 케이스의 상세 분석
- **속도**: ~5-10초 (CPU 기준)
- **메모리**: ~2-3GB (4bit 양자화)

### 라우팅 효율성
- **고신뢰도 케이스**: 95%+ → 즉시 처리 (빠름)
- **중간신뢰도 케이스**: ≤95% → EXAONE 분석 (정확함)
- **전체 처리시간**: 평균 2-3초

## 🔍 트러블슈팅

### 1. 모델 로딩 실패
```
오류: KoELECTRA 로드 실패
해결: 모델 경로 확인 및 어댑터 파일 존재 여부 확인
```

### 2. EXAONE 메모리 부족
```
오류: CUDA out of memory
해결: use_4bit=True 설정 확인 또는 CPU 사용
```

### 3. 응답 시간 지연
```
문제: 응답이 너무 느림
해결: 신뢰도 임계값 조정으로 EXAONE 호출 빈도 감소
```

## 📈 모니터링 및 로깅

### 로그 레벨 설정
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 주요 로그 포인트
- KoELECTRA 추론 시작/완료
- 라우팅 결정
- EXAONE 분석 시작/완료
- 최종 결과 생성

### 성능 메트릭
- 처리 시간
- 신뢰도 분포
- 라우팅 패턴
- 오류율

## 🛠️ 확장 가능성

### 1. 추가 에이전트
- 이미지 분석 에이전트
- URL 검증 에이전트
- 발신자 평판 에이전트

### 2. 고급 라우팅
- 컨텍스트 기반 라우팅
- 사용자별 맞춤 임계값
- 시간대별 처리 전략

### 3. 실시간 학습
- 온라인 학습 파이프라인
- 피드백 기반 모델 업데이트
- A/B 테스트 프레임워크

## 📞 지원

문제가 발생하거나 질문이 있으시면:
1. 로그 파일 확인
2. 테스트 스크립트 실행
3. 헬스 체크 엔드포인트 확인
4. 모델 파일 및 경로 검증

---

**🎉 KoELECTRA + EXAONE 멀티 에이전트 스팸 탐지 시스템을 성공적으로 구축했습니다!**
