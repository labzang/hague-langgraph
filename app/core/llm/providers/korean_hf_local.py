"""로컬 Hugging Face 한국어 LLM provider 스켈레톤.

실제 로컬 모델 디렉터리(예: `model.safetensors`, `config.json` 등)가
있는 경로를 받아 해당 모델을 로드하는 역할을 합니다.

현재는 아키텍처 목적의 스켈레톤만 제공하며, 구체적인 로딩 로직은
사용자가 직접 구현하도록 남겨둡니다.
"""

from pathlib import Path

from app.core.llm.base import LLMType


def create_local_korean_llm(model_dir: str | Path) -> LLMType:
    """로컬 Hugging Face 한국어 LLM 인스턴스를 생성합니다.

    model_dir에는 다음 파일들이 있어야 합니다:
    - model.safetensors (또는 pytorch_model.bin)
    - config.json
    - tokenizer.json
    - tokenizer_config.json

    Args:
        model_dir: 로컬 모델 파일이 위치한 디렉터리 경로.

    Returns:
        LLMType: LangChain 호환 LLM 인스턴스.
    """
    try:
        from langchain_community.llms import HuggingFacePipeline
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            pipeline,
            BitsAndBytesConfig
        )
        import torch
    except ImportError as e:
        raise ImportError(
            f"로컬 HF 모델 사용을 위해 필요한 패키지가 설치되지 않았습니다: {e}\n"
            "pip install transformers torch langchain-community 를 실행하세요."
        )

    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"모델 디렉터리를 찾을 수 없습니다: {model_path}")

    print(f"🔧 로컬 한국어 모델 로딩 중: {model_path}")

    # GPU 사용 가능 여부 확인
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🖥️ 사용 디바이스: {device}")

    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))

    # 모델 로드 (메모리 효율성을 위해 양자화 옵션 고려)
    model_kwargs = {"torch_dtype": torch.float16 if device == "cuda" else torch.float32}

    if device == "cuda":
        # GPU에서는 4bit 양자화 사용 (메모리 절약)
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        model_kwargs["quantization_config"] = quantization_config
        model_kwargs["device_map"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(str(model_path), **model_kwargs)

    # 파이프라인 생성
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
        return_full_text=False,
        device=0 if device == "cuda" else -1,
    )

    # LangChain 래퍼로 변환
    llm = HuggingFacePipeline(pipeline=pipe)

    print("✅ 로컬 한국어 모델 로딩 완료!")
    return llm
