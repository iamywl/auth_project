import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app, audit_logger

client = TestClient(app)

def run_concurrency_stress_test():
    print("==================================================")
    print("▶ [QA Stress Test] 대규모 동시성 & 레이스 컨디션 극한 검증")
    print("==================================================")

    # 1. 토큰 발급
    token_resp = client.post("/api/v1/oauth/token", json={
        "client_id": "test_partner_id",
        "client_secret": "test_partner_secret"
    })
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 본인확인 요청 생성 및 앱 승인
    req_resp = client.post("/api/v1/identity/request", headers=headers, json={
        "user_name": "QA테스터",
        "user_phone": "010-7777-8888",
        "user_birth": "19991231",
        "request_reason": "동시성 스트레스 테스트"
    })
    tx_id = req_resp.json()["tx_id"]
    client.post("/api/v1/identity/complete", json={"tx_id": tx_id})
    print(f"✅ 테스트 대상 트랜잭션 준비 완료 (tx_id: {tx_id}, 상태: COMPLETED)")

    # 3. 50개 스레드가 마이크로초 단위로 동일한 tx_id에 대해 동시 /verify 호출!
    CONCURRENT_WORKERS = 50
    results = []
    print(f"🔥 {CONCURRENT_WORKERS}개 스레드가 동시에 /api/v1/identity/verify 호출 시작 (Double-Spend 공격 시뮬레이션)...")

    def call_verify():
        resp = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
        return resp.status_code, resp.json()

    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(call_verify) for _ in range(CONCURRENT_WORKERS)]
        for f in futures:
            results.append(f.result())

    # 4. 결과 분석
    success_count = sum(1 for status_code, _ in results if status_code == 200)
    blocked_count = sum(1 for status_code, body in results if status_code == 400 and body.get("detail", {}).get("error_code") == "AUTH_4009_ALREADY_VERIFIED")

    print("--------------------------------------------------")
    print(f"📊 동시 호출 검증 결과:")
    print(f" - 성공 건수 (200 OK): {success_count}건 (기대치: 정확히 1건)")
    print(f" - 방어 차단 건수 (400 AUTH_4009): {blocked_count}건 (기대치: {CONCURRENT_WORKERS - 1}건)")
    print("--------------------------------------------------")

    assert success_count == 1, f"레이스 컨디션 발생! 성공 건수가 1이 아님: {success_count}"
    assert blocked_count == CONCURRENT_WORKERS - 1, f"방어 누수 발생! 차단 건수 불일치: {blocked_count}"
    print("✅ [성공] Redis 분산 락 및 원자적 상태 머신에 의해 100% 레이스 컨디션 방어 완료!")

    # 5. 감사로그 동시 쓰기(100건 동시 발생) 무결성 테스트
    print("\n🔥 100건 동시 비동기 감사로그 기록 스트레스 테스트 진행...")
    def log_concurrent(idx):
        audit_logger.log(
            action=f"CONCURRENT_STRESS_LOG_{idx}",
            client_id="test_partner_id",
            tx_id=f"tx_stress_{idx}",
            payload_summary={"idx": idx}
        )

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(log_concurrent, range(100)))

    # 6. 해시 체인 무결성 전수 검증
    integrity = audit_logger.verify_integrity()
    assert integrity["is_valid"] is True, f"해시체인 파손 발생: {integrity}"
    print(f"✅ [성공] 동시 쓰기 100건 이후 Hash-Chain 전수 검사 통과 (총 {integrity['total_records']}건 100% 무결성 유지)")

    print("\n🎉 QA 대규모 동시성 & 스트레스 부하 검증을 무결점(Zero-Defect)으로 통과했습니다!")

if __name__ == "__main__":
    run_concurrency_stress_test()
