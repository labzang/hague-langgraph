"""
EXAONE 기반 판독 에이전트 패키지

이 패키지는 KoELECTRA 게이트웨이에서 불확실한 케이스를 받아
EXAONE 모델을 사용하여 정밀 스팸 분석을 수행합니다.

주요 기능:
- 적응적 분석 타입 선택 (상세/빠른)
- LangGraph 기반 워크플로우
- 신뢰도 기반 판정 조정
"""

from .graph import (
    analyze_email_verdict,
    analyze_email_with_tools,
    quick_verdict,
    get_workflow_info,
    get_mcp_agent_wrapper,
    MCPAgentWrapper
)
from .base_model import EmailInput, GatewayResponse
from .state_model import ProcessingSessionState, VerdictState

__all__ = [
    "analyze_email_verdict",
    "analyze_email_with_tools",
    "quick_verdict",
    "get_workflow_info",
    "get_mcp_agent_wrapper",
    "MCPAgentWrapper",
    "VerdictState",
    "EmailInput",
    "GatewayResponse",
    "ProcessingSessionState"
]
