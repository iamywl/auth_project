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

## 🤖 멀티 에이전트 협업 체계 (Multi-Agent System)
본 프로젝트는 역할별로 분리된 전문 에이전트 가이드를 기반으로 진행됩니다.

- **총괄 규칙**: [`AGENTS.md`](./AGENTS.md) (현재 파일)
- **기획/컴플라이언스/문서화 에이전트**: [`.agents/planner_agent.md`](./.agents/planner_agent.md)
- **아키텍처/백엔드/프론트엔드/AX 개발 에이전트**: [`.agents/developer_agent.md`](./.agents/developer_agent.md)

---

## 📁 디렉토리 구조 (Directory Structure)
```text
auth_project/
├── AGENTS.md                        # 프로젝트 총괄 에이전트 지침
├── README.md                        # 프로젝트 소개 및 실행 가이드
├── .agents/
│   ├── planner_agent.md             # [기획 에이전트] 서비스/포털 기획, 컴플라이언스 분석, API 운영 매뉴얼 작성
│   └── developer_agent.md           # [개발 에이전트] PKI/인증 API, 제휴사 포털, AI 컴플라이언스 AX 구현
├── docs/                            # 기획서, 컴플라이언스 매핑표, API 운영 매뉴얼, 심사 대응 문서
│   ├── PRD.md                       # 서비스 및 제휴사 포털 기획서
│   ├── API_OPERATIONS_MANUAL.md     # 제휴사 인증 API 상세 운영 매뉴얼
│   └── COMPLIANCE_LICENSE_GUIDE.md  # 전자서명/본인확인/웹트러스트 라이선스 심사 기준 및 체크리스트
├── backend/                         # 인증 API 서버, PKI 엔진, AI 컴플라이언스 AX 엔진
└── frontend/                        # 제휴사 포털 사이트 & 라이선스 관리 AX 대시보드
```

---

## 🛠️ 공통 작업 원칙 (General Guidelines)
1. **컴플라이언스 우선 설계 (Compliance-by-Design)**: 모든 기능과 API는 전자서명법, 정보통신망법(본인확인기관), 전자금융거래법, 개인정보보호법 요건(암호화, 접근통제, 감사로그, 연계정보 CI/중복가입확인정보 DI 안전성)을 준수하여 기획·개발합니다.
2. **문서화의 명확성 (Technical Writing Excellence)**: 모든 API와 프로세스는 제휴사 개발자와 라이선스 심사원이 즉시 이해할 수 있도록 시퀀스 다이어그램, 에러 코드표, 요청/응답 명세를 포함해 문서화합니다.
3. **실행 가능한 AX (Actionable AI Transformation)**: 단순 개념 제시가 아닌, 실제 법령/심사 기준 분석 자동화, 제휴사 기술지원 Q&A 챗봇, API 연동 코드/매뉴얼 자동 생성 등 실질적인 업무 효율화(AX) 기능을 구현합니다.
