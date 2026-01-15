"""FastAPI 기반 RAG 백엔드 서버 - 통합 버전

이 파일은 기존의 api_server.py와 main.py를 통합한 버전입니다.
- FastAPI 애플리케이션 설정
- 벡터스토어 및 RAG 체인 초기화
- API 엔드포인트 정의
- 로컬 Midm 모델 지원
"""

import os
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from pydantic import BaseModel

from app.api.models import HealthResponse
from app.api.routes import search

# 로컬 모듈 imports
from app.config import settings
from app.router import chat_router, mcp_router

# 환경 변수 로드
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)


# ===== Pydantic 모델들 =====
class QueryRequest(BaseModel):
    """Query request model."""

    question: str
    k: int = 3


class DocumentRequest(BaseModel):
    """Document add request model."""

    content: str
    metadata: Optional[dict] = None


class DocumentListRequest(BaseModel):
    """Multiple documents add request model."""

    documents: List[dict]  # [{"content": "...", "metadata": {...}}]


# ===== 간단한 더미 임베딩 클래스 =====
class SimpleEmbeddings(Embeddings):
    """간단한 더미 임베딩 클래스 (OpenAI API 키가 없을 때 사용)"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서들을 임베딩으로 변환"""
        return [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        """쿼리를 임베딩으로 변환"""
        return [0.1, 0.2, 0.3, 0.4, 0.5]


# ===== 유틸리티 함수들 =====
def wait_for_postgres() -> bool:
    """PostgreSQL 데이터베이스가 준비될 때까지 대기."""
    import time

    max_retries = 10  # 더 짧게 설정
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(settings.database_url)
            conn.close()
            print("[성공] PostgreSQL 데이터베이스 연결 성공!")
            return True
        except psycopg2.OperationalError as exc:
            retry_count += 1
            print(
                f"[대기] PostgreSQL 연결 대기 중... ({retry_count}/{max_retries}) - {exc}"
            )
            time.sleep(1)

    print(
        "[경고] PostgreSQL 데이터베이스에 연결할 수 없습니다. 더미 모드로 실행합니다."
    )
    return False


def setup_vectorstore():
    """pgvector 벡터스토어 설정"""
    try:
        from langchain_community.vectorstores import PGVector
    except ImportError:
        from langchain_postgres import PGVector

    # 임베딩 모델 설정
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings()
        print("[AI] OpenAI 임베딩 모델을 사용합니다.")
    else:
        embeddings = SimpleEmbeddings()
        print("[더미] 더미 임베딩 모델을 사용합니다.")

    # 데이터베이스 연결 정보
    connection_string = settings.database_url

    # PGVector 벡터스토어 생성
    vectorstore = PGVector(
        connection_string=connection_string,
        embedding_function=embeddings,
        collection_name="langchain_collection",
    )

    return vectorstore


def add_sample_documents(vectorstore):
    """샘플 문서들을 벡터스토어에 추가"""
    sample_docs = [
        Document(
            page_content="LangChain은 대규모 언어 모델을 활용한 애플리케이션 개발을 위한 프레임워크입니다.",
            metadata={"source": "langchain_intro", "type": "definition"},
        ),
        Document(
            page_content="pgvector는 PostgreSQL에서 벡터 유사도 검색을 가능하게 하는 확장입니다.",
            metadata={"source": "pgvector_intro", "type": "definition"},
        ),
        Document(
            page_content="Midm-2.0-Mini-Instruct는 한국어에 특화된 소형 언어 모델입니다.",
            metadata={"source": "midm_intro", "type": "definition"},
        ),
        Document(
            page_content="RAG(Retrieval-Augmented Generation)는 검색과 생성을 결합한 AI 기법입니다.",
            metadata={"source": "rag_intro", "type": "definition"},
        ),
    ]

    print("[추가] 샘플 문서들을 벡터스토어에 추가 중...")
    vectorstore.add_documents(sample_docs)
    print("[완료] 샘플 문서 추가 완료!")


def setup_rag_chain(vectorstore):
    """RAG (Retrieval-Augmented Generation) 체인 설정"""
    # 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_template("""
다음 컨텍스트를 바탕으로 질문에 답해주세요:

컨텍스트: {context}

질문: {question}

답변:
""")

    # 검색기 설정
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # LLM 설정 및 RAG 체인 구성
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
        print("[AI] OpenAI GPT 모델을 사용합니다.")

        def format_docs(docs: List[Document]) -> str:
            return "\n\n".join(doc.page_content for doc in docs)

        # 실제 RAG 체인 구성
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
    else:
        # 로컬 Midm 모델 사용
        try:
            from app.core.llm.providers.midm_local import create_midm_local_llm

            llm = create_midm_local_llm()
            print("[AI] 로컬 Midm 모델을 사용합니다.")

            def rag_with_midm(question: str) -> str:
                """Midm 모델을 사용한 RAG 함수"""
                docs = retriever.invoke(question)
                context = "\n\n".join([doc.page_content for doc in docs])

                # Midm 모델용 프롬프트
                prompt_text = f"""다음 컨텍스트를 바탕으로 질문에 답해주세요:

컨텍스트:
{context}

질문: {question}

답변: """

                response = llm.invoke(prompt_text)
                return response

            rag_chain = RunnableLambda(rag_with_midm)

        except Exception as e:
            print(f"[경고] Midm 모델 로드 실패: {e}")
            print("[더미] 더미 RAG 함수를 사용합니다.")

            # 더미 RAG 함수
            def dummy_rag_function(question: str) -> str:
                """더미 RAG 함수"""
                docs = retriever.invoke(question)
                context = "\n".join([f"- {doc.page_content}" for doc in docs])

                return f"""[검색] 검색된 관련 문서들:
{context}

[더미응답] 위의 문서들이 '{question}' 질문과 관련된 내용입니다.
실제 AI 응답을 받으려면 OpenAI API 키를 설정하거나 Midm 모델을 올바르게 설치해주세요."""

            rag_chain = RunnableLambda(dummy_rag_function)

    return rag_chain


# ===== FastAPI 애플리케이션 설정 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수."""
    # 시작 시
    print("[시작] FastAPI RAG 애플리케이션 시작 중...")

    # 데이터베이스 연결 시도
    db_connected = wait_for_postgres()

    if db_connected:
        try:
            print("[설정] 벡터스토어 초기화 중...")
            vectorstore = setup_vectorstore()

            # 샘플 문서 추가 (기존 데이터가 있는지 확인)
            try:
                existing_docs = vectorstore.similarity_search("test", k=1)
                if not existing_docs:
                    add_sample_documents(vectorstore)
                else:
                    print("[정보] 기존 문서가 발견되어 샘플 문서 추가를 건너뜁니다.")
            except Exception as e:
                print(
                    f"[경고] 기존 문서 확인 중 오류 발생, 샘플 문서를 추가합니다: {e}"
                )
                add_sample_documents(vectorstore)

            # RAG 체인 설정
            print("[설정] RAG 체인 설정 중...")
            rag_chain = setup_rag_chain(vectorstore)

            # 앱 상태에 저장
            app.state.vectorstore = vectorstore
            app.state.rag_chain = rag_chain
            app.state.db_connected = True

        except Exception as e:
            print(f"[경고] 벡터스토어 초기화 실패: {e}")
            app.state.vectorstore = None
            app.state.rag_chain = None
            app.state.db_connected = False
    else:
        app.state.vectorstore = None
        app.state.rag_chain = None
        app.state.db_connected = False

    print("[완료] 애플리케이션 준비 완료!")
    yield
    # 종료 시
    print("[종료] 애플리케이션 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="RAG API Server",
    version="1.0.0",
    description="LangChain과 pgvector를 사용한 RAG API 서버 (로컬 Midm 모델 지원)",
    lifespan=lifespan,
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 전역 예외 핸들러 =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 예외를 캐치하여 로깅."""
    error_msg = str(exc)
    print(f"[오류] 전역 예외 발생: {error_msg}")
    print(f"[오류] 요청 경로: {request.url.path}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"서버 내부 오류: {error_msg}",
            "path": request.url.path,
        },
    )


# ===== API 엔드포인트들 =====
@app.get("/", tags=["root"])
async def root() -> dict:
    """루트 엔드포인트."""
    return {
        "message": "RAG API Server",
        "version": "1.0.0",
        "endpoints": {
            "retrieve": "POST /retrieve - 유사 문서 검색",
            "rag": "POST /rag - RAG (검색 + 생성)",
            "documents": "POST /documents - 문서 추가",
            "documents/batch": "POST /documents/batch - 다중 문서 추가",
            "health": "GET /health - 헬스체크",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """헬스체크 엔드포인트."""
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db_status,
        openai_configured=os.getenv("OPENAI_API_KEY") is not None,
    )


@app.post("/retrieve", tags=["rag"])
async def retrieve(request: QueryRequest):
    """유사 문서 검색 (검색만 수행)."""
    if not app.state.vectorstore:
        raise HTTPException(
            status_code=500, detail="벡터스토어가 초기화되지 않았습니다"
        )

    try:
        results = app.state.vectorstore.similarity_search(request.question, k=request.k)

        return {
            "question": request.question,
            "k": request.k,
            "results": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in results
            ],
            "count": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag", tags=["rag"])
async def rag(request: QueryRequest):
    """RAG (Retrieval-Augmented Generation) - 검색 + 답변 생성."""
    if not app.state.rag_chain:
        raise HTTPException(status_code=500, detail="RAG 체인이 초기화되지 않았습니다")

    try:
        print(f"[RAG] 질문 수신: {request.question}, k={request.k}")

        # 문서 검색
        if app.state.vectorstore:
            retrieved_docs = app.state.vectorstore.similarity_search(
                request.question, k=request.k
            )
            print(f"[RAG] {len(retrieved_docs)}개 문서 검색됨")
        else:
            retrieved_docs = []

        # 답변 생성
        print("[RAG] 답변 생성 중...")
        answer = app.state.rag_chain.invoke(request.question)
        print(f"[RAG] 답변 생성 완료: {answer[:100]}...")

        return {
            "question": request.question,
            "answer": answer,
            "retrieved_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in retrieved_docs
            ],
            "retrieved_count": len(retrieved_docs),
        }
    except Exception as e:
        print(f"[RAG] 오류: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chain", tags=["rag"])
async def api_chain(request: QueryRequest):
    """LangChain RAG API - /api/chain 엔드포인트."""
    print(f"[LangChain] /api/chain 호출: {request.question}")
    # 기존 /rag 엔드포인트와 동일한 로직 사용
    return await rag(request)


@app.post("/api/graph", tags=["rag"])
async def api_graph(request: QueryRequest):
    """LangGraph API - /api/graph 엔드포인트."""
    try:
        print(f"[LangGraph] /api/graph 호출: {request.question}")

        # LangGraph 사용
        from app.graph import run_once

        print("[LangGraph] 그래프 실행 중...")
        answer = run_once(request.question)
        print(f"[LangGraph] 답변 생성 완료: {answer[:100]}...")

        # 문서 검색 (참조용)
        retrieved_docs = []
        if app.state.vectorstore:
            try:
                retrieved_docs = app.state.vectorstore.similarity_search(
                    request.question, k=request.k
                )
                print(f"[LangGraph] {len(retrieved_docs)}개 문서 검색됨 (참조용)")
            except Exception as e:
                print(f"[LangGraph] 문서 검색 실패: {e}")

        return {
            "question": request.question,
            "answer": answer,
            "retrieved_documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in retrieved_docs
            ],
            "retrieved_count": len(retrieved_docs),
        }
    except Exception as e:
        print(f"[LangGraph] 오류: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LangGraph 오류: {str(e)}")


@app.post("/documents", tags=["documents"])
async def add_document(request: DocumentRequest):
    """단일 문서를 벡터스토어에 추가."""
    if not app.state.vectorstore:
        raise HTTPException(
            status_code=500, detail="벡터스토어가 초기화되지 않았습니다"
        )

    try:
        doc = Document(
            page_content=request.content,
            metadata=request.metadata or {},
        )
        app.state.vectorstore.add_documents([doc])

        return {
            "message": "문서가 성공적으로 추가되었습니다",
            "content": request.content,
            "metadata": request.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/batch", tags=["documents"])
async def add_documents(request: DocumentListRequest):
    """다중 문서를 벡터스토어에 추가."""
    if not app.state.vectorstore:
        raise HTTPException(
            status_code=500, detail="벡터스토어가 초기화되지 않았습니다"
        )

    try:
        docs = [
            Document(
                page_content=doc["content"],
                metadata=doc.get("metadata", {}),
            )
            for doc in request.documents
        ]
        app.state.vectorstore.add_documents(docs)

        return {
            "message": f"{len(docs)}개 문서가 성공적으로 추가되었습니다",
            "count": len(docs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 기존 라우터 포함 (호환성 유지) =====
try:
    app.include_router(search.router)
    app.include_router(chat_router.router)
    app.include_router(mcp_router.router)
    print("[성공] MCP 라우터 포함 완료")
except Exception as e:
    print(f"[경고] 라우터 포함 실패: {e}")


# ===== 메인 실행 =====
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug if hasattr(settings, "debug") else False,
    )
