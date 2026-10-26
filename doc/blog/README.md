# 📝 기술 블로그 & 엔지니어링 노트 (`doc/blog/`)

카카오뱅크 인증센터팀(본인확인기관 · 전자서명인증사업자 · 웹트러스트 인증) 타겟 프로젝트를 기획하고 개발하면서 마주한 **도메인/컴플라이언스 해석 이슈, 아키텍처 설계 의사결정, 암호화/PKI 구현 기법, 그리고 AI 기반 업무 자동화(AX) 트러블슈팅 과정**을 기록한 기술 블로그 시리즈입니다.

---

## 📚 시리즈 목차 (Tech Blog Series)

| 순서 | 문서 경로 | 핵심 주제 (기술 · 기법 · 이슈) | 담당 에이전트 |
| :---: | :--- | :--- | :---: |
| **01** | [`01_architecture_and_compliance_by_design.md`](./01_architecture_and_compliance_by_design.md) | **[기획 & 아키텍처]** 전자서명법·본인확인기관·웹트러스트 규제를 시스템 요구사항으로 변환하는 Compliance-by-Design 기법과 상태 머신 설계 이슈 해결 | 기획 + 개발 |
| **02** | [`02_pki_x509_ocsp_and_ci_di_engineering.md`](./02_pki_x509_ocsp_and_ci_di_engineering.md) | **[PKI & 암호화 기법]** X.509 3-Tier 인증서 체인(Root-Intermediate-Leaf) 구현, 실시간 OCSP/CRL 폐지 검증, HMAC-SHA256 기반 CI(88B)/DI(64B) 생성 이슈와 해결 | 개발 |
| **03** | [`03_partner_api_gateway_and_hash_chain_audit.md`](./03_partner_api_gateway_and_hash_chain_audit.md) | **[제휴사 API & 보안 감사]** 제휴사 API 게이트웨이 설계, Replay Attack 방지(Nonce/TTL) 기법, 라이선스 심사 증적을 위한 Hash-Chain 기반 무결성 감사 로그 구현 이슈 | 기획 + 개발 |
| **04** | [`04_ai_transformation_ax_for_license_audit.md`](./04_ai_transformation_ax_for_license_audit.md) | **[AI 전환 (AX) 기법]** 수백 페이지의 법령·인증업무준칙(CPS)·라이선스 심사 기준을 자동 점검하는 Compliance AX 엔진 및 제휴사 기술지원 AI 어시스턴트 구현기 | 기획 + 개발 |

---

## ✍️ 기술 블로그 작성 템플릿 원칙 (Blogging Standard)
모든 포스트는 채용 면접관과 실무 엔지니어가 읽었을 때 **"실제 문제를 깊이 있게 고민하고 기술적으로 해결할 줄 아는 지원자"**임을 직관적으로 느낄 수 있도록 다음 5단계 구조로 작성합니다.

1. **Why (배경 및 컴플라이언스/비즈니스 문제 정의)**: 왜 이 기능/정책이 인증센터에 필수적인가? 관련 법령(전자서명법, 정보통신망법, 전자금융거래법, WebTrust) 요건은 무엇인가?
2. **Issue & Challenge (개발/기획 과정에서 마주한 이슈)**: 단순 구현 시 발생하는 보안 취약점, 성능 병목, 규제 미충족, 제휴사 연동 불편함 등의 구체적 문제 상황.
3. **Alternatives & Trade-off (기술 대안 비교 및 의사결정)**: A 방식 vs B 방식의 장단점 비교 표 및 현재 아키텍처를 선택한 근거.
4. **How & Deep Dive (핵심 적용 기술 및 엔지니어링 기법)**: 다이어그램, 암호화 수식/규격, 실제 핵심 코드 스니펫을 통한 구체적인 해결 과정.
5. **Result & Retrospective (검증 결과 및 인사이트)**: 테스트 검증 결과, 라이선스 심사 대응 효과, 향후 고도화 방향.
