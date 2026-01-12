"""Midm-2.0-Mini-Instruct 로컬 모델 provider.

K-intelligence/Midm-2.0-Mini-Instruct 모델을 로컬에서 로드하여
LangChain 호환 LLM 인스턴스를 생성합니다.
"""

from pathlib import Path
from typing import Optional

from app.core.llm.base import LLMType


def create_midm_local_llm(model_dir: Optional[str] = None) -> LLMType:
    """Midm-2.0-Mini-Instruct 로컬 모델을 로드합니다.

    Args:
        model_dir: 모델 디렉터리 경로. None이면 기본 경로 사용.

    Returns:
        LLMType: LangChain 호환 LLM 인스턴스.

    Raises:
        ImportError: 필요한 패키지가 설치되지 않은 경우.
        FileNotFoundError: 모델 파일을 찾을 수 없는 경우.
    """
    try:
        from langchain_community.llms import HuggingFacePipeline
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch
    except ImportError as e:
        raise ImportError(
            f"Midm 모델 사용을 위해 필요한 패키지가 설치되지 않았습니다: {e}\n"
            "pip install transformers torch langchain-community 를 실행하세요."
        )

    # 기본 모델 경로 설정
    if model_dir is None:
        model_dir = Path(__file__).parent.parent.parent.parent / "model" / "midm"
    else:
        model_dir = Path(model_dir)

    if not model_dir.exists():
        raise FileNotFoundError(f"Midm 모델 디렉터리를 찾을 수 없습니다: {model_dir}")

    print(f"[AI] Midm-2.0-Mini-Instruct 모델 로딩 중: {model_dir}")

    # GPU 사용 가능 여부 확인
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[디바이스] 사용 디바이스: {device}")

    try:
        # 토크나이저 로드
        print("[로딩] 토크나이저 로딩 중...")
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))

        # 모델 로드 (Midm 모델 특성에 맞게 설정)
        print("[로딩] 모델 로딩 중...")
        model = AutoModelForCausalLM.from_pretrained(
            str(model_dir),
            torch_dtype="auto",  # 자동 dtype 선택
            device_map="auto",   # 자동 디바이스 매핑
            trust_remote_code=True,  # Midm 모델 필수 옵션
        )

        # 파이프라인 생성 (Midm 모델에 최적화된 설정)
        print("[설정] 파이프라인 생성 중...")
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id,  # 패딩 토큰 설정
        )

        # LangChain 래퍼로 변환
        llm = HuggingFacePipeline(pipeline=pipe)

        print("[완료] Midm-2.0-Mini-Instruct 모델 로딩 완료!")
        return llm

    except Exception as e:
        print(f"[오류] Midm 모델 로딩 중 오류 발생: {e}")
        raise


def create_midm_instruct_llm(model_dir: Optional[str] = None) -> LLMType:
    """Midm-2.0-Mini-Instruct 모델을 Instruct 형태로 로드합니다.

    이 함수는 create_midm_local_llm의 별칭으로, 명확성을 위해 제공됩니다.
    """
    return create_midm_local_llm(model_dir)
