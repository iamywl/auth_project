# auth_project

## 📌 프로젝트 개요 (Project Overview)
**카카오뱅크 인증센터팀 (본인확인기관 · 전자서명인증사업자 · 웹트러스트 인증)** 도메인을 타겟으로 한 **차세대 통합 인증 서비스 & 제휴사 API 포털 및 AI 기반 컴플라이언스/심사 자동화(AX) 플랫폼** 프로젝트입니다.

---

## 🎯 핵심 목표 및 도메인 범위
1. **제휴사 인증 API & 개발자 포털 (B2B Partner Portal & API Gateway)**
   - 본인확인(CI/DI 발급), 전자서명(PKI/전자서명값 검증), 간편인증 요청/검증 RESTful API 제공
   - 제휴사 온보딩(Client ID/Secret 발급, 이용기관 등록, Webhook 설정, 통계/트래픽 모니터링) 포털
   - 인터랙티브 **API 운영 매뉴얼 & 연동 테스트베드(Sandbox)** 내장
2. **인증 라이선스 & 컴플라이언스 AX (AI Transformation) 센터**
   - 본인확인기관, 전자서명인증사업자, 웹트러스트(WebTrust), 전자금융거래법, 개인정보보호법 등 **컴플라이언스 법령/가이드라인 AI 분석 및 라이선스 심사 대응 체크리스트 자동 점검 에이전트**
   - 감사 로그(Audit Trail) 무결성 검증 및 라이선스 심사 증적 보고서 자동 생성
3. **PKI & 인증서 라이프사이클 관리 시뮬레이터**
   - Root CA / Intermediate CA / 가입자 인증서 발급(CSR), 갱신, 폐지(CRL / OCSP) 및 전자서명 검증 파이프라인 구현

---

## 📌 채용 JD(Job Description) 핵심 충족 역량 기준
본 프로젝트의 모든 에이전트(기획 · 개발 · QA)는 다음 **4대 핵심 JD 요건**을 철저히 충족하도록 설계하고 구현 및 문서화합니다:

1. **Hexagonal Architecture (포트 & 어댑터) 등 클린 아키텍처 적용**:
   - 도메인 코어(PKI 암호화, FSM 상태 머신, CI/DI 유도 규칙)를 프레임워크나 외부 I/O와 분리.
   - **Inbound Port/Adapter** (REST API Controller, Partner Webhook, Admin Portal CLI)와 **Outbound Port/Adapter** (Redis Token/Session Store, RDBMS Audit Log Repo, HSM/KMS Crypto Adapter, OCSP Client)로 명확히 분리하여 결합도를 낮추고 테스트 용이성을 극대화.
2. **Redis를 활용한 고성능 분산 캐시 & 세션 & 분산 락(Distributed Lock) 설계**:
   - OAuth 2.0 세션 및 제휴사 토큰의 고속 In-Memory TTL 캐싱.
   - `Redlock` 알고리즘 또는 `SET key val NX PX`를 활용한 **트랜잭션 결과 검증 분산 락** 구현으로 멀티 인스턴스 환경에서도 Replay Attack 완벽 차단.
   - OCSP 응답 캐싱(Stapling)을 통한 CA 서버 부하 절감.
3. **GitLab CI/CD 파이프라인 구성 및 무중단 배포 체계**:
   - `.gitlab-ci.yml` 파이프라인 구축: Lint → Type Check → Unit Test → High-Concurrency QA Stress Test → Docker Build → Security Scan(SAST) → Kubernetes Rolling Update.
4. **대규모 서비스(DAU 1만~수백만 이상) 운영 및 고가용성 대응**:
   - 초당 수천 RPS의 스파이크 트래픽 대응을 위한 비동기 I/O 파이프라인.
   - Throttling/Rate Limiting(Token Bucket 알고리즘) 적용으로 제휴사별 DoS 방지.
   - Hash-Chain 감사 로그의 동시 쓰기 경합(Race Condition) 방지 및 분산 트랜잭션 멱등성 보장.

---

## 🤖 멀티 에이전트 협업 체계 (Multi-Agent System)
본 프로젝트는 역할별로 분리된 전문 에이전트 가이드를 기반으로 진행됩니다.

- **총괄 규칙**: [`AGENTS.md`](./AGENTS.md) (현재 파일)
- **기획/비즈니스 에이전트**: [`.agents/planner_agent.md`](./.agents/planner_agent.md)
- **아키텍처/풀스택/AX 개발 에이전트**: [`.agents/developer_agent.md`](./.agents/developer_agent.md)
- **QA/대규모 동시성·트래픽 스트레스/보안 검증 에이전트**: [`.agents/qa_agent.md`](./.agents/qa_agent.md)
- **컴플라이언스/법령·라이선스 감사/문서화 검토 에이전트**: [`.agents/compliance_agent.md`](./.agents/compliance_agent.md)
- **기술 블로깅 & 트러블슈팅 기록 규칙**: 기획, 아키텍처, 개발, QA 동시성 검증 및 컴플라이언스 심사 검토 과정에서 발생하는 모든 이슈(Race Condition, Deadlock, Hash-Chain Forking, TOCTOU, 규제 적합성)와 해결 기법을 `doc/blog/` 디렉토리에 6단계 작성 표준에 맞춰 상세히 연재합니다.

---

## 📁 디렉토리 구조 (Directory Structure)
```text
auth_project/
├── AGENTS.md                        # 프로젝트 총괄 에이전트 지침
├── README.md                        # 프로젝트 소개 및 실행 가이드
├── .agents/
│   ├── planner_agent.md             # [기획 에이전트] 서비스/포털 기획, API 운영 매뉴얼 작성
│   ├── developer_agent.md           # [개발 에이전트] PKI/인증 API, Hexagonal 아키텍처, Redis 락 구현
│   ├── qa_agent.md                  # [QA 에이전트] 대규모 동시성, 레이스 컨디션, 스트레스 부하 검증
│   └── compliance_agent.md          # [컴플라이언스 에이전트] 3대 라이선스 심사, 아키텍처 문서화 완전성 감사
├── doc/                             # 기획서, API 운영 매뉴얼, 라이선스 심사 문서 및 기술 블로그
│   ├── ARCHITECTURE.md              # Hexagonal 아키텍처 명세 및 공식 아이콘 R&R
│   ├── ARCHITECTURE_REVIEW_REPORT.md# [컴플라이언스 감사] 아키텍처 및 기술 문서화 완전성 심사 보고서
│   ├── PRD.md                       # 서비스 및 제휴사 포털 기획서
│   ├── API_OPERATIONS_MANUAL.md     # 제휴사 인증 API 상세 운영 매뉴얼
│   ├── COMPLIANCE_LICENSE_GUIDE.md  # 전자서명/본인확인/웹트러스트 라이선스 심사 기준 및 체크리스트
│   ├── assets/icons/                # 오픈소스 공식 벡터 아이콘 (FastAPI, Redis, GitLab, Python, Docker)
│   └── blog/                        # 6단계 표준 기술 블로그 시리즈
│       ├── GUIDELINES.md            # 블로그 작성 가이드라인 (Why-PainPoints-Tradeoff-DeepDive-Benefits)
│       └── 01 ~ 05_*.md             # 5편의 엔지니어링 기술 블로그
├── backend/                         # 인증 API 서버, PKI 엔진, 동시성 세이프 감사 엔진, AX 모듈
└── frontend/                        # 제휴사 포털 사이트 & 실시간 스트레스 테스트 대시보드
```

---

## 🛠️ 공통 작업 원칙 (General Guidelines)
1. **컴플라이언스 우선 설계 (Compliance-by-Design)**: 모든 기능과 API는 전자서명법, 정보통신망법(본인확인기관), 전자금융거래법, 개인정보보호법 요건(암호화, 접근통제, 감사로그, 연계정보 CI/중복가입확인정보 DI 안전성)을 준수하여 기획·개발합니다.
2. **문서화의 명확성 (Technical Writing Excellence)**: 모든 API와 프로세스는 제휴사 개발자와 라이선스 심사원이 즉시 이해할 수 있도록 시퀀스 다이어그램, 에러 코드표, 요청/응답 명세를 포함해 문서화합니다.
3. **실행 가능한 AX (Actionable AI Transformation)**: 단순 개념 제시가 아닌, 실제 법령/심사 기준 분석 자동화, 제휴사 기술지원 Q&A 챗봇, API 연동 코드/매뉴얼 자동 생성 등 실질적인 업무 효율화(AX) 기능을 구현합니다.
