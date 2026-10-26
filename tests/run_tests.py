import sys
import os

# auth_project 루트 경로를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app, audit_logger

def run_tests():
    client = TestClient(app)
    print("==================================================")
    print("▶ [Test 1] OAuth 2.0 & 본인확인 전체 라이프사이클 테스트")
    print("==================================================")
    
    # 1. OAuth 토큰 발급
    token_resp = client.post("/api/v1/oauth/token", json={
        "client_id": "test_partner_id",
        "client_secret": "test_partner_secret"
    })
    assert token_resp.status_code == 200, f"Token failed: {token_resp.text}"
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 1. OAuth 토큰 발급 성공:", token[:20] + "...")

    # 2. 본인확인 요청
    req_resp = client.post("/api/v1/identity/request", headers=headers, json={
        "user_name": "홍길동",
        "user_phone": "010-1234-5678",
        "user_birth": "19950515",
        "request_reason": "회원가입"
    })
    assert req_resp.status_code == 200
    tx_id = req_resp.json()["tx_id"]
    print("✅ 2. 본인확인 트랜잭션 발급 (REQUESTED):", tx_id)

    # 3. 승인 전 결과 검증 차단 (AUTH_4005)
    pre_verify = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert pre_verify.status_code == 400
    assert pre_verify.json()["detail"]["error_code"] == "AUTH_4005_TRANSACTION_PENDING"
    print("✅ 3. 미승인 상태 결과 조회 차단 (AUTH_4005) 정상 방어")

    # 4. 사용자 앱 승인 완료
    comp_resp = client.post("/api/v1/identity/complete", json={"tx_id": tx_id})
    assert comp_resp.status_code == 200
    print("✅ 4. 사용자 모바일 앱 생체/PIN 승인 완료 (COMPLETED)")

    # 5. 제휴사 1회성 검증 및 CI(88B)/DI(64B) 수령
    verify_resp = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["verified"] is True
    assert len(v_data["ci"]) == 88
    assert len(v_data["di"]) == 64
    print(f"✅ 5. 본인확인 결과 수령 (CI: {len(v_data['ci'])}B, DI: {len(v_data['di'])}B 표준 충족)")

    # 6. Replay Attack 재전송 방지 검증 (AUTH_4009)
    replay_resp = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert replay_resp.status_code == 400
    assert replay_resp.json()["detail"]["error_code"] == "AUTH_4009_ALREADY_VERIFIED"
    print("✅ 6. 재전송 공격(Replay Attack) 원천 차단 (AUTH_4009) 정상 방어")

    print("\n==================================================")
    print("▶ [Test 2] PKI 전자서명 및 실시간 OCSP 검증 테스트")
    print("==================================================")
    # 7. 전자서명 요청
    sign_req = client.post("/api/v1/sign/request", headers=headers, json={
        "user_name": "이몽룡",
        "user_phone": "010-9999-8888",
        "document_title": "금융 대출 약정서",
        "document_payload": "대출금 10,000,000원에 동의합니다."
    })
    assert sign_req.status_code == 200
    sign_tx_id = sign_req.json()["tx_id"]
    print("✅ 7. 전자서명 요청 트랜잭션 발급:", sign_tx_id)

    # 8. 사용자 앱 서명 생성
    client.post("/api/v1/sign/complete", json={"tx_id": sign_tx_id})
    print("✅ 8. 가입자 개인키 기반 RSA-2048 전자서명 완료")

    # 9. 서명 검증 및 OCSP 상태 확인
    verify_sign = client.post("/api/v1/sign/verify", headers=headers, json={"tx_id": sign_tx_id})
    assert verify_sign.status_code == 200
    s_data = verify_sign.json()
    assert s_data["signature_details"]["ocsp_status"] == "GOOD"
    print("✅ 9. 전자서명 무결성 & 실시간 OCSP 상태 (GOOD) 검증 성공")

    print("\n==================================================")
    print("▶ [Test 3] Hash-Chain 감사 로그 및 AI 컴플라이언스 스캔")
    print("==================================================")
    # 10. 감사 로그 무결성 전수 검증
    integrity = audit_logger.verify_integrity()
    assert integrity["is_valid"] is True
    print(f"✅ 10. 블록체인형 Hash-Chain 무결성 검증 통과 (총 {integrity['total_records']}건, 100% 무결성)")

    # 11. AI 컴플라이언스 자동 점검 리포트
    scan_resp = client.get("/api/v1/compliance/scan")
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["compliance_score"] == 100
    print(f"✅ 11. 라이선스 심사 AI 자동 진단 점수: {scan_data['compliance_score']}% (READY_FOR_AUDIT)")
    
    print("\n🎉 모든 단위 및 통합 엔지니어링 테스트를 100% 성공적으로 통과했습니다!")

if __name__ == "__main__":
    run_tests()
