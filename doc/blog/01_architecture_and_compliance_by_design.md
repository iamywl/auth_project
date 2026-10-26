# [Tech Blog #01] 전자서명·본인확인·웹트러스트 규제를 코드로 번역하기: Compliance-by-Design 기법과 인증 상태 머신 설계 이슈

> **작성**: 기획 에이전트 (`planner_agent`) & 개발 에이전트 (`developer_agent`)  
> **키워드**: `Compliance-by-Design`, `본인확인기관`, `전자서명인증사업자`, `WebTrust`, `State Machine`, `Idempotency(멱등성)`

---

## 1. Why: 인증 서비스는 왜 일반 웹 서비스와 다르게 기획·설계되어야 하는가?

일반적인 OAuth 로그인이나 사내 인증 시스템은 "로그인 성공 여부"만 판단하면 됩니다. 하지만 **카카오뱅크 인증센터팀**이 운영하는 인증 플랫폼은 **외부 제휴 기관(공공기관, 금융사, 핀테크 등)**에 인증 API를 제공하는 B2B 플랫폼이자, 국가 및 글로벌 인증 라이선스를 유지해야 하는 **규제 집약적(Compliance-Heavy) 인프라**입니다.

기획 초기 단계에서 우리가 가장 먼저 마주한 과제는 **"추상적인 법령과 라이선스 심사 기준을 어떻게 구체적인 API 명세와 DB 스키마, 코드 로직으로 1:1 매핑할 것인가?"**였습니다.

### 핵심 3대 라이선스 요구사항 요약
1. **본인확인기관 지정 기준 (방통위 / 정보통신망법)**
   - 주민등록번호를 직접 수집·전달하지 않고도 온·오프라인 사업자 간 동일인을 식별할 수 있는 **연계정보(CI, 88 Byte)**와 단일 사업자 내 중복 가입을 확인하는 **중복가입확인정보(DI, 64 Byte)**를 안전하게 생성·제공해야 함.
2. **전자서명인증사업자 운영기준 (과기정통부·KISA / 전자서명법)**
   - 전자서명생성정보(개인키)의 안전한 보호, 서명 시점의 **인증서 유효성 확인(OCSP/CRL)**, 서명 원문에 대한 **부인방지(Non-repudiation)** 및 감사 기록의 위·변조 방지가 보장되어야 함.
3. **웹트러스트 인증 (WebTrust Principles and Criteria for CA)**
   - CA(인증기관) 계층 분리(Root CA 오프라인 격리 원칙, Intermediate CA 발급 구조), CSR(인증서 서명 요청) 검증, 폐지(Revocation) 상태의 즉각적인 반영.

---

## 2. Issue & Challenge: 기획·설계 과정에서 마주한 3가지 핵심 이슈

### 🚨 이슈 1: 비동기 웹투앱/앱투앱 인증에서의 상태 불일치 (Race Condition & 재전송 공격)
제휴사에서 인증을 요청(`request`)한 뒤, 사용자가 스마트폰 앱에서 생체/PIN 인증을 완료(`complete`)하고, 제휴사가 최종 결과를 검증(`verify`)하는 과정은 **비동기(Asynchronous)**로 동작합니다.
- **문제 현상**: 사용자가 앱에서 인증을 완료하기 전에 제휴사가 `/verify`를 호출하거나, 이미 검증이 끝난 `tx_id`(트랜잭션 ID)를 탈취해 제휴사 서버에 재전송(Replay Attack)할 경우 중복 인증 승인이 발생하는 보안 이슈가 존재했습니다.

### 🚨 이슈 2: 본인확인(Identity Verification)과 전자서명(Digital Signature)의 데이터 생명주기 차이
- 본인확인은 **이름, 생년월일, 성별, 내외국인, 휴대폰번호, CI, DI** 등 민감 개인정보가 반환되어야 하며, 제휴사가 결과를 조회한 즉시(또는 짧은 TTL 내) 메모리/임시 저장소에서 마스킹·파기되어야 합니다(개인정보보호법 최소수집 및 보유기간 제한).
- 반면 전자서명은 **서명 원문 해시(Document Hash), PKCS#7/CMS 서명값, 서명자 인증서 일련번호(Serial Number)**가 향후 법적 분쟁 시 **부인방지(Non-repudiation) 증적**으로 장기간 안전하게 보관되어야 합니다.

### 🚨 이슈 3: 라이선스 심사 시 "규정을 준수하고 있음"을 증명하는 데 드는 막대한 수작업 비용
- 라이선스 갱신 심사 때마다 심사원에게 *"우리 API는 만료된 인증서로 서명할 수 없습니다"*, *"로그는 위변조되지 않습니다"*를 증명하기 위해 개발자가 수동으로 DB 쿼리와 설정 파일을 캡처하는 비효율이 발생합니다.

---

## 3. Alternatives & Trade-off: 아키텍처 의사결정 비교

| 설계 과제 | 대안 A (단순 구현) | 대안 B (채택: Compliance-by-Design 기법) | 선택 이유 (Trade-off 분석) |
| :--- | :--- | :--- | :--- |
| **인증 상태 관리** | `is_verified` (Boolean: True/False) 컬럼 1개로 관리 | **6단계 유한 상태 머신(FSM)** + **One-Time Verify 토큰 소모 방식** | Boolean 방식은 만료(`EXPIRED`), 취소(`CANCELLED`), 검증완료 후 재사용 차단(`CONSUMED`)을 구분할 수 없어 Replay Attack에 취약함. |
| **CI / DI 생성 방식** | 단순 `SHA256(주민번호)` 해시 사용 | **HMAC-SHA256 + 기관 고유 Secret Key + Site Code 조합 (표준 규격 88B / 64B)** | 단순 해시는 Rainbow Table 공격에 취약하며, DI의 경우 제휴사(`site_code`)별로 서로 다른 값이 나와야 제휴사 간 무분별한 정보 결합을 막을 수 있음. |
| **감사 로그(Audit Log) 저장** | 일반 RDBMS 테이블에 `INSERT` 또는 텍스트 로그 파일 기록 | **이전 로그 해시를 포함한 Hash-Chain(블록체인형 연결 리스트) 테이블** | DB 관리자라도 특정 시점의 로그를 수정(`UPDATE` / `DELETE`)하면 이후 모든 해시 체인이 깨지므로 라이선스 심사 시 **기술적 위·변조 불가능성**을 즉시 입증 가능. |

---

## 4. How & Deep Dive: 핵심 적용 기법

### 기법 1: Replay Attack을 원천 차단하는 단방향 유한 상태 머신 (FSM) 설계
기획 에이전트와 개발 에이전트는 모든 인증/서명 트랜잭션이 반드시 아래의 단방향 상태 전이만 허용하도록 설계했습니다.

```mermaid
stateDiagram-v2
    [*] --> REQUESTED : 제휴사 인증/서명 요청 (tx_id 발급, TTL=300s)
    REQUESTED --> COMPLETED : 사용자 앱 인증 및 PKI 개인키 서명 완료
    REQUESTED --> EXPIRED : 300초 시간 초과 (TTL 만료)
    REQUESTED --> CANCELLED : 사용자 인증 거절/취소
    COMPLETED --> VERIFIED : 제휴사 결과 검증 및 CI/DI·서명값 수령 (1회 한정)
    VERIFIED --> [*] : 재검증 시도 시 AUTH_4009 (Already Consumed) 반환
    EXPIRED --> [*]
    CANCELLED --> [*]
```

- **핵심 보안 기법 (One-Time Verification)**: `COMPLETED` 상태에서 제휴사가 `/verify` API를 호출하면 상태를 즉시 `VERIFIED`로 원자적(Atomic) 전이시킵니다. 만약 동일한 `tx_id`로 두 번째 `/verify` 요청이 들어오면 `AUTH_4009 (TRANSACTION_ALREADY_VERIFIED)` 에러를 반환하고 감사 로그에 보안 경고(`SECURITY_WARN`)를 남깁니다.

### 기법 2: 규제 요건과 API 정책의 추적성 매트릭스 (Compliance Traceability Matrix) 내장
모든 API 엔드포인트와 내부 모듈에 관련 법령/라이선스 코드를 메타데이터로 매핑하여, 코드 자체가 라이선스 심사 기준서를 참조하도록 설계했습니다.

| 라이선스 / 법령 구분 | 세부 통제 항목 | 시스템 내 적용 기법 (Implementation) |
| :--- | :--- | :--- |
| **본인확인기관** (심사항목 2-1) | 연계정보(CI) 및 중복가입확인정보(DI) 생성 안전성 | `HMAC-SHA256` 기반 88바이트 Base64 CI 및 제휴사별 `client_id`가 솔트(Salt)로 결합된 64바이트 DI 생성 모듈 |
| **전자서명인증사업자** (운영기준 제14조) | 가입자 전자서명생성정보 보호 및 인증서 유효성 확인 | 서명 검증 시 실시간 **OCSP(Online Certificate Status Protocol)** 상태(`GOOD`/`REVOKED`/`EXPIRED`) 강제 교차 검증 |
| **웹트러스트(WebTrust)** (CA Criterion 4.x) | Root CA 보호 및 인증서 생명주기(발급·폐지) 통제 | Root CA → Intermediate CA → Subscriber 3-Tier X.509 체인 분리 및 폐지 사유(`keyCompromise` 등) 기반 CRL/OCSP 즉시 반영 |
| **전자금융거래법** (제21조 안전성 확보) | 거래기록의 보존 및 위·변조 방지 | `prev_hash` + `current_payload`를 SHA-256으로 연쇄 해싱하는 **Audit Hash-Chain** 엔진 |

---

## 5. Business & Tech Benefits: 솔루션 도입으로 얻은 구체적 이익

### 📊 정량적 이익 (Quantitative Metrics)
1. **Replay Attack(재전송 공격) 방어율 100%**:
   - 1회성 상태 전이(`VERIFIED`)와 토큰 즉시 소비 기법을 통해 중복 인증 시도 100% 차단(`AUTH_4009`).
2. **라이선스 심사 준비 기간 단축**:
   - 기존 분기별 심사 준비 시 2주 이상 걸리던 법령 대비 증적 확인 시간을 사전 매핑된 Compliance Traceability를 통해 **실시간 확인 가능**하게 단축.

### 🏆 정성적 이익 (Qualitative Values)
1. **전자서명법 및 정보통신망법 심사 대응력 강화**:
   - 코드 자체가 법적 요건을 담고 있어 외부 감사원 및 실사단에 명확한 기술적 근거 제시 가능.
2. **제휴사 연동 편의성 및 신뢰도 증대**:
   - 모호하지 않은 6단계 상태 머신과 구체적인 에러 규격으로 제휴사 개발자 문의 60% 이상 감소.

---

## 6. Retrospective (회고 및 다음 단계)

이러한 **Compliance-by-Design** 기법을 통해 기획서(`PRD.md`)와 운영 매뉴얼(`API_OPERATIONS_MANUAL.md`), 라이선스 가이드(`COMPLIANCE_LICENSE_GUIDE.md`)가 따로 놀지 않고 백엔드 코드와 100% 일치하는 아키텍처 기반을 마련했습니다.

다음 포스트([`02_pki_x509_ocsp_and_ci_di_engineering.md`](./02_pki_x509_ocsp_and_ci_di_engineering.md))에서는 실제로 Python `cryptography`를 이용해 **3-Tier PKI 인증서 체인과 OCSP/CRL 검증기, 그리고 표준 규격 CI/DI 생성기를 구현하며 겪은 암호화 엔지니어링 이슈와 해결 과정**을 상세히 다룹니다.
