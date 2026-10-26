import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.load_resilience import rate_limiter, circuit_breaker

client = TestClient(app)

def run_sre_load_resilience_test():
    print("==================================================")
    print("▶ [SRE Load Stress] 대규모 스파이크 트래픽 부하 및 서킷 브레이커 검증")
    print("==================================================")

    # 1. 토큰 발급
    token_resp = client.post("/api/v1/oauth/token", json={
        "client_id": "test_partner_id",
        "client_secret": "test_partner_secret"
    })
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 제휴사 Rate Limiter 용량 초과 스파이크 부하 테스트 (150건 고속 연속 호출)
    TOTAL_CALLS = 150
    print(f"🔥 {TOTAL_CALLS}건의 본인확인 요청을 마이크로초 단위로 고속 폭풍 호출 (Burst Throttling 시뮬레이션)...")

    results = []
    def burst_request(idx):
        resp = client.post("/api/v1/identity/request", headers=headers, json={
            "user_name": f"부하테스터_{idx}",
            "user_phone": "010-0000-0000",
            "user_birth": "19900101",
            "request_reason": "부하 스트레스"
        })
        return resp.status_code

    with ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(burst_request, range(TOTAL_CALLS)))

    success_count = sum(1 for code in results if code == 200)
    throttled_count = sum(1 for code in results if code == 429)

    print("--------------------------------------------------")
    print(f"📊 Rate Limiting (Token Bucket) 결과 분석:")
    print(f" - 허용된 정상 처리 (200 OK): {success_count}건")
    print(f" - 폭주 차단 Throttling (429 Too Many Requests): {throttled_count}건")
    print("--------------------------------------------------")

    assert success_count > 0, "정상 처리가 1건도 없음"
    assert throttled_count > 0, "폭주 호출이 Throttling 차단되지 않음"
    print("✅ [성공] Token Bucket 알고리즘에 의해 트래픽 스파이크 DoS 차단 완료!")

    # 3. 서킷 브레이커 (Circuit Breaker) 장애 차단 테스트
    print("\n🔥 외부 통신망 장애 모의 주입 (서킷 브레이커 OPEN 트리거)...")
    for _ in range(circuit_breaker.failure_threshold):
        circuit_breaker.record_failure()

    assert circuit_breaker.state == "OPEN", "서킷 브레이커가 OPEN 상태로 전이되지 않음"
    print(f"⚡ 서킷 브레이커 상태: {circuit_breaker.state} (외부 통신망 차단 활성화)")

    # 서킷 OPEN 시 API 호출 시도 -> 503 Service Unavailable 즉시 격리 반환
    cb_resp = client.post("/api/v1/identity/request", headers=headers, json={
        "user_name": "장애격리테스터",
        "user_phone": "010-0000-0000",
        "user_birth": "19900101"
    })
    assert cb_resp.status_code == 503
    assert cb_resp.json()["detail"]["error_code"] == "CIRCUIT_BREAKER_OPEN"
    print("✅ [성공] Cascade Failure 방지를 위한 503 Fast-Fail 서킷 브레이커 동작 확인!")

    # 서킷 브레이커 정상 복구 시뮬레이션
    circuit_breaker.record_success()
    print("✅ 서킷 브레이커 CLOSED 정상 상태로 복구 완료.")

    print("\n🎉 서비스 부하 대응 & 고가용성 SRE 엔지니어링 검증을 100% 무결점으로 통과했습니다!")

if __name__ == "__main__":
    run_sre_load_resilience_test()
