"""FastAPI 메인 애플리케이션."""

import os
import traceback
from contextlib import asynccontextmanager
from typing import List

import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_community.vectorstores import PGVector
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

try:
    # 프로젝트 루트에서 실행할 때
    from app.api.models import HealthResponse
    from app.api.routes import search
    from app.config import settings
    from app.router import chat_router
except ImportError:
    # app 디렉토리에서 직접 실행할 때
    from api.models import HealthResponse
    from api.routes import search
    from config import settings
    from router import chat_router


class SimpleEmbeddings(Embeddings):
    """간단한 더미 임베딩 클래스 (OpenAI API 키가 없을 때 사용)"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서들을 임베딩으로 변환"""
        return [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        """쿼리를 임베딩으로 변환"""
        return [0.1, 0.2, 0.3, 0.4, 0.5]


def wait_for_postgres() -> None:
    """PostgreSQL 데이터베이스가 준비될 때까지 대기.

    Docker 컨테이너 대신 외부(Postgres/Neon 등) 인스턴스를 사용하므로,
    `Settings.database_url`을 사용해 접속을 시도합니다.
    """
    import time

    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # DATABASE_URL 포함: postgresql://... 형태의 전체 URI 사용
            conn = psycopg2.connect(settings.database_url)
            conn.close()
            print("[성공] PostgreSQL 데이터베이스 연결 성공!")
            return
        except psycopg2.OperationalError as exc:
            retry_count += 1
            print(
                f"[대기] PostgreSQL 연결 대기 중... ({retry_count}/{max_retries}) - {exc}"
            )
            time.sleep(2)

    raise Exception("PostgreSQL 데이터베이스에 연결할 수 없습니다.")


def setup_vectorstore() -> PGVector:
    """pgvector 벡터스토어 설정"""

    # 데이터베이스 연결 정보
    connection_string = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'langchain_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'langchain_password')}@"
        f"{os.getenv('POSTGRES_HOST', 'postgres')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'langchain_db')}"
    )

    # 임베딩 모델 설정 (OpenAI API 키가 있으면 OpenAI, 없으면 더미)
    if os.getenv("OPENAI_API_KEY"):
        embeddings = OpenAIEmbeddings()
        print("[AI] OpenAI 임베딩 모델을 사용합니다.")
    else:
        embeddings = SimpleEmbeddings()
        print("[더미] 더미 임베딩 모델을 사용합니다. (OpenAI API 키가 설정되지 않음)")

    # PGVector 벡터스토어 생성
    vectorstore = PGVector(
        connection_string=connection_string,
        embedding_function=embeddings,
        collection_name="langchain_collection",
    )

    return vectorstore


def add_sample_documents(vectorstore: PGVector):
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
            page_content="Docker는 애플리케이션을 컨테이너로 패키징하여 배포를 쉽게 만드는 플랫폼입니다.",
            metadata={"source": "docker_intro", "type": "definition"},
        ),
        Document(
            page_content="Python은 데이터 과학과 AI 개발에 널리 사용되는 프로그래밍 언어입니다.",
            metadata={"source": "python_intro", "type": "definition"},
        ),
    ]

    print("[추가] 샘플 문서들을 벡터스토어에 추가 중...")
    vectorstore.add_documents(sample_docs)
    print("[완료] 샘플 문서 추가 완료!")


def setup_rag_chain(vectorstore: PGVector):
    """RAG (Retrieval-Augmented Generation) 체인 설정"""

    # 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_template("""
다음 컨텍스트를 바탕으로 질문에 답해주세요:

컨텍스트: {context}

질문: {question}

답변:
""")

    # 검색기 설정
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # LLM 설정 및 RAG 체인 구성
    if os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        print("[AI] OpenAI GPT 모델을 사용합니다.")

        # 실제 RAG 체인 구성
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
    else:
        print("[더미] 더미 LLM을 사용합니다. (OpenAI API 키가 설정되지 않음)")

        # 더미 RAG 함수 (OpenAI API 키가 없을 때)
        def dummy_rag_function(question: str) -> str:
            """OpenAI API 키가 없을 때 사용하는 더미 RAG 함수"""
            # invoke 메서드를 사용하여 문서 검색
            docs = retriever.invoke(question)
            context = "\n".join([f"- {doc.page_content}" for doc in docs])

            return f"""[검색] 검색된 관련 문서들:
{context}

[더미응답] 위의 문서들이 '{question}' 질문과 관련된 내용입니다.
실제 AI 응답을 받으려면 OpenAI API 키를 설정해주세요.
하지만 벡터 검색 기능은 정상적으로 작동하고 있습니다!"""

        # RunnableLambda로 래핑하여 체인과 호환되도록 함
        rag_chain = RunnableLambda(dummy_rag_function)

    return rag_chain


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수."""
    # 시작 시
    print("[시작] FastAPI RAG 애플리케이션 시작 중...")

    # 데이터베이스 연결 시도 (실패해도 계속 진행)
    db_connected = False
    try:
        wait_for_postgres()
        db_connected = True
        print("[설정] 벡터스토어 초기화 중...")

        # 벡터스토어 설정
        vectorstore = setup_vectorstore()

        # 샘플 문서 추가 (기존 데이터가 있는지 확인)
        try:
            # 기존 문서 수 확인
            existing_docs = vectorstore.similarity_search("test", k=1)
            if not existing_docs:
                add_sample_documents(vectorstore)
            else:
                print("[정보] 기존 문서가 발견되어 샘플 문서 추가를 건너뜁니다.")
        except Exception as e:
            print(f"[경고] 기존 문서 확인 중 오류 발생, 샘플 문서를 추가합니다: {e}")
            add_sample_documents(vectorstore)

        # RAG 체인 설정
        print("[설정] RAG 체인 설정 중...")
        rag_chain = setup_rag_chain(vectorstore)

        # 앱 상태에 저장
        app.state.vectorstore = vectorstore
        app.state.rag_chain = rag_chain

    except Exception as e:
        print(f"[경고] 데이터베이스 연결 실패, 더미 모드로 실행합니다: {e}")
        # 더미 벡터스토어와 RAG 체인 설정
        app.state.vectorstore = None
        app.state.rag_chain = None
        db_connected = False

    app.state.db_connected = db_connected

    # 순환 의존성을 피하기 위해 지연 임포트
    try:
        from app.core.llm import create_llm_from_config
    except ImportError:
        from core.llm import create_llm_from_config

    # 데이터베이스 연결이 성공한 경우에만 기존 벡터스토어 초기화 시도
    if db_connected:
        try:
            try:
                from app.core.vectorstore import initialize_vectorstore
            except ImportError:
                from core.vectorstore import initialize_vectorstore
            initialize_vectorstore()
        except Exception as e:
            print(f"[경고] 기존 벡터스토어 초기화 실패: {e}")

    # 🔧 LLM 생성 및 전역 설정

    llm = create_llm_from_config(settings)
    if llm:
        print("[성공] 사용자 정의 LLM이 설정되었습니다.")
        # 전역 변수로 저장하여 라우터에서 사용
        app.state.llm = llm
    else:
        print("[경고] LLM 설정이 불완전합니다. 기본 동작으로 실행합니다.")
        app.state.llm = None

    # 🔧 Chat Service (QLoRA) 초기화
    if settings.use_chat_service and settings.chat_model_path:
        try:
            try:
                from app.service.chat_service import create_qlora_chat_service
            except ImportError:
                from service.chat_service import create_qlora_chat_service

            print("[설정] QLoRA Chat Service 초기화 중...")
            chat_service = create_qlora_chat_service(
                model_name_or_path=settings.chat_model_path,
                adapter_path=settings.chat_adapter_path,
            )
            app.state.chat_service = chat_service
            print("[성공] QLoRA Chat Service 초기화 완료!")
        except Exception as e:
            print(f"[경고] Chat Service 초기화 실패: {e}")
            app.state.chat_service = None
    else:
        app.state.chat_service = None
        if settings.use_chat_service:
            print("[경고] Chat Service를 사용하려면 CHAT_MODEL_PATH를 설정하세요.")

    print("[완료] 애플리케이션 준비 완료!")
    yield
    # 종료 시
    print("[종료] 애플리케이션 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="LangChain과 pgvector를 사용한 RAG API 서버",
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

# 전역 예외 핸들러 추가


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 예외를 캐치하여 로깅."""
    error_msg = str(exc)
    print(f"[오류] 전역 예외 발생: {error_msg}")
    print(f"[오류] 요청 경로: {request.url.path}")
    print(f"[오류] 요청 메서드: {request.method}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"서버 내부 오류: {error_msg}",
            "path": request.url.path,
        },
    )


# API 라우터 등록
app.include_router(search.router)
app.include_router(chat_router.router)


@app.get("/", tags=["root"])
async def root() -> dict:
    """루트 엔드포인트."""
    return {
        "message": "LangChain RAG API에 오신 것을 환영합니다!",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/hello-world", tags=["demo"])
async def hello_world() -> dict:
    """Hello World 데모 엔드포인트 - app.py 기능 통합"""
    try:
        # 데이터베이스 연결 상태 확인
        if not app.state.db_connected or not app.state.rag_chain:
            return {
                "message": "LangChain + pgvector Hello World 데모 (더미 모드)",
                "results": [
                    {
                        "question": "데이터베이스 연결 상태",
                        "answer": "데이터베이스에 연결되지 않았습니다. 환경 변수(DATABASE_URL 또는 POSTGRES_*)를 확인해주세요.",
                        "status": "warning",
                    }
                ],
                "status": "partial",
                "db_connected": False,
            }

        # 테스트 질문들
        test_questions = [
            "LangChain이 무엇인가요?",
            "pgvector는 어떤 기능을 제공하나요?",
            "Docker의 장점은 무엇인가요?",
            "Python이 AI 개발에 인기 있는 이유는?",
        ]

        results = []

        for question in test_questions:
            try:
                # RAG 체인을 사용하여 답변 생성
                answer = app.state.rag_chain.invoke(question)
                results.append(
                    {"question": question, "answer": answer, "status": "success"}
                )
            except Exception as e:
                results.append(
                    {
                        "question": question,
                        "answer": f"오류 발생: {str(e)}",
                        "status": "error",
                    }
                )

        return {
            "message": "LangChain + pgvector Hello World 데모",
            "results": results,
            "status": "completed",
            "db_connected": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Hello World 데모 실행 중 오류: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """헬스체크 엔드포인트."""
    try:
        # 데이터베이스 연결 확인 (DATABASE_URL 기반)
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
        openai_configured=settings.openai_api_key is not None,
    )


# python -m app.main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
