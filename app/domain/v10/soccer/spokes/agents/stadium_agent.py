"""경기장 데이터 정책 기반 에이전트."""
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch
from fastmcp import FastMCP
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

try:
    from langchain_huggingface import HuggingFacePipeline
except ImportError:
    from langchain_community.llms import HuggingFacePipeline

from app.core.llm.providers.exaone_local import create_exaone_local_llm

logger = logging.getLogger(__name__)


class StadiumAgent:
    """경기장 데이터를 정책 기반으로 처리하는 에이전트."""

    def __init__(self, model_dir: Optional[Path] = None):
        """StadiumAgent 초기화.

        Args:
            model_dir: ExaOne 모델 디렉토리 경로 (None이면 기본 경로 사용)
        """
        logger.info("[에이전트] StadiumAgent 초기화")

        # ExaOne 모델 로드
        self.exaone_llm = self._load_exaone_model(model_dir)

        # FastMCP 클라이언트 생성 및 툴 설정
        self.mcp = FastMCP(name="stadium_agent_exaone")
        self._setup_exaone_tools()

        logger.info("[에이전트] StadiumAgent 초기화 완료 (ExaOne, FastMCP)")

    def _get_default_model_dir(self) -> Path:
        """기본 ExaOne 모델 디렉토리 경로를 반환합니다.

        Returns:
            모델 디렉토리 Path
        """
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent.parent
        model_dir = project_root / "artifacts" / "base-models" / "exaone-2.4b"
        return model_dir

    def _load_exaone_model(self, model_dir: Optional[Path] = None):
        """ExaOne 모델을 로드합니다.

        Args:
            model_dir: 모델 디렉토리 경로

        Returns:
            LangChain 호환 LLM 인스턴스
        """
        if model_dir is None:
            model_dir = self._get_default_model_dir()

        if not model_dir.exists():
            logger.warning(f"[ExaOne] 모델 디렉토리를 찾을 수 없습니다: {model_dir}")
            logger.info("[ExaOne] 기본 경로에서 모델 로드 시도")
            try:
                return create_exaone_local_llm()
            except Exception as e:
                logger.error(f"[ExaOne] 모델 로드 실패: {e}", exc_info=True)
                raise

        logger.info(f"[ExaOne] 모델 로딩 중: {model_dir}")

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[ExaOne] 사용 디바이스: {device}")

            # 토크나이저 로드
            tokenizer = AutoTokenizer.from_pretrained(
                str(model_dir),
                trust_remote_code=True,
                local_files_only=True
            )

            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # 모델 로드 설정
            model_kwargs = {
                "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
                "device_map": "auto" if device == "cuda" else None,
                "trust_remote_code": True,
                "local_files_only": True
            }

            # 모델 로드
            model = AutoModelForCausalLM.from_pretrained(
                str(model_dir),
                **model_kwargs
            )

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

            logger.info("[ExaOne] 모델 로딩 완료")
            return llm

        except Exception as e:
            logger.error(f"[ExaOne] 모델 로딩 실패: {e}", exc_info=True)
            raise RuntimeError(f"ExaOne 모델 로딩 실패: {e}") from e

    def _setup_exaone_tools(self) -> None:
        """ExaOne 모델을 위한 FastMCP 툴을 설정합니다."""
        @self.mcp.tool()
        def exaone_generate_text(prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 텍스트를 생성합니다.

            Args:
                prompt: 생성할 텍스트의 프롬프트
                max_tokens: 최대 생성 토큰 수

            Returns:
                생성 결과 딕셔너리
            """
            try:
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                response = self.exaone_llm.invoke(formatted_prompt)

                # 응답에서 프롬프트 부분 제거
                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info(f"[ExaOne 툴] 텍스트 생성 완료: {len(response)}자")
                return {
                    "success": True,
                    "generated_text": response,
                    "prompt": prompt,
                    "length": len(response)
                }
            except Exception as e:
                logger.error(f"[ExaOne 툴] 텍스트 생성 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_analyze_stadium_data(stadium_data: Dict[str, Any]) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 경기장 데이터를 분석합니다.

            Args:
                stadium_data: 분석할 경기장 데이터 딕셔너리

            Returns:
                분석 결과 딕셔너리
            """
            try:
                # 경기장 데이터를 텍스트로 변환
                data_text = json.dumps(stadium_data, ensure_ascii=False, indent=2)
                prompt = f"다음 경기장 데이터를 분석하고 주요 특징을 요약해주세요:\n\n{data_text}"

                # ExaOne 모델 직접 호출
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                response = self.exaone_llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info("[ExaOne 툴] 경기장 데이터 분석 완료")
                return {
                    "success": True,
                    "analysis": response,
                    "stadium_data": stadium_data
                }
            except Exception as e:
                logger.error(f"[ExaOne 툴] 경기장 데이터 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        self._setup_filesystem_tools()
        logger.info("[FastMCP] ExaOne 툴 설정 완료")

    def _setup_filesystem_tools(self) -> None:
        """os와 pathlib 라이브러리를 사용한 파일 시스템 툴을 설정합니다."""
        # 프로젝트 루트 경로 설정 (보안을 위해 제한)
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent

        @self.mcp.tool()
        def path_exists(path: str) -> Dict[str, Any]:
            """경로가 존재하는지 확인합니다.

            Args:
                path: 확인할 경로 (상대 경로는 프로젝트 루트 기준)

            Returns:
                존재 여부 결과 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                exists = path_obj.exists()
                is_file = path_obj.is_file() if exists else False
                is_dir = path_obj.is_dir() if exists else False

                return {
                    "success": True,
                    "path": str(path_obj),
                    "exists": exists,
                    "is_file": is_file,
                    "is_dir": is_dir
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 경로 확인 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def list_directory(path: str = ".") -> Dict[str, Any]:
            """디렉토리 내용을 나열합니다.

            Args:
                path: 나열할 디렉토리 경로 (기본값: 현재 디렉토리)

            Returns:
                디렉토리 내용 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": False,
                        "error": "경로가 존재하지 않습니다"
                    }

                if not path_obj.is_dir():
                    return {
                        "success": False,
                        "error": "디렉토리가 아닙니다"
                    }

                items = []
                for item in path_obj.iterdir():
                    items.append({
                        "name": item.name,
                        "is_file": item.is_file(),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None
                    })

                return {
                    "success": True,
                    "path": str(path_obj),
                    "items": sorted(items, key=lambda x: (not x["is_dir"], x["name"])),
                    "count": len(items)
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 디렉토리 나열 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
            """파일 내용을 읽습니다.

            Args:
                file_path: 읽을 파일 경로
                encoding: 파일 인코딩 (기본값: utf-8)

            Returns:
                파일 내용 딕셔너리
            """
            try:
                path_obj = Path(file_path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": False,
                        "error": "파일이 존재하지 않습니다"
                    }

                if not path_obj.is_file():
                    return {
                        "success": False,
                        "error": "파일이 아닙니다"
                    }

                # 파일 크기 제한 (10MB)
                file_size = path_obj.stat().st_size
                if file_size > 10 * 1024 * 1024:
                    return {
                        "success": False,
                        "error": "파일이 너무 큽니다 (10MB 제한)"
                    }

                content = path_obj.read_text(encoding=encoding)

                return {
                    "success": True,
                    "path": str(path_obj),
                    "content": content,
                    "size": file_size,
                    "encoding": encoding
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 파일 읽기 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_path_info(path: str) -> Dict[str, Any]:
            """경로의 상세 정보를 조회합니다.

            Args:
                path: 조회할 경로

            Returns:
                경로 정보 딕셔너리
            """
            try:
                path_obj = Path(path)
                if not path_obj.is_absolute():
                    path_obj = project_root / path_obj

                # 보안: 프로젝트 루트 밖으로 나가는 것 방지
                try:
                    path_obj.resolve().relative_to(project_root.resolve())
                except ValueError:
                    return {
                        "success": False,
                        "error": "프로젝트 루트 밖의 경로는 접근할 수 없습니다"
                    }

                if not path_obj.exists():
                    return {
                        "success": True,
                        "path": str(path_obj),
                        "exists": False,
                        "absolute_path": str(path_obj.resolve())
                    }

                stat_info = path_obj.stat()

                return {
                    "success": True,
                    "path": str(path_obj),
                    "absolute_path": str(path_obj.resolve()),
                    "exists": True,
                    "is_file": path_obj.is_file(),
                    "is_dir": path_obj.is_dir(),
                    "size": stat_info.st_size if path_obj.is_file() else None,
                    "created": stat_info.st_ctime,
                    "modified": stat_info.st_mtime,
                    "parent": str(path_obj.parent),
                    "name": path_obj.name,
                    "stem": path_obj.stem,
                    "suffix": path_obj.suffix
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 경로 정보 조회 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def join_paths(*paths: str) -> Dict[str, Any]:
            """여러 경로를 결합합니다.

            Args:
                *paths: 결합할 경로들

            Returns:
                결합된 경로 딕셔너리
            """
            try:
                combined = Path(*paths)
                return {
                    "success": True,
                    "combined_path": str(combined),
                    "parts": list(combined.parts)
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 경로 결합 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_environment_variable(name: str, default: Optional[str] = None) -> Dict[str, Any]:
            """환경 변수를 읽습니다.

            Args:
                name: 환경 변수 이름
                default: 기본값 (환경 변수가 없을 때)

            Returns:
                환경 변수 값 딕셔너리
            """
            try:
                value = os.getenv(name, default)
                return {
                    "success": True,
                    "name": name,
                    "value": value,
                    "exists": name in os.environ
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 환경 변수 읽기 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def get_current_directory() -> Dict[str, Any]:
            """현재 작업 디렉토리를 반환합니다.

            Returns:
                현재 디렉토리 정보 딕셔너리
            """
            try:
                cwd = Path.cwd()
                return {
                    "success": True,
                    "current_directory": str(cwd),
                    "absolute_path": str(cwd.resolve())
                }
            except Exception as e:
                logger.error(f"[파일시스템 툴] 현재 디렉토리 조회 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        logger.info("[FastMCP] 파일시스템 툴 설정 완료 (os, pathlib)")

    async def process_stadiums(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """경기장 데이터를 정책 기반으로 처리합니다.

        Args:
            items: 처리할 경기장 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[에이전트] 정책 기반 처리 시작: {len(items)}개 항목")

        # TODO: 정책 기반 처리 로직 구현
        # 예: LLM을 사용한 데이터 검증, 변환, 보강 등

        processed_items = []
        for item in items:
            # 정책 기반 처리 예시
            processed_item = {
                **item,
                "processed_by": "policy_agent",
                "policy_applied": True,
            }
            processed_items.append(processed_item)

        result = {
            "success": True,
            "method": "policy_based",
            "processed_count": len(processed_items),
            "items": processed_items,
        }

        logger.info(f"[에이전트] 정책 기반 처리 완료: {len(processed_items)}개 항목")
        return result

