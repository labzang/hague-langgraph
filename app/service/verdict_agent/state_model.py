"""
상태 관리 모델들
처리 세션 및 상태 추적을 위한 Pydantic 모델들
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_model import EmailInput

class VerdictState(BaseModel):
    """판독 에이전트 상태 모델"""
    # 입력 데이터
    email_subject: str
    email_content: str
    koelectra_result: Dict[str, Any]

    # 처리 상태
    analysis_type: str = "detailed"  # "detailed" or "quick"
    exaone_prompt: Optional[str] = None
    exaone_response: Optional[str] = None

    # 결과
    final_verdict: Optional[str] = None  # "spam", "normal", "uncertain"
    confidence_adjustment: float = 0.0
    analysis_summary: Optional[str] = None

    # 메타데이터
    processing_steps: List[str] = []
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

class ProcessingSessionState(BaseModel):
    """처리 세션 상태 모델"""
    session_id: str
    email_input: EmailInput
    koelectra_result: Optional[Dict[str, Any]] = None
    verdict_result: Optional[Dict[str, Any]] = None
    final_decision: Optional[str] = None
    confidence_score: float = 0.0
    processing_steps: List[str] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "processing"  # "processing", "completed", "error"
    error: Optional[str] = None
