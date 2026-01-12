"""한국어 Llama 모델 초기화 및 관리."""

import os
from typing import Optional, Union
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser

# Ollama 사용 여부 확인
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "false").lower() == "true"

if USE_OLLAMA:
    try:
        from langchain_ollama import OllamaLLM, ChatOllama
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False
        print("⚠️ langchain-ollama가 설치되지 않았습니다. pip install langchain-ollama 실행하세요.")
else:
    OLLAMA_AVAILABLE = False

if USE_HUGGINGFACE:
    try:
        from langchain_community.llms import HuggingFacePipeline
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            pipeline,
            BitsAndBytesConfig
        )
        import torch
        HF_AVAILABLE = True
    except ImportError:
        HF_AVAILABLE = False
        print("⚠️ transformers가 설치되지 않았습니다. pip install transformers torch 실행하세요.")
else:
    HF_AVAILABLE = False


def init_ollama_llm() -> BaseLanguageModel:
    """Ollama를 사용하여 한국어 LLM 초기화."""
    if not OLLAMA_AVAILABLE:
        raise ImportError("langchain-ollama가 설치되지 않았습니다.")

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama2")

    print(f"Using Ollama LLM: {ollama_model} at {ollama_base_url}")

    llm = ChatOllama(
        model=ollama_model,
        base_url=ollama_base_url,
        temperature=0.7,
    )

    print("✓ Ollama LLM initialized!")
    return llm


def init_huggingface_llm() -> BaseLanguageModel:
    """Hugging Face Transformers를 사용하여 한국어 LLM 초기화."""
    if not HF_AVAILABLE:
        raise ImportError("transformers가 설치되지 않았습니다.")

    model_name = os.getenv(
        "HF_MODEL_NAME",
        "nousresearch/polyglot-ko-3.8b"  # 기본값: Polyglot-Ko 3.8B
    )

    device_map = "auto"
    if torch.cuda.is_available():
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ GPU를 사용할 수 없습니다. CPU 모드로 실행됩니다 (느릴 수 있습니다).")
        device_map = "cpu"

    print(f"Loading Hugging Face model: {model_name}")
    print("⏳ 모델 로딩 중... (처음 실행 시 다운로드 시간이 걸릴 수 있습니다)")

    # 양자화 설정 (메모리 절약)
    use_quantization = os.getenv("USE_QUANTIZATION", "true").lower() == "true"

    if use_quantization and torch.cuda.is_available():
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
    else:
        quantization_config = None

    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # 모델 로드
    if quantization_config:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map=device_map,
            torch_dtype=torch.float16,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map=device_map,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )

    # 파이프라인 생성
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
        return_full_text=False,
    )

    # LangChain 래퍼
    llm = HuggingFacePipeline(pipeline=pipe)

    print("✓ Hugging Face LLM initialized!")
    return llm


def init_korean_llm() -> BaseLanguageModel:
    """
    한국어 LLM 초기화.
    환경 변수에 따라 Ollama 또는 Hugging Face 사용.
    """
    if USE_OLLAMA:
        return init_ollama_llm()
    elif USE_HUGGINGFACE:
        return init_huggingface_llm()
    else:
        raise ValueError(
            "한국어 LLM을 사용하려면 환경 변수를 설정하세요:\n"
            "- USE_OLLAMA=true (Ollama 사용)\n"
            "- USE_HUGGINGFACE=true (Hugging Face 사용)"
        )




