# PubMed → 벡터DB 작업지시서

## 목적
YouTube 자막 데이터의 한계를 보완하여, 피부과 미용시술 및 성형외과 수술별 **효과·만족도에 대한 임상 근거**를 벡터DB에 추가

---

## 파이프라인

```
PubMed API (ESearch/EFetch) → 논문 제목+초록 수집 → Gemini로 한국어 FAQ 변환 → Gemini Embedding → pgvector 저장
```

- 기존 YouTube FAQ와 **같은 테이블**, `source='pubmed'`로 구분
- PubMed API: 무료, API키 있으면 10req/sec

---

## 검색 쿼리 — 피부과 미용시술 (18개)

| # | 카테고리 | 검색 키워드 (AND efficacy/satisfaction) |
|---|---------|---------------------------------------|
| 1 | 보톡스(주름) | botulinum toxin + forehead/glabellar/crow |
| 2 | 보톡스(사각턱) | botulinum toxin + masseter/jaw reduction/facial slimming |
| 3 | 보톡스(목주름) | botulinum toxin + platysma/neck band/nefertiti |
| 4 | 필러(팔자주름) | hyaluronic acid filler + nasolabial/marionette |
| 5 | 필러(볼/턱) | dermal filler + cheek/chin augmentation/midface volume |
| 6 | 필러(입술) | lip filler/lip augmentation + hyaluronic acid |
| 7 | 필러(눈밑) | tear trough/under eye filler/infraorbital hollow |
| 8 | 울쎄라(HIFU) | HIFU/Ultherapy + face lift/skin tightening |
| 9 | 써마지(RF) | radiofrequency/Thermage + skin tightening |
| 10 | 실리프팅 | thread lift/PDO thread + facial rejuvenation |
| 11 | 피코레이저(색소) | picosecond laser + pigmentation/melasma |
| 12 | 프락셀(흉터) | fractional laser/CO2 + acne scar/resurfacing |
| 13 | IPL(홍조) | IPL/intense pulsed light + rosacea/facial redness |
| 14 | 레이저토닝(기미) | laser toning/low-fluence Nd:YAG + melasma + Asian |
| 15 | 스킨부스터(리쥬란) | skin booster/polynucleotide/PDRN/Rejuran |
| 16 | 스컬트라 | poly-L-lactic acid/Sculptra/collagen stimulator |
| 17 | 엑소좀/PRP | exosome/growth factor/PRP + skin rejuvenation |
| 18 | 레이저제모 | laser hair removal/diode/alexandrite |

## 검색 쿼리 — 성형외과 수술 (16개)

| # | 카테고리 | 검색 키워드 (AND satisfaction/outcome) |
|---|---------|--------------------------------------|
| 1 | 쌍꺼풀 | double eyelid/blepharoplasty + Asian |
| 2 | 눈매교정 | ptosis correction/levator + aesthetic |
| 3 | 눈밑지방재배치 | lower blepharoplasty/fat repositioning |
| 4 | 트임(앞트임/뒤트임) | epicanthoplasty/canthoplasty + Asian |
| 5 | 코성형(아시안) | rhinoplasty + Asian/augmentation + silicone/cartilage |
| 6 | 코재수술 | revision rhinoplasty + complication rate |
| 7 | 코끝/콧볼 | nasal tip/tip plasty/alar reduction + Asian |
| 8 | 사각턱축소 | mandible reduction/V-line + Korean/Asian |
| 9 | 광대축소 | zygoma reduction/malar reduction + Korean |
| 10 | 턱끝수술 | genioplasty/chin surgery/sliding + aesthetic |
| 11 | 양악수술 | orthognathic/bimaxillary/two-jaw + aesthetic + Korean |
| 12 | 안면거상 | facelift/rhytidectomy/SMAS + satisfaction |
| 13 | 이마거상 | forehead lift/brow lift/endoscopic |
| 14 | 지방이식(얼굴) | fat grafting/lipofilling + face + survival rate |
| 15 | 지방흡입 | liposuction/body contouring + aesthetic |
| 16 | 가슴확대 | breast augmentation + implant/satisfaction/QoL |

---

## 수집 조건

- 기간: 2015~2025 (최근 10년)
- 정렬: relevance
- 쿼리당 최대: 30건
- 초록 없는 논문은 스킵
- 중복 PMID 제거

---

## FAQ 변환 지침 (Gemini 프롬프트 핵심)

- 논문 1건당 Q&A **2~4개** 생성
- 질문에 **시술명 포함** ("울쎄라 효과가 있나요?")
- 답변에 **구체적 수치 필수** (만족도 %, 효과 수치, 지속기간, 부작용률)
- 답변 끝에 `(출처: 저널명, 년도)` 표기
- 부작용/주의사항 언급된 경우 반드시 포함
- 영어 시술명 → 한국어 변환 (HIFU → 울쎄라, botulinum toxin → 보톡스 등)

---

## 예상 규모

| 항목 | 수량 |
|------|------|
| 검색 카테고리 | 34개 |
| 총 논문 (중복 제거 후) | 400~600건 |
| 총 FAQ | **1,000~2,000개** |
| 소요 시간 (Gemini 무료) | 약 5~8시간 |

---

## 주의사항

1. Gemini 무료 15RPM → `time.sleep(5)` + 429 재시도 필수
2. YouTube 파이프라인과 같은 Gemini 키 → **순차 실행**
3. 리포트 출력 시 YouTube/PubMed 소스 구분하여 "시술 설명 + 임상 근거" 조합
4. 논문 초록은 공개 데이터이나, 리포트에 인용 시 출처 표기 필수
