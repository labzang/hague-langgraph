"""FastAPI 메인 애플리케이션."""

import asyncio
from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.models import HealthResponse
from app.api.routes import search
from app.router import chat_router


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
            print("✅ PostgreSQL 데이터베이스 연결 성공!")
            return
        except psycopg2.OperationalError as exc:
            retry_count += 1
            print(
                f"⏳ PostgreSQL 연결 대기 중... ({retry_count}/{max_retries}) - {exc}"
            )
            time.sleep(2)

    raise Exception("PostgreSQL 데이터베이스에 연결할 수 없습니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수."""
    # 시작 시
    print("🚀 FastAPI RAG 애플리케이션 시작 중...")
    wait_for_postgres()
    print("🔧 벡터스토어 초기화 중...")
    # 순환 의존성을 피하기 위해 지연 임포트
    from app.core.vectorstore import initialize_vectorstore

    initialize_vectorstore()
    # 🔧 LLM 생성 및 전역 설정
    from app.core.llm import create_llm_from_config

    llm = create_llm_from_config(settings)
    if llm:
        print("✅ 사용자 정의 LLM이 설정되었습니다.")
        # 전역 변수로 저장하여 라우터에서 사용
        app.state.llm = llm
    else:
        print("⚠️ LLM 설정이 불완전합니다. 기본 동작으로 실행합니다.")
        app.state.llm = None

    # 🔧 Chat Service (QLoRA) 초기화
    if settings.use_chat_service and settings.chat_model_path:
        try:
            from app.service.chat_service import create_qlora_chat_service

            print("🔧 QLoRA Chat Service 초기화 중...")
            chat_service = create_qlora_chat_service(
                model_name_or_path=settings.chat_model_path,
                adapter_path=settings.chat_adapter_path,
            )
            app.state.chat_service = chat_service
            print("✅ QLoRA Chat Service 초기화 완료!")
        except Exception as e:
            print(f"⚠️ Chat Service 초기화 실패: {e}")
            app.state.chat_service = None
    else:
        app.state.chat_service = None
        if settings.use_chat_service:
            print("⚠️ Chat Service를 사용하려면 CHAT_MODEL_PATH를 설정하세요.")

    print("✅ 애플리케이션 준비 완료!")
    yield
    # 종료 시
    print("👋 애플리케이션 종료 중...")


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
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 예외를 캐치하여 로깅."""
    error_msg = str(exc)
    print(f"❌ 전역 예외 발생: {error_msg}")
    print(f"❌ 요청 경로: {request.url.path}")
    print(f"❌ 요청 메서드: {request.method}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"서버 내부 오류: {error_msg}",
            "path": request.url.path,
        }
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

