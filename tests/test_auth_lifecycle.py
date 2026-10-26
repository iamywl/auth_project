import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, pki_engine, audit_logger

client = TestClient(app)

def test_full_oauth_and_identity_lifecycle():
    # 1. OAuth 토큰 발급
    token_resp = client.post("/api/v1/oauth/token", json={
        "client_id": "test_partner_id",
        "client_secret": "test_partner_secret"
    })
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 본인확인 요청 (REQUESTED)
    req_resp = client.post("/api/v1/identity/request", headers=headers, json={
        "user_name": "홍길동",
        "user_phone": "010-1234-5678",
        "user_birth": "19950515",
        "request_reason": "회원가입"
    })
    assert req_resp.status_code == 200
    tx_id = req_resp.json()["tx_id"]
    assert req_resp.json()["status"] == "REQUESTED"

    # 3. 유저 앱 승인 전 검증 시도 시 실패 (AUTH_4005)
    pre_verify = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert pre_verify.status_code == 400
    assert pre_verify.json()["detail"]["error_code"] == "AUTH_4005_TRANSACTION_PENDING"

    # 4. 유저 앱에서 본인인증 완료 시뮬레이션 (COMPLETED)
    comp_resp = client.post("/api/v1/identity/complete", json={"tx_id": tx_id})
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "COMPLETED"

    # 5. 제휴사 결과 검증 (1회 소비, CI 88B, DI 64B 수령)
    verify_resp = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert verify_resp.status_code == 200
    res_data = verify_resp.json()
    assert res_data["verified"] is True
    assert len(res_data["ci"]) == 88
    assert len(res_data["di"]) == 64

    # 6. Replay Attack 방지 검증: 동일 tx_id로 2회차 검증 시도시 차단 (AUTH_4009)
    replay_resp = client.post("/api/v1/identity/verify", headers=headers, json={"tx_id": tx_id})
    assert replay_resp.status_code == 400
    assert replay_resp.json()["detail"]["error_code"] == "AUTH_4009_ALREADY_VERIFIED"

def test_digital_signature_and_ocsp_revocation():
    # 1. 토큰 발급
    token_resp = client.post("/api/v1/oauth/token", json={
        "client_id": "test_partner_id",
        "client_secret": "test_partner_secret"
    })
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 서명 요청
    sign_req = client.post("/api/v1/sign/request", headers=headers, json={
        "user_name": "이몽룡",
        "user_phone": "010-9999-8888",
        "document_title": "금융 대출 약정서",
        "document_payload": "대출금 10,000,000원에 동의합니다."
    })
    assert sign_req.status_code == 200
    tx_id = sign_req.json()["tx_id"]

    # 3. 유저 앱 전자서명 생성
    client.post("/api/v1/sign/complete", json={"tx_id": tx_id})

    # 4. 서명 검증 성공
    verify_resp = client.post("/api/v1/sign/verify", headers=headers, json={"tx_id": tx_id})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["signature_details"]["ocsp_status"] == "GOOD"

def test_hash_chain_audit_integrity():
    integrity = audit_logger.verify_integrity()
    assert integrity["is_valid"] is True
    assert integrity["total_records"] > 0

def test_compliance_ax_scan():
    scan_resp = client.get("/api/v1/compliance/scan")
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["compliance_score"] == 100
    assert scan_data["overall_status"] == "READY_FOR_AUDIT"
