"""API 요청/응답 모델."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    """벡터 검색 요청 모델."""

    query: str = Field(..., description="검색할 질문 또는 키워드")
    k: int = Field(default=5, ge=1, le=20, description="반환할 문서 개수")


class DocumentResponse(BaseModel):
    """문서 응답 모델."""

    content: str = Field(..., description="문서 내용")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="문서 메타데이터")
    score: Optional[float] = Field(None, description="유사도 점수")


class SearchResponse(BaseModel):
    """벡터 검색 응답 모델."""

    query: str = Field(..., description="검색 쿼리")
    documents: List[DocumentResponse] = Field(..., description="검색된 문서 목록")
    count: int = Field(..., description="반환된 문서 개수")


class RAGRequest(BaseModel):
    """RAG 질의 요청 모델."""

    question: str = Field(..., description="질문 내용")
    k: int = Field(default=2, ge=1, le=10, description="검색에 사용할 문서 개수")


class RAGResponse(BaseModel):
    """RAG 질의 응답 모델."""

    question: str = Field(..., description="질문 내용")
    answer: str = Field(..., description="생성된 답변")
    sources: Optional[List[DocumentResponse]] = Field(
        None, description="참조된 문서 목록"
    )
    # 프론트엔드 호환성을 위한 필드
    retrieved_documents: Optional[List[DocumentResponse]] = Field(
        None, description="검색된 문서 목록 (프론트엔드 호환)"
    )
    retrieved_count: Optional[int] = Field(
        None, description="검색된 문서 개수 (프론트엔드 호환)"
    )

    @model_validator(mode='after')
    def set_retrieved_fields(self) -> 'RAGResponse':
        """sources가 있으면 retrieved_documents와 retrieved_count를 자동 설정."""
        if self.sources and not self.retrieved_documents:
            self.retrieved_documents = self.sources
        if self.retrieved_documents is not None and self.retrieved_count is None:
            self.retrieved_count = len(self.retrieved_documents)
        return self


class HealthResponse(BaseModel):
    """헬스체크 응답 모델."""

    status: str = Field(..., description="서비스 상태")
    version: str = Field(..., description="애플리케이션 버전")
    database: str = Field(..., description="데이터베이스 연결 상태")
    openai_configured: bool = Field(..., description="OpenAI API 키 설정 여부")

