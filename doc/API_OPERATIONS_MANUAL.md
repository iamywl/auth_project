# 📘 제휴사 인증 API 상세 운영 매뉴얼 (API Operations Manual)

> **버전**: v1.0.0  
> **발행처**: 카카오뱅크 인증센터  
> **대상**: 제휴사 연동 개발자 및 인프라 운영 담당자  

---

## 1. 개요 및 인증 아키텍처

카카오뱅크 인증 API는 제휴사(이용기관)가 고객의 신원을 안전하게 검증(본인확인)하고 금융/전자계약 서명을 수행할 수 있도록 **OAuth 2.0 기반 보안 통신**과 **PKI 전자서명 체계**를 제공합니다.

### 1.1. 기본 연동 환경
- **프로토콜**: HTTPS / TLS 1.3 권장 (최소 TLS 1.2)
- **Base URL (운영/개발)**: `https://api-auth.kakaobank.com` (테스트베드: `http://localhost:8000`)
- **데이터 포맷**: JSON (`application/json; charset=UTF-8`)
- **공통 헤더**:
  - `Authorization: Bearer {ACCESS_TOKEN}` (OAuth 토큰 API 제외)
  - `Content-Type: application/json`
  - `X-Client-Id: {CLIENT_ID}`

---

## 2. API 엔드포인트 상세 명세

### 2.1. 제휴사 Access Token 발급
- **Endpoint**: `POST /api/v1/oauth/token`
- **설명**: 발급받은 `client_id`와 `client_secret`을 통해 API 호출용 Access Token을 획득합니다.

#### Request Body
```json
{
  "client_id": "partner_kb_sec_01",
  "client_secret": "sec_kbbank_9938174209"
}
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "identity sign"
}
```

---

### 2.2. 본인확인 요청 (Identity Verification Request)
- **Endpoint**: `POST /api/v1/identity/request`
- **설명**: 사용자 스마트폰 앱으로 본인확인 푸시를 발송하고 트랜잭션 ID(`tx_id`)를 발급받습니다.

#### Request Body
```json
{
  "user_name": "홍길동",
  "user_phone": "010-1234-5678",
  "user_birth": "19900101",
  "request_reason": "회원가입 본인확인",
  "ttl_seconds": 300
}
```

#### Response (200 OK)
```json
{
  "tx_id": "tx_ident_8a9f2b1c",
  "status": "REQUESTED",
  "expires_at": 1730000300,
  "message": "인증 요청이 성공적으로 접수되었습니다. 사용자가 앱에서 승인해야 합니다."
}
```

---

### 2.3. 본인확인 결과 조회 및 검증 (Identity Verify)
- **Endpoint**: `POST /api/v1/identity/verify`
- **설명**: 사용자가 앱에서 인증을 완료한 후, 제휴사가 1회성으로 최종 신원 결과 및 CI/DI를 수령합니다. **(1회 검증 완료 시 재조회 불가)**

#### Request Body
```json
{
  "tx_id": "tx_ident_8a9f2b1c"
}
```

#### Response (200 OK)
```json
{
  "tx_id": "tx_ident_8a9f2b1c",
  "verified": true,
  "user_info": {
    "name": "홍길동",
    "birthday": "19900101",
    "gender": "1",
    "phone": "010-1234-5678"
  },
  "ci": "aW4vZ2VuZXJhdGVkL2NpL2tleS9leGFtcGxlLzEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTA=",
  "di": "ZGlfZXhhbXBsZV9mb3JfcGFydG5lcl82NGJ5dGVzX2hhc2hfa2V5XzEyMzQ1Njc4OTAxMjM0NQ==",
  "verified_at": "2026-10-26T13:10:00Z"
}
```

---

### 2.4. 전자서명 요청 및 검증 (Digital Signature)
- **요청 Endpoint**: `POST /api/v1/sign/request`
- **검증 Endpoint**: `POST /api/v1/sign/verify`
- **검증 응답**: PKI 서명값 무결성(`valid_signature=true`), 인증서 체인 검증 결과(`chain_valid=true`), 실시간 OCSP 상태(`cert_status="GOOD"`), 서명 시점 타임스탬프 토큰(TSA) 제공.

---

## 3. 표준 에러 코드 체계 (Error Codes)

| HTTP Code | 에러 코드 (Error Code) | 에러 메시지 | 조치 및 트러블슈팅 가이드 |
| :---: | :--- | :--- | :--- |
| **401** | `AUTH_4001_INVALID_CREDENTIALS` | Client ID or Secret is invalid | 발급된 API Key 및 Secret 재확인 |
| **401** | `AUTH_4002_TOKEN_EXPIRED` | Access Token has expired | `/oauth/token`을 호출하여 토큰 재발급 |
| **400** | `AUTH_4004_TRANSACTION_NOT_FOUND` | Invalid or non-existent tx_id | 요청 시 발급된 `tx_id` 유효성 점검 |
| **400** | `AUTH_4005_TRANSACTION_PENDING` | User has not completed authentication | 유저 앱 승인 대기 중 (폴링 간격: 3초 권장) |
| **400** | `AUTH_4008_TRANSACTION_EXPIRED` | Authentication request expired (TTL over) | 300초 경과로 만료됨. 신규 인증 요청 필요 |
| **400** | `AUTH_4009_ALREADY_VERIFIED` | Transaction already consumed | 이미 1회 검증 완료된 건임. 재전송 공격 차단 |
| **500** | `CERT_5001_OCSP_REVOKED` | User certificate is revoked | 가입자 인증서 폐지됨 (서명 검증 실패) |

---

## 4. 연동 예제 코드 (Sample Integration Code)

### Python (Requests)
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 토큰 발급
token_resp = requests.post(f"{BASE_URL}/oauth/token", json={
    "client_id": "test_partner_id",
    "client_secret": "test_partner_secret"
}).json()
access_token = token_resp["access_token"]

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# 2. 본인확인 요청
req_resp = requests.post(f"{BASE_URL}/identity/request", headers=headers, json={
    "user_name": "홍길동",
    "user_phone": "010-1234-5678",
    "user_birth": "19900101",
    "request_reason": "서비스 회원가입",
    "ttl_seconds": 300
}).json()
tx_id = req_resp["tx_id"]
print(f"인증 트랜잭션 발급: {tx_id}")

# 3. 유저 앱 인증 후 결과 검증 (1회)
verify_resp = requests.post(f"{BASE_URL}/identity/verify", headers=headers, json={
    "tx_id": tx_id
}).json()
print("본인확인 CI/DI 결과:", verify_resp)
```
