"""FastAPI 기반 RAG 백엔드 서버.

FastAPI 앱의 엔트리 포인트.
하는 일:
FastAPI 인스턴스 생성.
router/ 안의 라우터들 include.
CORS, 미들웨어, 로깅, 예외 핸들러 설정.
앱 시작 시점에:
LLM/벡터스토어/필요한 리소스들을 미리 로드(옵션),
또는 DI 컨테이너 초기화.
역할: 이 프로젝트의 “메인 실행 파일”이자 API 서버의 부팅 스크립트.

이 모듈은 순수하게 API 서버 역할만 수행하며,
Next.js 프론트엔드(`frontend/`)와는 HTTP 요청/응답으로만 통신합니다.
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.language_models.base import BaseLanguageModel
from pydantic import BaseModel

# 한국어 모델 지원
from app.core.korean_llm import init_korean_llm
from app.core.korean_embeddings import init_korean_embeddings

# Load environment variables from root directory
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

app = FastAPI(title="RAG API Server", version="1.0.0")

# CORS 설정 (Next.js 프론트엔드에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for vector store and RAG chain
vector_store: Optional[PGVector] = None
rag_chain = None


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


def init_vector_store() -> PGVector:
    """Initialize vector store with pgvector."""
    postgres_user = os.getenv("PGVECTOR_USER", os.getenv("POSTGRES_USER", "langchain_user"))
    postgres_password = os.getenv("PGVECTOR_PASSWORD", os.getenv("POSTGRES_PASSWORD", "langchain_password"))
    postgres_host = os.getenv("PGVECTOR_HOST", os.getenv("POSTGRES_HOST", "postgres"))
    postgres_port = int(os.getenv("PGVECTOR_PORT", os.getenv("POSTGRES_PORT", "5432")))
    postgres_db = os.getenv("PGVECTOR_DATABASE", os.getenv("POSTGRES_DB", "langchain_db"))

    connection_string = (
        f"postgresql+psycopg://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )

    # Use Korean embeddings or OpenAI embeddings
    embeddings = init_korean_embeddings()

    collection_name = os.getenv("COLLECTION_NAME", "rag_collection")

    store = PGVector(
        connection=connection_string,
        embeddings=embeddings,
        collection_name=collection_name,
    )

    return store


def init_llm() -> BaseLanguageModel:
    """
    Initialize LLM with Korean model or OpenAI.
    환경 변수에 따라 한국어 모델 또는 OpenAI 사용.
    """
    # OpenAI 사용 여부 확인
    use_openai = os.getenv("USE_OPENAI", "false").lower() == "true"
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if use_openai and openai_api_key:
        print("Using OpenAI LLM (gpt-3.5-turbo)")
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
        )
        print("✓ OpenAI LLM initialized!")
        return llm
    else:
        # 한국어 모델 사용
        return init_korean_llm()


@app.on_event("startup")
async def startup_event():
    """Initialize vector store and RAG chain on startup."""
    global vector_store, rag_chain

    try:
        print("Initializing vector store...")
        vector_store = init_vector_store()
        print("✓ Vector store initialized!")

        print("Initializing LLM...")
        llm = init_llm()

        # Create RAG prompt template (Korean)
        template = """다음 컨텍스트를 바탕으로 질문에 답변해주세요.

컨텍스트:
{context}

질문: {question}

답변:"""

        prompt = ChatPromptTemplate.from_template(template)

        def format_docs(docs: List[Document]) -> str:
            return "\n\n".join(doc.page_content for doc in docs)

        retriever = vector_store.as_retriever(search_kwargs={"k": 3})

        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        print("✓ RAG chain initialized!")
        print("API server is ready!")

    except Exception as e:
        print(f"✗ Startup error: {e}")
        import traceback

        traceback.print_exc()
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG API Server",
        "version": "1.0.0",
        "endpoints": {
            "retrieve": "POST /retrieve - Retrieve similar documents",
            "rag": "POST /rag - RAG (Retrieval + Generation)",
            "add_document": "POST /documents - Add a document",
            "add_documents": "POST /documents/batch - Add multiple documents",
            "health": "GET /health - Health check",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "vector_store": "initialized" if vector_store else "not initialized",
        "rag_chain": "initialized" if rag_chain else "not initialized",
    }


@app.post("/retrieve")
async def retrieve(request: QueryRequest):
    """
    Retrieve similar documents (검색만 수행).
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        results = vector_store.similarity_search(request.question, k=request.k)

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


@app.post("/rag")
async def rag(request: QueryRequest):
    """
    RAG (Retrieval-Augmented Generation) - 검색 + 답변 생성.
    """
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG chain not initialized")

    try:
        if not vector_store:
            raise HTTPException(status_code=500, detail="Vector store not initialized")

        print(f"[RAG] Received question: {request.question}, k={request.k}")

        # Retrieve documents
        retrieved_docs = vector_store.similarity_search(request.question, k=request.k)
        print(f"[RAG] Retrieved {len(retrieved_docs)} documents")

        # Generate answer
        print("[RAG] Generating answer...")
        answer = rag_chain.invoke(request.question)
        print(f"[RAG] Answer generated: {answer[:100]}...")

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
        print(f"[RAG] Error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents")
async def add_document(request: DocumentRequest):
    """
    Add a single document to the vector store.
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        doc = Document(
            page_content=request.content,
            metadata=request.metadata or {},
        )
        vector_store.add_documents([doc])

        return {
            "message": "Document added successfully",
            "content": request.content,
            "metadata": request.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/batch")
async def add_documents(request: DocumentListRequest):
    """
    Add multiple documents to the vector store.
    """
    if not vector_store:
        raise HTTPException(status_code=500, detail="Vector store not initialized")

    try:
        docs = [
            Document(
                page_content=doc["content"],
                metadata=doc.get("metadata", {}),
            )
            for doc in request.documents
        ]
        vector_store.add_documents(docs)

        return {
            "message": f"{len(docs)} documents added successfully",
            "count": len(docs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

