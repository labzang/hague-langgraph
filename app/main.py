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
from urllib.parse import urlparse

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

# DB 테스트를 위한 설정 import
from app.core.config import settings

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


class ResearchRequest(BaseModel):
    """연구 태스크 요청 모델"""
    task: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 8192


class SpamAnalysisRequest(BaseModel):
    """스팸 분석 요청 모델"""
    email: dict  # {"subject": "...", "content": "...", "sender": "..."}


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
def test_neon_db_connection() -> dict:
    """Neon DB 연결 테스트 및 상세 정보 반환."""
    import time

    print("\n" + "="*60)
    print("[테스트] Neon DB 연결 테스트 시작")
    print("="*60)

    # 설정 정보 출력
    print(f"[설정] DATABASE_URL 환경변수 존재 여부: {settings.database_url_env is not None}")
    if settings.database_url_env:
        # 보안을 위해 URL 일부만 표시
        parsed_url = urlparse(settings.database_url_env)
        masked_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
        print(f"[설정] DATABASE_URL (마스킹됨): {masked_url}")
    else:
        print(f"[설정] POSTGRES_HOST: {settings.postgres_host}")
        print(f"[설정] POSTGRES_PORT: {settings.postgres_port}")
        print(f"[설정] POSTGRES_DB: {settings.postgres_db}")
        print(f"[설정] POSTGRES_USER: {settings.postgres_user}")

    # 최종 연결 문자열 (보안을 위해 일부만 표시)
    final_url = settings.database_url
    parsed_final = urlparse(final_url)
    masked_final = f"{parsed_final.scheme}://{parsed_final.hostname}:{parsed_final.port}{parsed_final.path}"
    print(f"[설정] 최종 연결 문자열 (마스킹됨): {masked_final}")
    print("-"*60)

    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            print(f"[시도] 연결 시도 {retry_count + 1}/{max_retries}...")
            conn = psycopg2.connect(settings.database_url)

            # 연결 성공 시 추가 정보 확인
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            print(f"[성공] PostgreSQL 버전: {db_version}")

            # pgvector 확장 확인
            try:
                cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                vector_ext = cursor.fetchone()
                if vector_ext:
                    print("[성공] pgvector 확장이 설치되어 있습니다.")
                else:
                    print("[경고] pgvector 확장이 설치되어 있지 않습니다.")
            except Exception as e:
                print(f"[경고] pgvector 확장 확인 실패: {e}")

            cursor.close()
            conn.close()

            print("="*60)
            print("[성공] ✅ Neon DB 연결 테스트 성공!")
            print("="*60 + "\n")

            return {
                "status": "success",
                "database_version": db_version,
                "connection_string": masked_final,
                "has_vector_extension": vector_ext is not None if 'vector_ext' in locals() else False
            }

        except psycopg2.OperationalError as exc:
            retry_count += 1
            error_msg = str(exc)
            print(f"[실패] 연결 실패 ({retry_count}/{max_retries}): {error_msg}")

            if retry_count < max_retries:
                print(f"[대기] 2초 후 재시도...")
                time.sleep(2)
            else:
                print("="*60)
                print("[실패] ❌ Neon DB 연결 테스트 실패!")
                print(f"[오류] 마지막 오류: {error_msg}")
                print("="*60 + "\n")

                return {
                    "status": "failed",
                    "error": error_msg,
                    "retries": retry_count
                }

        except Exception as exc:
            print("="*60)
            print(f"[오류] 예상치 못한 오류 발생: {exc}")
            print("="*60 + "\n")
            return {
                "status": "error",
                "error": str(exc)
            }

    return {
        "status": "failed",
        "error": "최대 재시도 횟수 초과",
        "retries": max_retries
    }


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
        # 더미 RAG 함수
        print("[더미] 더미 RAG 함수를 사용합니다.")

        def dummy_rag_function(question: str) -> str:
            """더미 RAG 함수"""
            docs = retriever.invoke(question)
            context = "\n".join([f"- {doc.page_content}" for doc in docs])

            return f"""[검색] 검색된 관련 문서들:
{context}

[더미응답] 위의 문서들이 '{question}' 질문과 관련된 내용입니다.
실제 AI 응답을 받으려면 OpenAI API 키를 설정해주세요."""

        rag_chain = RunnableLambda(dummy_rag_function)

    return rag_chain


# ===== FastAPI 애플리케이션 설정 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수."""
    # 시작 시
    print("\n" + "="*60)
    print("[시작] FastAPI RAG 애플리케이션 시작 중...")
    print("="*60 + "\n")

    # Neon DB 연결 테스트
    test_result = test_neon_db_connection()
    app.state.db_test_result = test_result

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
            "research": "POST /research - 연구 오케스트레이터",
            "spam-analysis": "POST /spam-analysis - 스팸 분석 워크플로우",
        },
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    """헬스체크 엔드포인트."""
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "openai_configured": os.getenv("OPENAI_API_KEY") is not None,
    }


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
    """채팅 에이전트 API - /api/graph 엔드포인트."""
    # /rag 엔드포인트와 동일한 로직 사용
    return await rag(request)


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


@app.post("/research", tags=["orchestrator"])
async def research_task(request: ResearchRequest):
    """연구 태스크 엔드포인트 (현재 미구현)."""
    raise HTTPException(
        status_code=501,
        detail="연구 오케스트레이터 기능이 현재 비활성화되어 있습니다."
    )


@app.post("/spam-analysis", tags=["orchestrator"])
async def spam_analysis_task(request: SpamAnalysisRequest):
    """스팸 분석 워크플로우 엔드포인트 (현재 미구현)."""
    raise HTTPException(
        status_code=501,
        detail="스팸 분석 워크플로우 기능이 현재 비활성화되어 있습니다."
    )


# 라우터는 제거됨 (DB 테스트만 유지)


# ===== 메인 실행 =====
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"[경로] 프로젝트 루트를 Python 경로에 추가: {project_root}")

    import uvicorn

    print("\n" + "="*60)
    print("[실행] FastAPI 서버 시작")
    print("="*60)
    print(f"[서버] http://127.0.0.1:8000 에서 실행됩니다")
    print(f"[문서] http://127.0.0.1:8000/docs 에서 API 문서를 확인할 수 있습니다")
    print("="*60 + "\n")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug if hasattr(settings, "debug") else False,
    )
