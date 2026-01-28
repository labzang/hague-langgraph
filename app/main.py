"""FastAPI 기반 RAG 백엔드 서버 - 통합 버전

이 파일은 기존의 api_server.py와 main.py를 통합한 버전입니다.
- FastAPI 애플리케이션 설정
- 벡터스토어 및 RAG 체인 초기화
- API 엔드포인트 정의
- 로컬 Midm 모델 지원
"""

import os
import sys
import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import time

import uvicorn
import psycopg2
import subprocess
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# DB 테스트를 위한 설정 import
from app.core.config import settings

# 환경 변수 로드
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# 비동기 컨텍스트 매니저, 데이터베이스 초기화
def test_neon_db_connection() -> dict:
    """Neon DB 연결 테스트 및 상세 정보 반환.

    서버 시작 시 한 번만 실행되며, 연결 실패 시 재시도하지 않고 로그만 남깁니다.
    """
    logger.info("[DB 연결] 데이터베이스 연결 테스트 시작...")

    final_url = settings.database_url
    parsed_final = urlparse(final_url)
    masked_final = f"{parsed_final.scheme}://{parsed_final.hostname}:{parsed_final.port}{parsed_final.path}"

    # psycopg2는 postgresql+asyncpg:// 형식을 이해하지 못하므로 변환 필요
    db_url_for_psycopg2 = final_url
    if db_url_for_psycopg2.startswith("postgresql+asyncpg://"):
        db_url_for_psycopg2 = db_url_for_psycopg2.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif db_url_for_psycopg2.startswith("postgresql+psycopg2://"):
        db_url_for_psycopg2 = db_url_for_psycopg2.replace("postgresql+psycopg2://", "postgresql://", 1)

    try:
        conn = psycopg2.connect(db_url_for_psycopg2)

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]

        try:
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            vector_ext = cursor.fetchone()
            has_vector = vector_ext is not None
        except Exception:
            has_vector = False

        cursor.close()
        conn.close()

        logger.info(f"[DB 연결] ✅ 연결 성공 (PostgreSQL {db_version.split(',')[0] if ',' in db_version else db_version})")
        if has_vector:
            logger.info("[DB 연결] pgvector 확장 확인됨")

        return {
            "status": "success",
            "database_version": db_version,
            "connection_string": masked_final,
            "has_vector_extension": has_vector
        }

    except psycopg2.OperationalError as exc:
        error_msg = str(exc)
        logger.warning(f"[DB 연결] ❌ 연결 실패: {error_msg}")
        logger.warning("[DB 연결] 서버는 계속 실행되지만 데이터베이스 기능이 제한될 수 있습니다.")
        return {
            "status": "failed",
            "error": error_msg,
        }

    except Exception as exc:
        logger.error(f"[DB 연결] 예상치 못한 오류: {exc}")
        return {
            "status": "error",
            "error": str(exc)
        }


async def run_auto_migrations():
    """Alembic 마이그레이션 적용 (기존 마이그레이션만 적용, 자동 생성 없음)."""
    logger.info("[마이그레이션] 기존 마이그레이션 적용 중...")

    try:
        # 마이그레이션 적용만 수행 (자동 생성 제거)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        if result.returncode == 0:
            if "Target database is not up to date" in result.stderr:
                logger.info("[마이그레이션] ✅ 마이그레이션 적용 완료")
            elif result.stdout.strip():
                logger.info("[마이그레이션] ✅ 마이그레이션 적용 완료")
            else:
                logger.info("[마이그레이션] 이미 최신 상태입니다")
        else:
            # 실패해도 서버는 계속 실행
            logger.warning(f"[마이그레이션] 마이그레이션 적용 경고: {result.stderr}")
            logger.warning("[마이그레이션] 서버는 계속 실행되지만 마이그레이션이 적용되지 않았을 수 있습니다.")

    except FileNotFoundError:
        logger.warning("[마이그레이션] Alembic이 설치되지 않았습니다. 'pip install alembic'을 실행하세요.")
    except Exception as e:
        # 마이그레이션 실패해도 서버는 계속 실행
        logger.warning(f"[마이그레이션] 마이그레이션 적용 중 오류 (무시됨): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수."""
    import asyncio

    # 시작 시
    logger.info("="*60)
    logger.info("[시작] FastAPI RAG 애플리케이션 시작 중...")
    logger.info("="*60)

    # Neon DB 연결 테스트
    try:
        test_result = test_neon_db_connection()
        app.state.db_test_result = test_result
    except Exception as e:
        logger.error(f"[오류] 데이터베이스 연결 테스트 실패: {e}")
        app.state.db_test_result = {"error": str(e)}

    # Alembic 마이그레이션 자동 적용
    try:
        await run_auto_migrations()
    except Exception as e:
        logger.error(f"[오류] 마이그레이션 자동 적용 실패: {e}")
        logger.error(traceback.format_exc())

    logger.info("[완료] 애플리케이션 준비 완료!")

    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        # 정상적인 종료 신호 - 조용히 처리
        pass
    finally:
        # 종료 시 정리 작업 (모든 예외를 조용히 처리)
        try:
            logger.info("[종료] 애플리케이션 종료 중...")

            # 데이터베이스 연결 종료 (타임아웃 설정)
            try:
                from app.core.database import close_database
                # 최대 3초 대기
                await asyncio.wait_for(close_database(), timeout=3.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # 타임아웃이나 취소는 정상적인 종료로 처리
                pass
            except Exception as e:
                # 기타 예외는 경고만 로깅
                logger.warning(f"[경고] 데이터베이스 종료 중 오류 (무시됨): {e}")

        except (asyncio.CancelledError, KeyboardInterrupt):
            # 종료 중 취소 신호는 정상적인 종료로 처리
            pass
        except Exception:
            # 모든 기타 예외는 조용히 무시 (종료 중이므로)
            pass


# FastAPI 인스턴스 생성
app = FastAPI(
    title="RAG API Server",
    version="1.0.0",
    description="LangChain과 pgvector를 사용한 RAG API 서버",
    lifespan=lifespan,
)


# 미들웨어 설정 (CORS, 로깅, 에러 처리)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",  # 개발 환경용, 프로덕션에서는 특정 도메인으로 제한
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["*"],
)


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 예외를 캐치하여 로깅."""
    error_msg = str(exc)
    logger.error(f"[오류] 전역 예외 발생: {error_msg}")
    logger.error(f"[오류] 요청 경로: {request.url.path}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"서버 내부 오류: {error_msg}",
            "path": request.url.path,
        },
    )


# 라우터 등록 (API 엔드포인트 정의)
# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Soccer chat 라우터를 먼저 등록 (챗팅 질문 처리)
try:
    from app.api.v10.soccer.chat_router import router as soccer_chat_router
    api_v10_soccer_prefix = "/api/v10/soccer"
    chat_router_prefix = api_v10_soccer_prefix + "/chat"

    app.include_router(
        soccer_chat_router,
        prefix=chat_router_prefix,
        tags=["soccer", "chat"]
    )
    logger.info(f"[라우터] chat_router 등록 완료")
    logger.info(f"[라우터] 경로: {chat_router_prefix}/query")
except Exception as chat_error:
    logger.error(f"[라우터 오류] chat_router 등록 실패: {chat_error}")
    logger.error(traceback.format_exc())

# Soccer player 라우터를 먼저 등록 (다른 라우터와 독립적으로)
try:
    from app.api.v10.soccer.player_router import router as soccer_player_router
    api_v10_soccer_prefix = "/api/v10/soccer"
    player_router_prefix = api_v10_soccer_prefix + "/player"

    app.include_router(
        soccer_player_router,
        prefix=player_router_prefix,
        tags=["soccer", "player"]
    )
    logger.info(f"[라우터] player_router 등록 완료")
    logger.info(f"[라우터] 경로: {player_router_prefix}/upload")

    # 등록된 라우터 확인
    player_routes_found = []
    for route in app.routes:
        if hasattr(route, 'path') and 'player' in route.path:
            methods = getattr(route, 'methods', set())
            player_routes_found.append((route.path, methods))
            logger.info(f"[라우터 확인] 등록된 경로: {route.path} (메서드: {methods})")

    if not player_routes_found:
        logger.warning("[라우터 경고] player 라우터가 등록되지 않았습니다!")
    else:
        logger.info(f"[라우터 확인] 총 {len(player_routes_found)}개의 player 라우터가 등록되었습니다.")
except Exception as player_error:
    logger.error(f"[라우터 오류] player_router 등록 실패: {player_error}")
    logger.error(traceback.format_exc())

# Soccer team 라우터 등록
try:
    from app.api.v10.soccer.team_router import router as soccer_team_router
    api_v10_soccer_prefix = "/api/v10/soccer"
    team_router_prefix = api_v10_soccer_prefix + "/team"

    app.include_router(
        soccer_team_router,
        prefix=team_router_prefix,
        tags=["soccer", "team"]
    )
    logger.info(f"[라우터] team_router 등록 완료")
    logger.info(f"[라우터] 경로: {team_router_prefix}/upload")
except Exception as team_error:
    logger.error(f"[라우터 오류] team_router 등록 실패: {team_error}")
    logger.error(traceback.format_exc())

# Soccer stadium 라우터 등록
try:
    from app.api.v10.soccer.stadium_router import router as soccer_stadium_router
    api_v10_soccer_prefix = "/api/v10/soccer"
    stadium_router_prefix = api_v10_soccer_prefix + "/stadium"

    app.include_router(
        soccer_stadium_router,
        prefix=stadium_router_prefix,
        tags=["soccer", "stadium"]
    )
    logger.info(f"[라우터] stadium_router 등록 완료")
    logger.info(f"[라우터] 경로: {stadium_router_prefix}/upload")
except Exception as stadium_error:
    logger.error(f"[라우터 오류] stadium_router 등록 실패: {stadium_error}")
    logger.error(traceback.format_exc())

# Soccer schedule 라우터 등록
try:
    from app.api.v10.soccer.schedule_router import router as soccer_schedule_router
    api_v10_soccer_prefix = "/api/v10/soccer"
    schedule_router_prefix = api_v10_soccer_prefix + "/schedule"

    app.include_router(
        soccer_schedule_router,
        prefix=schedule_router_prefix,
        tags=["soccer", "schedule"]
    )
    logger.info(f"[라우터] schedule_router 등록 완료")
    logger.info(f"[라우터] 경로: {schedule_router_prefix}/upload")
except Exception as schedule_error:
    logger.error(f"[라우터 오류] schedule_router 등록 실패: {schedule_error}")
    logger.error(traceback.format_exc())

# 다른 라우터 등록
try:
    # Admin 라우터 등록
    from app.api.v10.product import (
        consumer_router,
        order_router,
        product_router,
        email_router,
    )
    from app.api.v10.admin import upload_router

    api_prefix = "/api/v1/admin"
    api_v10_prefix = "/api/v10/admin"

    app.include_router(
        consumer_router.router,
        prefix=api_prefix+"/consumers",
        tags=["consumers"]
    )
    app.include_router(
        order_router.router,
        prefix=api_prefix+"/orders",
        tags=["orders"]
    )
    app.include_router(
        product_router.router,
        prefix=api_prefix+"/products",
        tags=["products"]
    )
    app.include_router(
        email_router.router,
        prefix=api_prefix+"/emails",
        tags=["emails"]
    )
    app.include_router(
        upload_router.router,
        prefix=api_v10_prefix,
        tags=["admin", "upload"]
    )
    logger.info("[성공] 기타 라우터 등록 완료")
except ImportError as e:
    logger.warning(f"[경고] 일부 라우터 import 실패: {e}")
except Exception as e:
    logger.warning(f"[경고] 일부 라우터 등록 실패: {e}")


# 루트 엔드포인트
@app.get("/", tags=["root"])
async def root() -> dict:
    """루트 엔드포인트."""
    return {
        "message": "RAG API Server",
        "version": "1.0.0",
        "status": "running"
    }


# 등록된 라우터 확인 엔드포인트 (디버깅용)
@app.get("/api/routes", tags=["debug"])
async def get_routes() -> dict:
    """등록된 모든 라우터 경로를 반환합니다 (디버깅용)."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'N/A')
            })
    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x["path"]),
        "player_routes": [r for r in routes if "player" in r["path"]],
        "stadium_routes": [r for r in routes if "stadium" in r["path"]],
        "team_routes": [r for r in routes if "team" in r["path"]],
        "schedule_routes": [r for r in routes if "schedule" in r["path"]],
    }


# 헬스체크 엔드포인트
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


# ===== 메인 실행 =====
if __name__ == "__main__":
    # 포트 8000만 사용 (고정)
    port = 8000

    # 포트 사용 중인지 확인
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
    except OSError:
        sock.close()
        logger.error("="*60)
        logger.error(f"[오류] 포트 {port}가 이미 사용 중입니다. 다른 프로세스를 종료하거나 포트를 해제해주세요.")
        logger.error("="*60)
        sys.exit(1)

    logger.info("\n" + "="*60)
    logger.info("[실행] FastAPI 서버 시작")
    logger.info("="*60)
    logger.info(f"[서버] http://127.0.0.1:{port} 에서 실행됩니다")
    logger.info(f"[문서] http://127.0.0.1:{port}/docs 에서 API 문서를 확인할 수 있습니다")
    logger.info("="*60 + "\n")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=settings.debug if hasattr(settings, "debug") else False,
    )
