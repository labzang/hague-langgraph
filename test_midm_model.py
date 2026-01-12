#!/usr/bin/env python3
"""Midm 모델 로딩 테스트 스크립트.

이 스크립트는 Midm-2.0-Mini-Instruct 모델이 올바르게 로드되는지
테스트하기 위한 독립적인 스크립트입니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_midm_model():
    """Midm 모델 로딩 테스트."""
    try:
        print("🧪 Midm-2.0-Mini-Instruct 모델 로딩 테스트 시작...")

        from app.core.llm.providers.midm_local import create_midm_local_llm

        # 모델 로드
        llm = create_midm_local_llm()

        # 간단한 텍스트 생성 테스트
        print("\n📝 텍스트 생성 테스트:")
        test_prompt = "안녕하세요. 저는"

        response = llm.invoke(test_prompt)
        print(f"입력: {test_prompt}")
        print(f"출력: {response}")

        print("\n✅ Midm 모델 테스트 완료!")
        return True

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_factory_integration():
    """팩토리 함수를 통한 통합 테스트."""
    try:
        print("\n🏭 팩토리 함수 통합 테스트 시작...")

        # 환경 변수 임시 설정
        os.environ["LLM_PROVIDER"] = "midm"

        from app.config import Settings
        from app.core.llm.factory import create_llm_from_config

        settings = Settings()
        llm = create_llm_from_config(settings)

        if llm:
            print("✅ 팩토리 함수를 통한 모델 생성 성공!")

            # 간단한 테스트
            response = llm.invoke("한국어로 인사해주세요.")
            print(f"응답: {response}")

            return True
        else:
            print("❌ 팩토리 함수에서 None 반환")
            return False

    except Exception as e:
        print(f"❌ 팩토리 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Midm 모델 테스트 시작\n")

    # 모델 디렉터리 확인
    model_dir = project_root / "app" / "model" / "midm"
    if not model_dir.exists():
        print(f"❌ 모델 디렉터리가 존재하지 않습니다: {model_dir}")
        sys.exit(1)

    print(f"📁 모델 디렉터리: {model_dir}")
    print(f"📋 모델 파일들:")
    for file in sorted(model_dir.iterdir()):
        print(f"   - {file.name}")

    print("\n" + "="*50)

    # 테스트 실행
    test1_success = test_midm_model()
    test2_success = test_factory_integration()

    print("\n" + "="*50)
    print("📊 테스트 결과:")
    print(f"   직접 로딩: {'✅ 성공' if test1_success else '❌ 실패'}")
    print(f"   팩토리 통합: {'✅ 성공' if test2_success else '❌ 실패'}")

    if test1_success and test2_success:
        print("\n🎉 모든 테스트 통과! Midm 모델이 정상적으로 설정되었습니다.")
        sys.exit(0)
    else:
        print("\n💥 일부 테스트 실패. 설정을 확인해주세요.")
        sys.exit(1)
