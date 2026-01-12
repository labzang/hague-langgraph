"""벡터 검색 API 라우트."""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from langchain_core.documents import Document

from app.api.models import SearchRequest, SearchResponse, DocumentResponse
from app.core.vectorstore import get_vectorstore, VectorStoreType

router = APIRouter(prefix="/search", tags=["search"])


def get_vectorstore_dependency() -> VectorStoreType:
    """벡터스토어 의존성 주입."""
    return get_vectorstore()


@router.post("", response_model=SearchResponse)
async def vector_search(
    request: SearchRequest,
    vectorstore: VectorStoreType = Depends(get_vectorstore_dependency),
) -> SearchResponse:
    """
    벡터 유사도 검색을 수행합니다.

    - **query**: 검색할 질문 또는 키워드
    - **k**: 반환할 문서 개수 (1-20)
    """
    try:
        # 유사도 검색 수행
        docs_with_scores = vectorstore.similarity_search_with_score(
            request.query, k=request.k
        )

        # 응답 모델로 변환
        documents = [
            DocumentResponse(
                content=doc.page_content,
                metadata=doc.metadata,
                score=float(score),
            )
            for doc, score in docs_with_scores
        ]

        return SearchResponse(
            query=request.query,
            documents=documents,
            count=len(documents),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")


@router.get("/health")
async def search_health() -> dict:
    """검색 서비스 헬스체크."""
    return {"status": "healthy", "service": "vector_search"}

