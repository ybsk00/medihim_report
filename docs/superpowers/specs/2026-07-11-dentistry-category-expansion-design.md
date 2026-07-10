# 치과(dentistry) 카테고리 확장 — 설계 문서

- 작성일: 2026-07-11
- 작성자: 유범석 + Claude
- 상태: 설계 승인 대기
- 관련: CLAUDE.md "다음 작업 — 치과 카테고리 확장", 규칙 20·25·28

## 1. 목표

일본 의료관광 플랫폼 이뻐(IPPEO)의 AI 상담 리포트 시스템에 **치과(dentistry)** 카테고리를
기존 피부과(dermatology)/성형외과(plastic_surgery)와 **동일한 로직**으로 추가한다.

- 의도 파악/분류 에이전트가 치과 상담을 인지 → RAG DB에서 치과 데이터 검색 → 동일 포맷 리포트(R3+R4) 생성 → 웹훅으로 메디힘 서버 전송
- RAG DB는 **PubMed 논문 전용**으로 구축, 목표 **2,500~3,000 FAQ 벡터**
- 실제 DB 연동 리포트 생성 + 메디힘 웹훅 통신/데이터 연동 테스트까지 완료 후 보고

## 2. 핵심 원칙 (절대 준수)

1. **순수 가산적(additive) 확장** — 기존 피부과/성형외과 동작 100% 무영향.
2. **리포트 출력 JSON 키 구조 100% 불변** — 치과는 값(내용)만 다르고 키는 그대로.
3. **이뻐 콜백 키/URL/status 불변** — `doctor_report`(R3)/`patient_report`(R4)/`embed_url`/`json_url` 구조 변경 금지.
4. 경계 시술 오분류 방지가 핵심 리스크.

## 3. 코드 영향 분석 (조사 완료)

### 3-1. 카테고리를 실제로 다루는 곳 → 치과 추가 필요

| 위치 | 현재 상태 | 변경 |
|------|-----------|------|
| `supabase/migrations/001_initial_schema.sql` CHECK 제약 | `consultations.classification`, `faq_vectors.category`, `youtube_sources.category`, `classification_keywords.category` = 2~3종만 허용 | 신규 마이그레이션 011로 `'dentistry'` 추가 |
| `backend/agents/classifier.py` | 피부/성형 2분류 하드코딩 프롬프트 | 3분류 + 치과 키워드 노출 + 경계규칙 3종 |
| `backend/agents/validator.py` | 프롬프트에 2종만 명시 | dentistry 추가 |
| `backend/agents/report_writer.py` (R4) | `category_note` 2분기 (line 78-82) | 치과 분기 추가(치료 단계 중심) |
| `backend/agents/r3_director_writer.py` (R3) | `category_label` 2분기 (line 60) | 치과 라벨("치과") |
| `backend/agents/pipeline.py` | 폴백 빌더 `category_ko/ja` 2분기, unclassified 기본값 "plastic_surgery" | 치과 라벨 대응 |
| `backend/scripts/build_pubmed_vectors.py` | 34개 쿼리(피부18+성형16) | `DENTISTRY_QUERIES` 세트 추가 |
| 치과 키워드 seed | 없음 | 명확 키워드 + 경계 규칙 seed SQL |

### 3-2. 완전히 카테고리 무관 → 변경 없음 (확인 완료)

- `backend/agents/rag_agent.py` — category 파라미터를 그대로 `search_faq` RPC에 전달. ✓
- `search_faq` RPC (`004_update_search_faq.sql`) — `target_category` 파라미터 방식. ✓
- `backend/agents/report_reviewer.py` — 카테고리 문자열 미참조, 타입(r3/r4)별 검토만. ✓
- **`backend/services/ippeo_callback.py`** — 리포트 토큰만 payload에 담음. 치과 리포트도 자동으로 동일 구조 발신. **코드 수정 0.** ✓
- `backend/services/dev_report_format.py` — report_data 구조 기반 변환, 카테고리 무관. ✓
- `reports` 테이블 — category CHECK 없음(report_type만 존재). ✓

## 4. 테스트 환경 — Supabase 개발 브랜치

운영 `medihim_report`(`vkwdkjwiriqujfzjpxlp`)를 **불변**으로 두기 위해, copy-on-write 개발 브랜치를
생성하여 그 위에서 벡터 빌드 + end-to-end 검증을 수행한다.

- 브랜치는 운영 스키마 + 기존 4,784 벡터 + `search_faq` RPC를 정확히 복제 → 회귀 테스트까지 완벽 재현.
- 백엔드 `config.py`가 읽는 `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`를 브랜치 값으로 임시 지정하여
  로컬에서 파이프라인 실행.
- 검증 완료 후 브랜치 삭제.

### 배포 시 운영 반영 전략 (검증 후 함께)

브랜치에서 임베딩까지 끝난 치과 벡터를 운영에서 **재계산 없이 rows 복사**:

1. 운영에 마이그레이션 011 적용(CHECK에 dentistry 추가).
2. 운영에 치과 키워드 seed SQL 적용.
3. 브랜치의 `faq_vectors` 중 `category='dentistry'` rows를 운영 `faq_vectors`로 복사(임베딩 포함, 재계산 불필요 → 빠름).
4. 코드 배포 `--no-traffic --tag` → 태그 URL 검증 → `update-traffic --to-latest`.
5. 롤백: `update-traffic --to-revisions <이전리비전>=100`.

## 5. RAG 벡터DB 구축 (PubMed 전용)

### 5-1. 쿼리 세트

`DENTISTRY_QUERIES`를 6개 영역으로 균형 있게 구성(약 40개 쿼리):

1. **임플란트** — implant survival/osseointegration/immediate loading/all-on-4/sinus lift
2. **교정** — orthodontics/clear aligner(Invisalign)/lingual/self-ligating/TAD
3. **심미(라미네이트/미백/크라운)** — laminate veneer/ceramic crown/teeth whitening/digital smile design
4. **보존(신경치료/충치)** — root canal/endodontic/composite resin/inlay onlay
5. **치주** — periodontal/scaling root planing/gum graft/regeneration
6. **구강외과** — wisdom tooth extraction/impacted third molar/TMJ/orthognathic(교합 맥락)

- 각 쿼리 `retmax=35~40`, `mindate=2015 maxdate=2025`, sort=relevance → 논문 ~1,000편.
- FAQ 2~4개/편 → **2,500~3,000 FAQ 벡터** 목표.

### 5-2. 파이프라인 (기존 재사용)

기존 3단계(`--step 1` 수집 → `--step 2` Gemini FAQ 변환 → `--step 3` 임베딩) 그대로 사용.
- `category='dentistry'`, `youtube_url=https://pubmed.ncbi.nlm.nih.gov/{pmid}/` 로 저장(기존 PubMed 구분 패턴).
- **FAQ 본문은 기존과 동일하게 한국어로 유지**(피부/성형과 일관). build 스크립트 FAQ 프롬프트의 "영어 시술명 → 한국어 변환" 규칙에 치과 용어를 추가: implant→임플란트, root canal→신경치료, ceramic crown→세라믹 크라운, orthodontics→치아교정, teeth whitening→치아미백, periodontal→치주치료 등.
- **일본어 치과 용어**(インプラント/根管治療/セラミック 등)는 R4 writer의 치과 서브템플릿에서 처리(7절). build 스크립트/저장 벡터에는 일본어 미포함.

### 5-3. 실행 방식

- Gemini 15 RPM(무료 tier) 병목: article당 5초 sleep → ~1,000편 = 최소 1.4h, 429 백오프 포함 수 시간.
- **백그라운드 실행** + 진행률 로깅. 단계별 재시작 가능(기존 스크립트 지원).

## 6. 분류 로직 상세

### 6-1. 치과 명확 키워드 (seed)

임플란트, 치아교정(교정), 투명교정, 라미네이트, 크라운, 신경치료, 충치치료, 스케일링,
치주치료(잇몸치료), 치아미백, 사랑니, 발치, 틀니, 브릿지, 턱관절, 부정교합

### 6-2. 경계 시술 규칙 (오분류 방지 — 핵심)

| 시술 | 치과로 분류 | 타과로 분류 |
|------|-------------|-------------|
| 양악수술 | 교합/저작/부정교합 기능 맥락 → **치과(구강외과)** | 얼굴 윤곽/심미 맥락 → 성형외과 |
| 미백 | "치아 미백" 맥락 동반 → **치과** | 피부 미백/톤 → 피부과 |
| 보톡스 | 이갈이(bruxism)/사각턱 저작근 치료 맥락 → **치과** | 주름/피부 → 피부과, 윤곽 → 성형외과 |

classifier.py 프롬프트에 3분류 + 위 규칙을 명시. validator.py도 dentistry 인지하도록 프롬프트 수정.

## 7. 서브 템플릿 (치과)

- 성형외과 = 구조적 접근, 피부과 = 치료 프로토콜, **치과 = 치료 단계·통원 횟수·재료 선택지** 중심.
- R4(일본어): `category_note`에 "歯科の相談です。治療ステップ・通院回数・材料の選択肢を中心に記述してください。"
- R3(한국어): `category_label = "치과"`.
- 일본어 치과 용어 표기 기준: インプラント / 根管治療 / セラミック / 矯正 / ホワイトニング / 歯周治療.

## 8. End-to-End 테스트 계획

브랜치 DB + DEV 콜백으로 수행:

1. **치과 상담 샘플** 준비(임플란트/교정/심미 각 1건, 일본어 또는 한국어).
2. 파이프라인 실행 → `classification == 'dentistry'` 확인.
3. RAG가 **치과 벡터만** 반환하는지 확인(카테고리 필터 격리 검증).
4. R3(치과 상담실장, 6섹션)+R4(일본어 고객, 10섹션) 생성 + **JSON 키 구조 불변** 확인.
5. `notify_report_ready`로 **DEV 콜백 실전송** → payload에 `doctor_report`/`patient_report`/`embed_url`/`json_url` 키 정상 + 200 응답 확인.
6. **회귀 테스트**: 피부과·성형외과 샘플 각 1건 정상 생성 + 콜백 확인.
7. 경계 케이스: "양악(저작 기능)" → 치과, "양악(윤곽)" → 성형 분류 확인.

## 9. 배포 (검증 후 함께)

7절 검증 통과 후 4절 "배포 시 운영 반영 전략" 실행. 배포 시점은 최종 승인 후.

## 10. 범위 밖 (이번 작업 제외)

- 프론트엔드 관리자페이지 치과 배지/필터/수동분류 버튼 — 사용자 지정 범위(파이프라인+RAG+리포트+웹훅)에 미포함. 별도 후속 작업.
- YouTube 치과 벡터 — 이번엔 PubMed 전용(사용자 지시).

## 11. 완료 기준

- [ ] 마이그레이션 011 + 치과 키워드 seed 작성
- [ ] 8개 파일 코드 변경(값 추가, JSON 키 불변)
- [ ] 치과 벡터 2,500~3,000 구축(브랜치)
- [ ] end-to-end 테스트 6단계 + 회귀 통과
- [ ] DEV 콜백 200 확인
- [ ] 배포(최종 승인 후) + 운영 검증
