"""
KoELECTRA 게이트웨이 시스템 테스트 스크립트
"""

import asyncio
import json
import requests
from typing import Dict, Any

# 테스트 설정
BASE_URL = "http://localhost:8000"
MCP_ENDPOINT = f"{BASE_URL}/mcp"

# 테스트 이메일 데이터
TEST_EMAILS = [
    {
        "name": "정상 이메일 - 업무 관련",
        "email": {
            "subject": "회의 일정 변경 안내",
            "content": "안녕하세요. 내일 예정된 팀 회의가 오후 3시로 변경되었습니다. 참고 부탁드립니다.",
            "sender": "team@company.com",
            "metadata": {"type": "business"}
        }
    },
    {
        "name": "의심스러운 이메일 - 중간 신뢰도",
        "email": {
            "subject": "계정 확인 필요",
            "content": "보안상 문제로 계정 확인이 필요합니다. 아래 링크를 클릭하여 확인해주세요.",
            "sender": "security@unknown.com",
            "metadata": {"type": "security"}
        }
    },
    {
        "name": "명백한 스팸 - 고신뢰도",
        "email": {
            "subject": "긴급! 1억원 당첨! 지금 클릭!",
            "content": "축하합니다! 복권에 당첨되었습니다. 즉시 개인정보와 계좌번호를 보내주세요. 수수료 50만원만 먼저 송금하면 1억원을 드립니다!",
            "sender": "winner@fake-lottery.com",
            "metadata": {"type": "lottery_scam"}
        }
    },
    {
        "name": "정상 이메일 - 주문 확인",
        "email": {
            "subject": "주문 확인: 도서 구매",
            "content": "주문해주신 '파이썬 프로그래밍' 도서가 정상적으로 주문 처리되었습니다. 배송은 2-3일 소요됩니다.",
            "sender": "order@bookstore.co.kr",
            "metadata": {"type": "order_confirmation"}
        }
    }
]

async def test_health_check():
    """헬스 체크 테스트"""
    print("=== 헬스 체크 테스트 ===")
    try:
        response = requests.get(f"{MCP_ENDPOINT}/health")
        if response.status_code == 200:
            result = response.json()
            print("✅ 헬스 체크 성공")
            print(f"   상태: {result.get('status')}")
            print(f"   서비스: {result.get('services')}")
            return True
        else:
            print(f"❌ 헬스 체크 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 헬스 체크 오류: {e}")
        return False

async def test_gateway_info():
    """게이트웨이 정보 테스트"""
    print("\n=== 게이트웨이 정보 테스트 ===")
    try:
        response = requests.get(f"{MCP_ENDPOINT}/gateway-info")
        if response.status_code == 200:
            result = response.json()
            print("✅ 게이트웨이 정보 조회 성공")
            print(f"   게이트웨이 타입: {result.get('gateway_type')}")
            print(f"   컴포넌트: {list(result.get('components', {}).keys())}")
            print(f"   플로우: {' → '.join(result.get('processing_flow', []))}")
            return True
        else:
            print(f"❌ 게이트웨이 정보 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 게이트웨이 정보 오류: {e}")
        return False

async def test_stats():
    """통계 정보 테스트"""
    print("\n=== 통계 정보 테스트 ===")
    try:
        response = requests.get(f"{MCP_ENDPOINT}/stats")
        if response.status_code == 200:
            result = response.json()
            print("✅ 통계 조회 성공")
            print(f"   총 세션: {result.get('total_sessions', 0)}개")
            print(f"   상태 분포: {result.get('status_distribution', {})}")
            print(f"   라우팅 분포: {result.get('routing_distribution', {})}")
            print(f"   평균 처리시간: {result.get('average_processing_time', 'N/A')}")
            return True
        else:
            print(f"❌ 통계 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 통계 조회 오류: {e}")
        return False

async def test_email_analysis(email_data: Dict[str, Any], test_name: str):
    """이메일 분석 테스트"""
    print(f"\n=== {test_name} ===")
    try:
        response = requests.post(
            f"{MCP_ENDPOINT}/analyze-email",
            json=email_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ 이메일 분석 성공")
            print(f"   제목: {email_data['subject'][:50]}...")
            print(f"   최종 판정: {'🚨 스팸' if result['is_spam'] else '✅ 정상'}")
            print(f"   신뢰도: {result['confidence']:.3f}")
            print(f"   KoELECTRA 결과: {result['koelectra_decision']}")
            print(f"   처리 경로: {result['processing_path']}")
            print(f"   세션 ID: {result['metadata'].get('session_id', 'N/A')}")
            print(f"   라우팅 결정: {result['metadata'].get('routing_decision', 'N/A')}")

            if result.get('exaone_analysis'):
                print(f"   판독 에이전트 분석: {result['exaone_analysis'][:100]}...")
            else:
                print("   판독 에이전트: 호출되지 않음 (고신뢰도 판정)")

            return result
        else:
            print(f"❌ 이메일 분석 실패: {response.status_code}")
            if response.text:
                print(f"   오류 내용: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 이메일 분석 오류: {e}")
        return None

async def run_performance_test():
    """성능 테스트"""
    print("\n=== 성능 테스트 ===")

    # 간단한 이메일로 여러 번 요청
    test_email = {
        "subject": "테스트 이메일",
        "content": "성능 테스트용 이메일입니다."
    }

    import time

    num_requests = 5
    start_time = time.time()

    success_count = 0
    for i in range(num_requests):
        try:
            response = requests.post(
                f"{MCP_ENDPOINT}/analyze-email",
                json=test_email,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            print(f"   요청 {i+1} 실패: {e}")

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_requests

    print(f"✅ 성능 테스트 완료")
    print(f"   총 요청: {num_requests}개")
    print(f"   성공: {success_count}개")
    print(f"   총 시간: {total_time:.2f}초")
    print(f"   평균 응답시간: {avg_time:.2f}초")
    print(f"   성공률: {success_count/num_requests*100:.1f}%")

async def main():
    """메인 테스트 함수"""
    print("🚀 KoELECTRA 게이트웨이 시스템 테스트 시작")
    print("=" * 60)

    # 1. 헬스 체크
    health_ok = await test_health_check()
    if not health_ok:
        print("❌ 헬스 체크 실패. 서버가 실행 중인지 확인하세요.")
        return

    # 2. 게이트웨이 정보
    await test_gateway_info()

    # 3. 초기 통계
    await test_stats()

    # 4. 이메일 분석 테스트
    results = []
    for test_case in TEST_EMAILS:
        result = await test_email_analysis(
            test_case["email"],
            test_case["name"]
        )
        if result:
            results.append({
                "name": test_case["name"],
                "result": result
            })

    # 5. 성능 테스트
    await run_performance_test()

    # 6. 최종 통계
    await test_stats()

    # 7. 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    spam_count = sum(1 for r in results if r["result"]["is_spam"])
    normal_count = len(results) - spam_count

    print(f"총 테스트: {len(results)}개")
    print(f"스팸 판정: {spam_count}개")
    print(f"정상 판정: {normal_count}개")

    print("\n상세 결과:")
    for r in results:
        status = "🚨 스팸" if r["result"]["is_spam"] else "✅ 정상"
        confidence = r["result"]["confidence"]
        print(f"  {r['name']}: {status} (신뢰도: {confidence:.3f})")

    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    print("KoELECTRA + EXAONE 멀티 에이전트 시스템 테스트")
    print("서버가 http://localhost:8000 에서 실행 중이어야 합니다.")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
