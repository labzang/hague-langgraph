# 에이전트 플랫폼 마이그레이션 계획

## 🎯 목표: RAG → 범용 에이전트 오케스트레이션 플랫폼

현재 스팸 탐지 시스템을 **범용 에이전트 오케스트레이션 플랫폼**으로 전환합니다.

## 📊 현재 vs 목표 구조

### 현재 구조 (스팸 특화)
```
app/
├── routers/mcp_router.py        # 스팸 탐지 전용
├── services/verdict_agent/      # 스팸 판독 에이전트
├── services/spam_classifier/    # KoELECTRA 스팸 분류
├── controllers/                 # 스팸 컨트롤러
└── api/routes/search.py         # RAG 검색
```

### 목표 구조 (범용 에이전트 플랫폼)
```
app/
├── orchestrator/                # 🆕 에이전트 오케스트레이션 핵심
│   ├── __init__.py
│   ├── mcp_app.py              # MCPApp 래퍼
│   ├── orchestrator.py         # 메인 오케스트레이터
│   └── workflow_manager.py     # 워크플로우 관리
├── agents/                     # 🆕 에이전트 컬렉션
│   ├── __init__.py
│   ├── base_agent.py           # 에이전트 베이스 클래스
│   ├── research/               # 연구 에이전트들
│   │   ├── searcher.py         # 웹 검색 에이전트
│   │   ├── fact_checker.py     # 팩트 체크 에이전트
│   │   └── report_writer.py    # 보고서 작성 에이전트
│   ├── analysis/               # 분석 에이전트들 (기존 스팸 포함)
│   │   ├── spam_detector.py    # 기존 스팸 탐지 → 에이전트화
│   │   ├── sentiment_analyzer.py
│   │   └── content_classifier.py
│   └── utility/                # 유틸리티 에이전트들
│       ├── file_manager.py
│       └── data_processor.py
├── workflows/                  # 🆕 워크플로우 정의
│   ├── __init__.py
│   ├── research_workflow.py    # 연구 워크플로우
│   ├── analysis_workflow.py    # 분석 워크플로우 (기존 스팸)
│   └── custom_workflow.py      # 사용자 정의 워크플로우
├── routers/                    # 🔄 API 라우터 (확장)
│   ├── orchestrator_router.py  # 🆕 오케스트레이터 API
│   ├── agent_router.py         # 🆕 개별 에이전트 API
│   ├── workflow_router.py      # 🆕 워크플로우 API
│   └── legacy_mcp_router.py    # 기존 스팸 API (호환성)
├── services/                   # 🔄 기존 서비스 유지/확장
│   ├── llm/                    # LLM 서비스들
│   ├── vector/                 # 벡터 서비스들
│   └── external/               # 외부 서비스 연동
└── config/                     # 🔄 설정 확장
    ├── agent_config.py         # 🆕 에이전트 설정
    ├── workflow_config.py      # 🆕 워크플로우 설정
    └── mcp_config.py           # 🆕 MCP 서버 설정
```

## 🚀 마이그레이션 단계별 계획

### Phase 1: 핵심 인프라 구축 (1-2주)

#### 1.1 오케스트레이터 핵심 구축
```python
# app/orchestrator/mcp_app.py
from mcp_agent.app import MCPApp
from typing import Dict, Any
import asyncio

class AgentPlatformApp:
    def __init__(self, name: str = "agent_platform"):
        self.mcp_app = MCPApp(name=name)
        self.agents = {}
        self.workflows = {}

    async def run(self):
        """플랫폼 실행"""
        async with self.mcp_app.run() as app:
            yield app

    def register_agent(self, agent):
        """에이전트 등록"""
        self.agents[agent.name] = agent

    def register_workflow(self, workflow):
        """워크플로우 등록"""
        self.workflows[workflow.name] = workflow
```

#### 1.2 베이스 에이전트 클래스
```python
# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from mcp_agent.agents.agent import Agent

class BaseAgent(ABC):
    def __init__(self, name: str, instruction: str, server_names: List[str]):
        self.name = name
        self.instruction = instruction
        self.server_names = server_names
        self._mcp_agent = None

    @property
    def mcp_agent(self) -> Agent:
        if self._mcp_agent is None:
            self._mcp_agent = Agent(
                name=self.name,
                instruction=self.instruction,
                server_names=self.server_names
            )
        return self._mcp_agent

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 실행 로직"""
        pass
```

### Phase 2: 기존 스팸 시스템 에이전트화 (1주)

#### 2.1 스팸 탐지 에이전트 변환
```python
# app/agents/analysis/spam_detector.py
from app.agents.base_agent import BaseAgent
from app.services.spam_classifier.inference import SpamClassifier

class SpamDetectorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="spam_detector",
            instruction="""You are an expert spam email detector.
            Analyze emails and classify them as spam or legitimate.""",
            server_names=["filesystem"]  # 필요한 MCP 서버들
        )
        self.classifier = None

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        email_data = context.get("email", {})

        # 기존 KoELECTRA 로직 활용
        if self.classifier is None:
            self.classifier = SpamClassifier(
                model_path="app/model/spam/lora/run_20260115_1313",
                base_model="monologg/koelectra-small-v3-discriminator"
            )

        result = await asyncio.to_thread(
            self.classifier.predict,
            f"{email_data.get('subject', '')} {email_data.get('content', '')}"
        )

        return {
            "agent": self.name,
            "result": result,
            "confidence": result["confidence"],
            "classification": "spam" if result["is_spam"] else "legitimate"
        }
```

#### 2.2 판독 에이전트 변환
```python
# app/agents/analysis/verdict_agent.py
from app.agents.base_agent import BaseAgent
from app.services.verdict_agent.graph import get_mcp_agent_wrapper

class VerdictAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="verdict_agent",
            instruction="""You are a detailed email analysis agent.
            Provide thorough analysis of suspicious emails.""",
            server_names=["filesystem"]
        )

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        email_data = context.get("email", {})
        koelectra_result = context.get("koelectra_result", {})

        # 기존 EXAONE 로직 활용
        mcp_wrapper = get_mcp_agent_wrapper()
        result = await mcp_wrapper.analyze_with_exaone(
            email_data.get("subject", ""),
            email_data.get("content", ""),
            koelectra_result
        )

        return {
            "agent": self.name,
            "result": result,
            "verdict": result.get("verdict"),
            "analysis": result.get("exaone_response")
        }
```

### Phase 3: 연구 에이전트 추가 (1주)

#### 3.1 웹 검색 에이전트
```python
# app/agents/research/searcher.py
from app.agents.base_agent import BaseAgent

class SearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="searcher",
            instruction="""You are an expert web researcher. Your role is to:
            1. Search for relevant, authoritative sources on the given topic
            2. Visit the most promising URLs to gather detailed information
            3. Return a structured summary of your findings with source URLs

            Focus on high-quality sources like academic papers, respected tech publications,
            and official documentation.

            Save each individual source in the output/sources/ folder. We only need up to 10 sources max.
            """,
            server_names=["brave", "fetch", "filesystem"]
        )

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # MCP 에이전트를 통한 웹 검색 실행
        # 제시된 코드의 로직 활용
        pass
```

### Phase 4: 워크플로우 시스템 (1주)

#### 4.1 워크플로우 매니저
```python
# app/workflows/workflow_manager.py
from typing import List, Dict, Any
from app.agents.base_agent import BaseAgent

class WorkflowManager:
    def __init__(self):
        self.workflows = {}

    def register_workflow(self, name: str, agents: List[BaseAgent], plan_type: str = "full"):
        """워크플로우 등록"""
        self.workflows[name] = {
            "agents": agents,
            "plan_type": plan_type
        }

    async def execute_workflow(self, name: str, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """워크플로우 실행"""
        if name not in self.workflows:
            raise ValueError(f"Workflow {name} not found")

        workflow = self.workflows[name]
        results = []

        # 순차 실행 (나중에 병렬/조건부 실행 추가 가능)
        for agent in workflow["agents"]:
            result = await agent.execute(task, context)
            results.append(result)
            # 다음 에이전트를 위한 컨텍스트 업데이트
            context.update(result)

        return {
            "workflow": name,
            "results": results,
            "final_context": context
        }
```

#### 4.2 기존 스팸 워크플로우
```python
# app/workflows/analysis_workflow.py
from app.workflows.workflow_manager import WorkflowManager
from app.agents.analysis.spam_detector import SpamDetectorAgent
from app.agents.analysis.verdict_agent import VerdictAgent

def create_spam_analysis_workflow():
    """기존 스팸 분석을 워크플로우로 변환"""
    manager = WorkflowManager()

    # 에이전트들 생성
    spam_detector = SpamDetectorAgent()
    verdict_agent = VerdictAgent()

    # 워크플로우 등록
    manager.register_workflow(
        name="spam_analysis",
        agents=[spam_detector, verdict_agent],
        plan_type="sequential"
    )

    return manager
```

### Phase 5: API 통합 (1주)

#### 5.1 오케스트레이터 라우터
```python
# app/routers/orchestrator_router.py
from fastapi import APIRouter, HTTPException
from app.orchestrator.mcp_app import AgentPlatformApp
from app.workflows.analysis_workflow import create_spam_analysis_workflow

router = APIRouter(prefix="/orchestrator", tags=["Agent Orchestrator"])

@router.post("/execute-workflow")
async def execute_workflow(
    workflow_name: str,
    task: str,
    context: Dict[str, Any] = {}
):
    """워크플로우 실행"""
    try:
        # 플랫폼 초기화
        platform = AgentPlatformApp()

        # 워크플로우 매니저 생성
        if workflow_name == "spam_analysis":
            manager = create_spam_analysis_workflow()
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        # 워크플로우 실행
        async with platform.run() as app:
            result = await manager.execute_workflow(workflow_name, task, context)
            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows")
async def list_workflows():
    """사용 가능한 워크플로우 목록"""
    return {
        "workflows": [
            {
                "name": "spam_analysis",
                "description": "Email spam detection and analysis",
                "agents": ["spam_detector", "verdict_agent"]
            },
            {
                "name": "research_report",
                "description": "Web research and report generation",
                "agents": ["searcher", "fact_checker", "report_writer"]
            }
        ]
    }
```

## 🔄 기존 코드 호환성 유지

### 기존 API 엔드포인트 유지
```python
# app/routers/legacy_mcp_router.py
# 기존 /mcp/analyze-email 엔드포인트를 새 워크플로우로 리다이렉트

@router.post("/analyze-email", response_model=GatewayResponse)
async def analyze_email_legacy(email: EmailInput):
    """기존 스팸 분석 API (호환성 유지)"""
    # 새 워크플로우 시스템으로 리다이렉트
    context = {
        "email": {
            "subject": email.subject,
            "content": email.content,
            "sender": email.sender
        }
    }

    # 워크플로우 실행
    result = await execute_workflow("spam_analysis", "analyze email", context)

    # 기존 응답 형식으로 변환
    return convert_to_legacy_response(result)
```

## 📈 마이그레이션 이점

### 1. **확장성** ✅
- 새로운 에이전트 쉽게 추가
- 다양한 워크플로우 조합 가능
- 도메인별 전문 에이전트 개발

### 2. **재사용성** ✅
- 에이전트 간 독립성
- 워크플로우 재조합 가능
- 모듈화된 구조

### 3. **호환성** ✅
- 기존 API 유지
- 점진적 마이그레이션
- 기존 모델/서비스 재활용

### 4. **미래 확장** ✅
- 연구 보고서 생성
- 데이터 분석 파이프라인
- 고객 서비스 자동화
- 콘텐츠 생성 등

## 🎯 최종 목표 달성

이 마이그레이션을 통해:
1. **현재**: 스팸 탐지 시스템
2. **목표**: 범용 에이전트 오케스트레이션 플랫폼

제시된 연구 오케스트레이터 코드가 자연스럽게 통합되어 **진정한 에이전트 플랫폼**이 완성됩니다! 🚀
