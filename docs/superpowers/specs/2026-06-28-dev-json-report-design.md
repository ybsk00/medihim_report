# DEV 전용 JSON 리포트 제공 — 설계 문서

- 작성일: 2026-06-28
- 작성자: 유범석 + Claude
- 상태: 설계 확정 (DEV 구현 → 테스트 → 운영 반영 순)

## 1. 배경 / 목적

메디힘(이뻐) 개발사가 변경되었다. 새 개발사는 기존 아이프레임(iframe) 임베드 대신,
**리포트 내용을 JSON으로 받아 자체 디자인을 입혀 렌더링하고, 내용도 수작업으로 수정**하기를 원한다.

- **운영(PROD)은 현행 아이프레임 그대로 유지** — 일절 변경 없음.
- **개발(DEV) 콜백에만** JSON 파일 URL을 추가 제공한다.
- 안전을 위해 기존 `embed_url`(아이프레임)도 **그대로 남겨둔다** → 새 개발사가 헤매면 아이프레임으로 폴백 가능.
- **웹훅 통신 자체는 불변** — 콜백 엔드포인트/인증(API Key·HMAC)/키(`patient_report`·`doctor_report`)/재시도 모두 그대로.

## 2. 비목표 (YAGNI)

- PROD 콜백 페이로드 변경 — 하지 않는다.
- 아이프레임 페이지/컴포넌트 변경 — 하지 않는다.
- 신규 인증 체계 — 기존 토큰 기반 그대로.
- DB 스키마 변경 — 없음. 기존 `reports.report_data` / `report_data_ko`를 변환만 한다.

## 3. 전체 흐름

```
파이프라인 완료 → notify_report_ready()
  ├─ PROD 콜백: { ..., patient_report: { report_token, embed_url } }          (현행 그대로)
  └─ DEV  콜백: { ..., patient_report: { report_token, embed_url, json_url } } (json_url만 추가)

새 개발사: json_url(ja/ko) GET
  → GET /api/dev/report/{lang}/{token}.json
  → reports.report_data(또는 report_data_ko) 조회
  → 디자인용 블록 JSON으로 변환 후 반환
  → 개발사가 blocks를 순회하며 디자인 입힘 + 수작업 수정
```

## 4. 콜백 변경 (`backend/services/ippeo_callback.py`)

현재 `notify_report_ready`는 PROD/DEV에 **동일 payload**를 보낸다. 이를 **목적지별로 분리**한다.

- 공통 payload(현행)를 만든 뒤, **DEV 목적지에 한해** 각 리포트 항목에 `json_url`을 추가한 변형 payload를 생성한다.
- `json_url`은 `embed_url`과 같은 위치(`patient_report`/`doctor_report` 안)에 형제 키로 들어간다.
- PROD payload에는 `json_url`을 절대 넣지 않는다.

```jsonc
// DEV 콜백 — patient_report (R4) 예시
"patient_report": {
  "report_token": "abc123",
  "embed_url": { "ja": "{FRONTEND_URL}/embed/patient/ja/abc123",
                 "ko": "{FRONTEND_URL}/embed/patient/ko/abc123" },   // 유지
  "json_url":  { "ja": "{FRONTEND_URL}/api/dev/report/ja/abc123.json",
                 "ko": "{FRONTEND_URL}/api/dev/report/ko/abc123.json" }  // 추가
}
// doctor_report (R3) 는 ko 만:
"json_url": { "ko": "{FRONTEND_URL}/api/dev/report/ko/abc123.json" }
```

> 구현 메모: `_send_to_all`을 (label, url, payload) 단위로 받도록 바꾸거나,
> PROD용/DEV용 payload 2벌을 만들어 각각 전송. 폴백 토큰 승계 로직(규칙 25)은 변경 없이 그대로 동작.

## 5. 신규 엔드포인트 (`backend/api/dev_report.py`)

```
GET /api/dev/report/{lang}/{token}.json     (lang = ja | ko)
```

- 동작: `reports`에서 `access_token == token` 조회 → `report_type` 확인 → `report_data`(ko면 `report_data_ko` 우선) 선택 → 변환 함수로 블록 JSON 생성 후 반환.
- 상태 제약: 기존 embed와 동일하게 `status in (draft, approved, sent)` 허용(승인 전 미리보기 가능).
- 없는 토큰 → 404. 미허용 상태 → 403.
- 열람 추적(`email_opened_at`)은 **갱신하지 않는다**(개발사 디자인 작업용 호출이므로 고객 열람과 구분).
- `main.py`에 라우터 등록.

## 6. 변환 함수 (`backend/services/dev_report_format.py`)

```python
def to_design_blocks(report_data: dict, report_type: str,
                     customer_name: str, consultation_round: int, lang: str) -> dict
```

반환 형태:

```json
{
  "meta": {
    "이름": "田中様",
    "리포트종류": "고객용",          // r4=고객용, r3=병원용
    "회차": 3,
    "역할라벨": "상담실장",          // r3: 2차=의사, 그 외=상담실장. r4=null
    "언어": "ja",
    "리포트제목": "...",            // report_data.title
    "날짜": "..."                   // report_data.date
  },
  "blocks": [ { "구분": "...", ... }, ... ]
}
```

### 블록 구분자(`구분`) 고정 어휘 — 6종

| 구분 | 의미 | 필드 |
|------|------|------|
| `큰제목` | 리포트 최상단 제목 | `내용`: 문자열 |
| `섹션제목` | 소제목(섹션 헤더) | `내용`: 문자열, `섹션키`: 원본 키 |
| `본문` | 문단 텍스트 | `내용`: 문자열 |
| `리스트` | 불릿 목록 | `내용`: 문자열 배열 |
| `항목` | 라벨-값 쌍(비용/회복기간 등) | `라벨`: 문자열, `값`: 문자열 |
| `주석` | 비고·면책·보충 문구 | `내용`: 문자열 |

- 값이 비었거나 `null`인 항목은 블록을 생성하지 않는다(빈 블록 금지).
- `섹션제목`의 표시 텍스트는 원본 `report_data`에 없으므로(프론트 컴포넌트에 하드코딩되어 있음)
  **변환 함수가 보유한 제목 사전**에서 가져온다(아래 7·8절).

## 7. R4(고객용) 섹션 → 블록 매핑

`섹션제목` 텍스트 사전(ja / ko):

| 섹션키 | ja | ko |
|--------|----|----|
| section1_key_summary | ご相談の要点 | 핵심 요약 |
| section2_cause_analysis | 原因・背景の分析 | 원인 분석 |
| section3_recommendation | おすすめの方向性 | 추천 방향 |
| section4_recovery | 回復について | 회복 정보 |
| section5_scar_info | 傷跡について | 흉터 정보 |
| section6_precautions | 施術前後の注意点 | 시술 전후 주의점 |
| section7_risks | リスクについて | 리스크 |
| section8_cost_estimate | 費用の目安 | 예상 비용 |
| section9_visit_date | ご来院の目安 | 내원 일정 |
| section10_ippeo_message | イッポからのメッセージ | 이뻐 메시지 |

블록 생성 규칙:

- `title` → `큰제목`
- section1: `섹션제목` + `리스트`(points)
- section2: `섹션제목` + `본문`(intro) + `리스트`(causes) + `본문`(conclusion)
- section3: `섹션제목` + `본문`(primary.label 있으면) + `리스트`(primary.items) + `본문`(secondary.label) + `리스트`(secondary.items) + `본문`(goal)
- section4: `섹션제목` + `항목`×N(timeline: period→라벨, detail→값) + `주석`(note)
- section5/6/7: `섹션제목` + `리스트`(points)
- section8: `섹션제목` + `리스트`(items) + `주석`(includes) + `주석`(note)
- section9: `섹션제목` + `본문`(date) + `주석`(note)
- section10: `섹션제목` + `본문`×N(paragraphs) + `본문`(final_summary)
- `hospital_comparison`(있으면): 본 설계 범위에서는 생략(YAGNI). 필요 시 후속 확장.

## 8. R3(병원용/한국어) 섹션 → 블록 매핑

`섹션제목` 텍스트 사전(ko 고정):

| 섹션키 | 제목 |
|--------|------|
| section1_consultation_summary | 상담 요약 |
| section2_procedure_plan | 시술 계획 |
| section3_cost_estimate | 비용 견적 |
| section4_scheduling | 일정 |
| section5_considerations | 고려사항 |
| section6_action_items | 액션 아이템 |
| section7_voice_analysis | 음성 분석 |

블록 생성 규칙:

- `title` → `큰제목`
- section1: `섹션제목` + `항목`(분류=classification) + `항목`(CTA=cta_level) + `본문`(round_summary)
- section2: `섹션제목` + (primary_procedures: `항목`×N {name→라벨, description→값}) + (additional_options: `항목`×N)
- section3: `섹션제목` + `항목`×N(items: procedure→라벨, estimated_cost→값) + `리스트`(package_options) + `항목`(총 예상=total_estimate) + `주석`(note)
- section4: `섹션제목` + `항목`(희망일=preferred_date) + `본문`(treatment_timeline) + `리스트`(follow_up_plan)
- section5: `섹션제목` + `리스트`(patient_concerns) + `리스트`(negotiation_points) + `본문`(risk_communication)
- section6: `섹션제목` + `리스트`(before_visit) + `리스트`(during_consultation) + `리스트`(after_consultation)
- section7(있으면): `섹션제목` + 음성 분석 핵심을 `본문`/`항목`으로 요약(emotional_state.summary, voice_cta.level 등)

> R3는 한국어 단일이므로 `json_url`도 `ko`만 제공. `lang=ja` 요청이 와도 R3는 한국어 데이터를 반환.

## 9. 안전성 / 운영 무해 보장

- PROD 콜백 payload는 바이트 단위로 현행과 동일(분기 전 공통 payload를 그대로 사용).
- 신규 엔드포인트는 **추가만** 하므로 기존 API에 영향 없음.
- 변환 함수는 `report_data`를 **읽기 전용**으로 다룬다(DB 미변경).
- 누락 키/폴백 리포트에도 죽지 않도록 모든 섹션 접근을 방어적으로(`.get`, 빈 값 스킵) 처리.

## 10. 테스트

- 단위 테스트(`test_dev_report_format.py`): R4·R3 샘플 `report_data`를 넣어
  - 블록 `구분`이 6종 어휘만 사용하는지
  - 빈/누락 섹션이 블록을 만들지 않는지
  - meta 필드(이름/리포트종류/회차/언어)가 올바른지
  - ko 요청 시 R4 제목 사전이 한국어로 나오는지
- DEV 통합 테스트: 실제 토큰으로 `GET /api/dev/report/ja/{token}.json` 호출 → 블록 구조 육안 확인.

## 11. 산출물

1. `backend/services/dev_report_format.py` — 변환 함수
2. `backend/api/dev_report.py` — 엔드포인트 + `main.py` 등록
3. `backend/services/ippeo_callback.py` — DEV payload에 `json_url` 추가
4. `test_dev_report_format.py` — 단위 테스트
5. **개발사용 구현 매뉴얼**(`docs/dev-handoff/ippeo-json-report-manual.md`) — JSON 스키마/구분자/렌더링 예시
6. (배포) DEV 검증 후 사용자 지시 시 운영 Cloud Run 반영
