"""
기본 모델들
이메일 입력 및 게이트웨이 응답을 위한 Pydantic 모델들
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class EmailInput(BaseModel):
    """이메일 입력 모델"""
    subject: str
    content: str
    sender: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class GatewayResponse(BaseModel):
    """게이트웨이 응답 모델"""
    is_spam: bool
    confidence: float
    koelectra_decision: str
    exaone_analysis: Optional[str] = None
    processing_path: str
    timestamp: datetime
    metadata: Dict[str, Any]
