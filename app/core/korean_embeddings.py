"""한국어 임베딩 모델 초기화 및 관리."""

import os
from langchain_core.embeddings import Embeddings
from typing import List

# OpenAI 임베딩 사용 여부 (기본값: false)
USE_OPENAI_EMBEDDINGS = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"

if not USE_OPENAI_EMBEDDINGS:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        HF_EMBEDDINGS_AVAILABLE = True
    except ImportError:
        HF_EMBEDDINGS_AVAILABLE = False
        print("⚠️ langchain-community가 설치되지 않았습니다.")
else:
    HF_EMBEDDINGS_AVAILABLE = False


def init_korean_embeddings() -> Embeddings:
    """
    한국어 임베딩 모델 초기화.

    추천 모델:
    - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (다국어, 빠름)
    - BAAI/bge-small-ko-v1.5 (한국어 특화, 최신)
    - jhgan/ko-sroberta-multitask (한국어 특화)
    """
    if USE_OPENAI_EMBEDDINGS:
        from langchain_openai import OpenAIEmbeddings
        print("Using OpenAI embeddings (text-embedding-3-small)")
        return OpenAIEmbeddings(model="text-embedding-3-small")

    if not HF_EMBEDDINGS_AVAILABLE:
        raise ImportError("Hugging Face embeddings를 사용할 수 없습니다.")

    # 한국어 특화 임베딩 모델 (기본값)
    model_name = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "BAAI/bge-small-ko-v1.5"  # 한국어 특화, 경량 모델
    )

    print(f"Loading Korean embedding model: {model_name}")
    print("⏳ 임베딩 모델 로딩 중... (처음 실행 시 다운로드 시간이 걸릴 수 있습니다)")

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={
            "device": "cpu",  # GPU 사용 시 "cuda"로 변경
        },
        encode_kwargs={
            "normalize_embeddings": True,  # 벡터 정규화
        }
    )

    print("✓ Korean embedding model initialized!")
    return embeddings




