# 에이전트 플랫폼 최적화 구조

## 🎯 제거/정리 계획

### ❌ 완전 제거 대상

```bash
# 1. 빈 폴더 제거
rm -rf app/bases/

# 2. RAG 전용 레포지토리 제거 (MCP filesystem으로 대체)
rm -rf app/repositories/

# 3. 중복 컨트롤러 제거 (orchestrator로 대체)
rm -rf app/controllers/

# 4. 사용하지 않는 라우터 제거
rm app/routers/training_router.py  # 또는 에이전트로 변환

# 5. 중복 서비스 제거/이동
rm app/services/chat_service.py      # ConversationAgent로 대체
rm app/services/rag_service.py       # RetrievalAgent로 대체
rm app/services/training_service.py  # TrainingAgent로 대체 또는 제거
```

### 🔄 이동/통합 대상

```bash
# 기존 서비스들을 에이전트로 변환
app/services/spam_classifier/     → app/agents/analysis/     (완료)
app/services/verdict_agent/       → app/agents/analysis/     (완료)
app/api/routes/search.py          → app/agents/retrieval/    (신규)
app/routers/chat_router.py        → app/agents/conversation/ (신규)
```

## 🏗️ 최적화된 최종 구조

```
app/
├── main.py                          # 메인 애플리케이션
├── research_orchestrator_main.py    # CLI 실행 파일
├── config.py                        # 설정
├── requirements.txt                 # 의존성
│
├── orchestrator/                    # 🆕 오케스트레이션 핵심
│   ├── __init__.py
│   ├── mcp_app.py                  # MCP 앱 래퍼
│   ├── orchestrator.py             # 메인 오케스트레이터
│   └── workflow_manager.py         # 워크플로우 관리
│
├── agents/                          # 🆕 에이전트 컬렉션
│   ├── __init__.py
│   ├── base_agent.py               # 베이스 에이전트
│   ├── analysis/                   # 분석 에이전트들
│   │   ├── spam_detector.py        # 스팸 탐지
│   │   └── verdict_agent.py        # 상세 판독
│   ├── research/                   # 연구 에이전트들
│   │   ├── searcher.py            # 웹 검색
│   │   ├── fact_checker.py        # 팩트 체킹
│   │   └── report_writer.py       # 보고서 작성
│   ├── retrieval/                  # 🆕 검색 에이전트들
│   │   └── vector_searcher.py      # 벡터 검색
│   └── conversation/               # 🆕 대화 에이전트들
│       └── chat_agent.py           # 채팅 에이전트
│
├── routers/                        # API 라우터들
│   ├── orchestrator_router.py      # 🆕 오케스트레이터 API
│   ├── mcp_router.py              # 기존 MCP API (호환성)
│   └── chat_router.py             # 기존 채팅 API (호환성)
│
├── services/                       # 🔄 재구성된 서비스들
│   ├── llm/                       # LLM 서비스 (유지)
│   │   ├── exaone_local.py
│   │   ├── korean_hf_local.py
│   │   └── openai.py
│   ├── vector/                    # 벡터 서비스 (유지)
│   │   └── vectorstore.py
│   └── external/                  # 🆕 외부 서비스 연동
│       ├── web_search.py          # 웹 검색 API
│       └── file_manager.py        # 파일 관리
│
├── core/                          # 핵심 유틸리티 (유지)
│   ├── korean_embeddings.py
│   ├── korean_llm.py
│   └── llm/
│
├── api/                           # API 모델 (유지)
│   └── models.py
│
├── data/                          # 데이터 (유지)
└── model/                         # 모델 파일들 (유지)
```

## 📊 정리 효과

### Before (현재)
- **총 폴더**: 15개
- **중복 구조**: controllers + services + repositories
- **복잡도**: 높음 (RAG + 에이전트 혼재)

### After (정리 후)
- **총 폴더**: 10개
- **통합 구조**: orchestrator + agents 중심
- **복잡도**: 낮음 (에이전트 플랫폼 특화)

## 🚀 정리 순서

### Phase 1: 안전한 제거
1. `app/bases/` 제거 (빈 폴더)
2. `app/repositories/` 제거 (사용하지 않음)
3. `app/controllers/` 제거 (orchestrator로 대체됨)

### Phase 2: 서비스 통합
1. `chat_service.py` → `ConversationAgent` 변환
2. `rag_service.py` → `RetrievalAgent` 변환
3. `training_service.py` 제거 또는 `TrainingAgent` 변환

### Phase 3: 라우터 정리
1. `training_router.py` 제거 (사용하지 않음)
2. `search.py` → `RetrievalAgent`로 통합
3. 기존 API 호환성 유지

## ✅ 정리 후 이점

1. **구조 단순화**: 15개 → 10개 폴더
2. **역할 명확화**: 에이전트 중심 구조
3. **유지보수성 향상**: 중복 제거
4. **확장성 개선**: 새 에이전트 추가 용이
5. **성능 최적화**: 불필요한 레이어 제거

## 🔧 호환성 보장

- 기존 API 엔드포인트 유지
- 점진적 마이그레이션 지원
- 기존 모델/데이터 100% 재활용
