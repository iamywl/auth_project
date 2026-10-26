import uuid
import time
import datetime
import hashlib
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .pki_engine import pki_engine
from .audit_logger import audit_logger
from .compliance_ax import compliance_ax_engine
from .redis_adapter import dist_lock_service, redis_session_store

app = FastAPI(
    title="KakaoBank Partner Auth & Compliance AX Platform",
    description="카카오뱅크 인증센터 제휴사 인증 API & 라이선스 심사/컴플라이언스 AX 게이트웨이",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public"))
if os.path.exists(static_dir):
    app.mount("/portal", StaticFiles(directory=static_dir, html=True), name="portal")

# 인메모리 저장소 (프로토타입 / 데모용)
PARTNERS_DB = {
    "partner_kb_sec_01": {
        "client_secret": "sec_kbbank_9938174209",
        "name": "카카오페이 증권",
        "allowed_ips": ["*"]
    },
    "test_partner_id": {
        "client_secret": "test_partner_secret",
        "name": "테스트 제휴사 (Sandbox)",
        "allowed_ips": ["*"]
    }
}

ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}
TRANSACTIONS_DB: Dict[str, Dict[str, Any]] = {}

# --- Pydantic DTO Schemas ---
class TokenRequest(BaseModel):
    client_id: str = Field(..., example="test_partner_id")
    client_secret: str = Field(..., example="test_partner_secret")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    scope: str = "identity sign"

class IdentityRequest(BaseModel):
    user_name: str = Field(..., example="홍길동")
    user_phone: str = Field(..., example="010-1234-5678")
    user_birth: str = Field(..., example="19900101")
    request_reason: str = Field(default="서비스 본인확인", example="회원가입")
    ttl_seconds: int = Field(default=300, ge=60, le=600)

class AppCompleteRequest(BaseModel):
    tx_id: str
    pin_or_bio_token: str = "BIO_AUTHENTICATED_TOKEN"

class VerifyRequest(BaseModel):
    tx_id: str

class SignRequest(BaseModel):
    user_name: str = Field(..., example="홍길동")
    user_phone: str = Field(..., example="010-1234-5678")
    document_title: str = Field(..., example="비대면 금융상품 가입 계약서")
    document_payload: str = Field(..., example="본인은 상기 계약 내용에 동의합니다.")
    ttl_seconds: int = Field(default=300)

class AXQueryRequest(BaseModel):
    query: str

# --- Helper Dependency ---
def verify_partner_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_4001_UNAUTHORIZED", "message": "Bearer Access Token이 필요합니다."}
        )
    token = authorization.split(" ")[1]
    if token not in ACTIVE_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_4002_TOKEN_EXPIRED", "message": "유효하지 않거나 만료된 토큰입니다."}
        )
    return ACTIVE_TOKENS[token]["client_id"]

# --- 1. OAuth Token API ---
@app.post("/api/v1/oauth/token", response_model=TokenResponse, tags=["OAuth"])
def issue_oauth_token(req: TokenRequest):
    partner = PARTNERS_DB.get(req.client_id)
    if not partner or partner["client_secret"] != req.client_secret:
        audit_logger.log(
            action="OAUTH_TOKEN_FAILED",
            client_id=req.client_id,
            tx_id="N/A",
            payload_summary={"reason": "Invalid credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_4001_INVALID_CREDENTIALS", "message": "클라이언트 ID 또는 Secret이 잘못되었습니다."}
        )

    token_str = f"kb_at_{uuid.uuid4().hex}"
    
    # Redis 세션 저장소에 세션 캐싱 (DAU 스케일아웃 분산 아키텍처)
    redis_session_store.set(token_str, {"client_id": req.client_id}, ttl_seconds=3600)
    ACTIVE_TOKENS[token_str] = {
        "client_id": req.client_id,
        "created_at": time.time(),
        "expires_at": time.time() + 3600
    }

    audit_logger.log(
        action="OAUTH_TOKEN_ISSUED",
        client_id=req.client_id,
        tx_id="N/A",
        payload_summary={"scope": "identity sign", "expires_in": 3600}
    )

    return TokenResponse(access_token=token_str)

# --- 2. Identity Verification APIs (본인확인) ---
@app.post("/api/v1/identity/request", tags=["Identity"])
def request_identity_verification(req: IdentityRequest, client_id: str = Depends(verify_partner_token)):
    tx_id = f"tx_id_{uuid.uuid4().hex[:12]}"
    now = time.time()
    
    # 가입자 임시 인증서 발급 (PKI 시뮬레이션)
    user_cert_pem, user_key_pem, serial = pki_engine.issue_user_certificate(req.user_name, req.user_phone)

    TRANSACTIONS_DB[tx_id] = {
        "tx_id": tx_id,
        "tx_type": "IDENTITY",
        "client_id": client_id,
        "status": "REQUESTED", # REQUESTED -> COMPLETED -> VERIFIED
        "user_name": req.user_name,
        "user_phone": req.user_phone,
        "user_birth": req.user_birth,
        "user_cert_pem": user_cert_pem,
        "user_key_pem": user_key_pem,
        "cert_serial": serial,
        "created_at": now,
        "expires_at": now + req.ttl_seconds
    }

    audit_logger.log(
        action="IDENTITY_REQUEST_CREATED",
        client_id=client_id,
        tx_id=tx_id,
        payload_summary={"user_name": req.user_name, "ttl": req.ttl_seconds}
    )

    return {
        "tx_id": tx_id,
        "status": "REQUESTED",
        "expires_at": int(now + req.ttl_seconds),
        "message": "인증 요청이 접수되었습니다. 사용자가 모바일 앱에서 승인해야 합니다."
    }

@app.post("/api/v1/identity/complete", tags=["Identity Simulator"])
def complete_identity_in_user_app(req: AppCompleteRequest):
    """사용자가 스마트폰 앱에서 본인인증(생체/PIN)을 성공적으로 승인하는 시뮬레이터"""
    tx = TRANSACTIONS_DB.get(req.tx_id)
    if not tx:
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4004_NOT_FOUND", "message": "존재하지 않는 트랜잭션입니다."})

    if tx["status"] != "REQUESTED":
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4006_INVALID_STATE", "message": f"현재 상태({tx['status']})에서는 승인할 수 없습니다."})

    if time.time() > tx["expires_at"]:
        tx["status"] = "EXPIRED"
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4008_EXPIRED", "message": "인증 유효시간(TTL)이 초과되었습니다."})

    tx["status"] = "COMPLETED"
    tx["completed_at"] = time.time()

    audit_logger.log(
        action="IDENTITY_APP_COMPLETED",
        client_id=tx["client_id"],
        tx_id=req.tx_id,
        payload_summary={"method": "BIO_AUTH"}
    )

    return {"tx_id": req.tx_id, "status": "COMPLETED", "message": "사용자 앱 승인이 완료되었습니다."}

@app.post("/api/v1/identity/verify", tags=["Identity"])
def verify_identity_result(req: VerifyRequest, client_id: str = Depends(verify_partner_token)):
    """
    제휴사가 1회에 한해 본인확인 결과를 조회
    - Redis 분산 락(Distributed Lock)을 적용하여 멀티스레드/멀티인스턴스 고동시성 Replay Attack 완벽 차단
    """
    lock_key = f"lock:verify:{req.tx_id}"
    # Redis 분산 락 획득 시도 (동시 요청 경합 방어)
    acquired = dist_lock_service.acquire_lock(lock_key, ttl_ms=3000)
    if not acquired:
        audit_logger.log(
            action="SECURITY_ALERT_CONCURRENT_RACE_CONDITION",
            client_id=client_id,
            tx_id=req.tx_id,
            payload_summary={"warning": "Concurrent verify requests detected. Distributed lock contention."}
        )
        raise HTTPException(
            status_code=400,
            detail={"error_code": "AUTH_4009_ALREADY_VERIFIED", "message": "동시 검증 요청 경합 또는 이미 소비된 트랜잭션입니다."}
        )

    try:
        tx = TRANSACTIONS_DB.get(req.tx_id)
        if not tx:
            raise HTTPException(status_code=400, detail={"error_code": "AUTH_4004_NOT_FOUND", "message": "트랜잭션을 찾을 수 없습니다."})

        if tx["client_id"] != client_id:
            raise HTTPException(status_code=403, detail={"error_code": "AUTH_4003_FORBIDDEN", "message": "해당 제휴사의 트랜잭션이 아닙니다."})

        # Replay Attack 차단: 이미 소비(VERIFIED)된 트랜잭션
        if tx["status"] == "VERIFIED":
            audit_logger.log(
                action="SECURITY_ALERT_REPLAY_ATTACK",
                client_id=client_id,
                tx_id=req.tx_id,
                payload_summary={"warning": "Double verification attempt blocked"}
            )
            raise HTTPException(
                status_code=400,
                detail={"error_code": "AUTH_4009_ALREADY_VERIFIED", "message": "이미 결과 조회가 완료된 1회성 트랜잭션입니다. (재사용 불가)"}
            )

        if tx["status"] == "REQUESTED":
            raise HTTPException(
                status_code=400,
                detail={"error_code": "AUTH_4005_TRANSACTION_PENDING", "message": "사용자가 아직 앱에서 인증을 완료하지 않았습니다."}
            )

        if tx["status"] != "COMPLETED":
            raise HTTPException(status_code=400, detail={"error_code": "AUTH_4006_INVALID_STATE", "message": f"트랜잭션 상태 불일치 ({tx['status']})"})

        # 상태 원자적 전이: COMPLETED -> VERIFIED
        tx["status"] = "VERIFIED"

        # 표준 규격 CI (88B), DI (64B) 생성
        rrn_back_dummy = hashlib.sha256(f"{tx['user_birth']}:{tx['user_phone']}".encode()).hexdigest()
        ci, di = pki_engine.generate_ci_and_di(tx["user_birth"][:6], rrn_back_dummy, client_id)

        audit_logger.log(
            action="IDENTITY_VERIFIED_CONSUMED",
            client_id=client_id,
            tx_id=req.tx_id,
            payload_summary={"ci_length": len(ci), "di_length": len(di)}
        )

        return {
            "tx_id": req.tx_id,
            "verified": True,
            "user_info": {
                "name": tx["user_name"],
                "birthday": tx["user_birth"],
                "gender": "1" if int(tx["user_birth"][:4]) < 2000 else "3",
                "phone": tx["user_phone"]
            },
            "ci": ci,
            "di": di,
            "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    finally:
        # 분산 락 해제
        dist_lock_service.release_lock(lock_key)

# --- 3. Digital Signature APIs (전자서명) ---
@app.post("/api/v1/sign/request", tags=["Digital Signature"])
def request_digital_signature(req: SignRequest, client_id: str = Depends(verify_partner_token)):
    tx_id = f"tx_sign_{uuid.uuid4().hex[:12]}"
    now = time.time()
    
    user_cert_pem, user_key_pem, serial = pki_engine.issue_user_certificate(req.user_name, req.user_phone)

    TRANSACTIONS_DB[tx_id] = {
        "tx_id": tx_id,
        "tx_type": "SIGN",
        "client_id": client_id,
        "status": "REQUESTED",
        "user_name": req.user_name,
        "user_phone": req.user_phone,
        "document_title": req.document_title,
        "document_payload": req.document_payload,
        "user_cert_pem": user_cert_pem,
        "user_key_pem": user_key_pem,
        "cert_serial": serial,
        "signature_b64": None,
        "created_at": now,
        "expires_at": now + req.ttl_seconds
    }

    audit_logger.log(
        action="SIGN_REQUEST_CREATED",
        client_id=client_id,
        tx_id=tx_id,
        payload_summary={"doc_title": req.document_title}
    )

    return {
        "tx_id": tx_id,
        "status": "REQUESTED",
        "expires_at": int(now + req.ttl_seconds),
        "message": "전자서명 요청이 생성되었습니다."
    }

@app.post("/api/v1/sign/complete", tags=["Digital Signature Simulator"])
def complete_sign_in_user_app(req: AppCompleteRequest):
    tx = TRANSACTIONS_DB.get(req.tx_id)
    if not tx or tx["tx_type"] != "SIGN":
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4004_NOT_FOUND", "message": "전자서명 트랜잭션을 찾을 수 없습니다."})

    # 실제 RSA 개인키 전자서명 수행
    doc_hash = hashlib.sha256(tx["document_payload"].encode("utf-8")).hexdigest()
    signature_b64 = pki_engine.sign_data(doc_hash, tx["user_key_pem"])
    
    tx["status"] = "COMPLETED"
    tx["doc_hash"] = doc_hash
    tx["signature_b64"] = signature_b64

    audit_logger.log(
        action="SIGN_APP_COMPLETED",
        client_id=tx["client_id"],
        tx_id=req.tx_id,
        payload_summary={"doc_hash": doc_hash}
    )

    return {"tx_id": req.tx_id, "status": "COMPLETED", "message": "가입자 전자서명이 생성되었습니다."}

@app.post("/api/v1/sign/verify", tags=["Digital Signature"])
def verify_digital_signature(req: VerifyRequest, client_id: str = Depends(verify_partner_token)):
    tx = TRANSACTIONS_DB.get(req.tx_id)
    if not tx or tx["tx_type"] != "SIGN":
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4004_NOT_FOUND", "message": "서명 트랜잭션이 존재하지 않습니다."})

    if tx["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail={"error_code": "AUTH_4005_TRANSACTION_PENDING", "message": "서명이 완료되지 않았습니다."})

    # PKI 엔진 서명 및 실시간 OCSP 검증
    verify_result = pki_engine.verify_signature(
        data_str=tx["doc_hash"],
        signature_b64=tx["signature_b64"],
        cert_pem=tx["user_cert_pem"]
    )

    if not verify_result["valid"]:
        audit_logger.log(
            action="SIGN_VERIFICATION_FAILED",
            client_id=client_id,
            tx_id=req.tx_id,
            payload_summary=verify_result
        )
        raise HTTPException(status_code=400, detail=verify_result)

    tx["status"] = "VERIFIED"

    audit_logger.log(
        action="SIGN_VERIFIED_SUCCESS",
        client_id=client_id,
        tx_id=req.tx_id,
        payload_summary={"serial": verify_result["serial_number"]}
    )

    return {
        "tx_id": req.tx_id,
        "verified": True,
        "document_title": tx["document_title"],
        "signature_details": verify_result,
        "signature_value_b64": tx["signature_b64"][:32] + "...",
        "tsa_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

# --- 4. Compliance & License AX Endpoints (AI 전환 모듈) ---
@app.get("/api/v1/compliance/scan", tags=["Compliance AX"])
def run_compliance_license_scan():
    """라이선스 심사 대응 AI 자동 점검 스캔 리포트"""
    return compliance_ax_engine.run_license_audit_scan()

@app.get("/api/v1/audit/logs", tags=["Audit & Security"])
def get_audit_trail_logs(limit: int = 20):
    """블록체인형 Hash-Chain 감사 로그 조회"""
    return {
        "integrity": audit_logger.verify_integrity(),
        "recent_logs": audit_logger.get_recent_logs(limit=limit)
    }

@app.post("/api/v1/support/chat", tags=["Compliance AX"])
def partner_support_ai_chat(req: AXQueryRequest):
    """제휴사 기술지원 및 트러블슈팅 AI 어시스턴트"""
    return compliance_ax_engine.answer_partner_support_query(req.query)

@app.post("/api/v1/pki/revoke/{serial}", tags=["PKI Simulator"])
def simulate_revoke_certificate(serial: int):
    """심사 시연용 인증서 강제 폐지 시뮬레이터 (OCSP 실패 유도)"""
    pki_engine.revoke_certificate(serial)
    audit_logger.log(
        action="CERTIFICATE_REVOKED_BY_ADMIN",
        client_id="SYSTEM",
        tx_id="N/A",
        payload_summary={"serial": str(serial)}
    )
    return {"revoked": True, "serial": serial, "message": f"인증서 일련번호 {serial}번이 폐지(Revoked)되었습니다."}
