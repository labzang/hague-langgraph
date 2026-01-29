"""EXAONE-2.4B 로컬 모델 provider.

LG AI Research의 EXAONE-2.4B 모델을 로컬에서 로드하여
LangChain 호환 LLM 인스턴스를 생성합니다.
"""

from pathlib import Path
from typing import Optional

from app.core.llm.base import LLMType


def create_exaone_local_llm(model_dir: Optional[str] = None) -> LLMType:
    """EXAONE-2.4B 로컬 모델을 로드합니다.

    Args:
        model_dir: 모델 디렉터리 경로. None이면 기본 경로 사용.

    Returns:
        LLMType: LangChain 호환 LLM 인스턴스.

    Raises:
        ImportError: 필요한 패키지가 설치되지 않은 경우.
        FileNotFoundError: 모델 파일을 찾을 수 없는 경우.
    """
    try:
        # 새로운 langchain-huggingface 패키지 사용 시도
        try:
            from langchain_huggingface import HuggingFacePipeline
        except ImportError:
            # 백업으로 기존 패키지 사용
            from langchain_community.llms import HuggingFacePipeline

        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch
    except ImportError as e:
        raise ImportError(
            f"EXAONE 모델 사용을 위해 필요한 패키지가 설치되지 않았습니다: {e}\n"
            "pip install transformers torch langchain-community 를 실행하세요."
        )

    # 기본 모델 경로 설정
    if model_dir is None:
        model_dir = Path(__file__).parent.parent.parent.parent.parent / "artifacts" / "base-models" / "exaone-2.4b"
    else:
        model_dir = Path(model_dir)

    if not model_dir.exists():
        raise FileNotFoundError(f"EXAONE 모델 디렉터리를 찾을 수 없습니다: {model_dir}")

    print(f"[AI] EXAONE-2.4B 모델 로딩 중: {model_dir}")

    # GPU 사용 가능 여부 확인
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[디바이스] 사용 디바이스: {device}")

    try:
        # 토크나이저 로드
        print("[로딩] 토크나이저 로딩 중...")
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            trust_remote_code=True,
            local_files_only=True
        )

        # 패딩 토큰 설정
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        print("[로딩] EXAONE 모델 로딩 중...")

        # 모델 로드 설정
        model_kwargs = {
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
            "device_map": "auto" if device == "cuda" else None,
            "trust_remote_code": True,
            "local_files_only": True
        }

        # 메모리가 부족한 경우를 대비한 양자화 설정
        if device == "cuda":
            try:
                from transformers import BitsAndBytesConfig

                # 4bit 양자화 설정 (메모리 절약)
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                model_kwargs["quantization_config"] = quantization_config
                print("[설정] 4bit 양자화 활성화")
            except ImportError:
                print("[경고] BitsAndBytesConfig를 사용할 수 없습니다. 일반 모드로 로드합니다.")

        # 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            str(model_dir),
            **model_kwargs
        )

        print("[설정] 텍스트 생성 파이프라인 생성 중...")

        # 텍스트 생성 파이프라인 생성
        text_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            device=0 if device == "cuda" else -1,
        )

        # LangChain HuggingFacePipeline로 래핑
        llm = HuggingFacePipeline(
            pipeline=text_pipeline,
            model_kwargs={
                "temperature": 0.7,
                "max_new_tokens": 512,
                "do_sample": True,
                "top_p": 0.9,
            }
        )

        print("[완료] EXAONE-2.4B 모델 로딩 완료!")
        return llm

    except Exception as e:
        print(f"[오류] EXAONE 모델 로딩 실패: {e}")
        raise


class ExaoneLocalLLM:
    """EXAONE 모델을 위한 간단한 래퍼 클래스"""

    def __init__(self, model_dir: Optional[str] = None):
        self.llm = create_exaone_local_llm(model_dir)

    def invoke(self, prompt: str) -> str:
        """프롬프트를 받아 응답을 생성합니다."""
        try:
            # EXAONE 모델용 프롬프트 포맷팅
            formatted_prompt = f"[질문] {prompt}\n[답변] "

            response = self.llm.invoke(formatted_prompt)

            # 응답에서 프롬프트 부분 제거
            if "[답변]" in response:
                response = response.split("[답변]")[-1].strip()

            return response
        except Exception as e:
            print(f"[오류] EXAONE 모델 응답 생성 실패: {e}")
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {e}"
