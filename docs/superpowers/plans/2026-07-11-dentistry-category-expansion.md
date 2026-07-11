# 치과(dentistry) 카테고리 확장 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 피부과/성형외과와 동일한 로직으로 치과(dentistry) 카테고리를 추가하여, 분류→RAG(PubMed 벡터)→R3+R4 리포트 생성→이뻐 웹훅 전송까지 동작하게 한다.

**Architecture:** 카테고리는 값만 추가되는 순수 가산적 확장. DB CHECK 제약·분류/검증 프롬프트·R3/R4 writer 서브템플릿·PubMed 쿼리 세트에 치과를 더하고, RAG/콜백/리뷰어는 이미 카테고리 무관이라 수정하지 않는다. 검증은 운영 무영향의 Supabase 개발 브랜치에서, 콜백은 DEV로만.

**Tech Stack:** Python 3.13, FastAPI, Supabase(PostgreSQL+pgvector), Gemini(LLM+임베딩), PubMed(Entrez/Biopython), httpx.

## Global Constraints

- 리포트 출력 **JSON 키 구조 100% 불변** — 치과는 값만 다르고 키는 그대로.
- 이뻐 콜백 키(`doctor_report`/`patient_report`) · `embed_url` · `json_url` · `status` **변경 금지**. 치과는 **가산적**일 것.
- 기존 피부과/성형외과 동작 **100% 무영향**.
- 경계 규칙은 **치아미백 1종만** 추가. 양악·보톡스는 손대지 않음(기존 성형/피부 유지).
- 벡터 RAG는 **PubMed 전용**. 목표 치과 **2,500~3,000 FAQ**.
- 운영 `medihim_report`(`vkwdkjwiriqujfzjpxlp`)는 검증 완료 전까지 **불변**. 테스트는 개발 브랜치에서.
- 콜백 실전송은 **DEV만**(PROD 라이브 메디힘에 테스트 데이터 유입 금지).
- 테스트는 프로젝트 관례를 따른다: 루트에 `test_*.py`, 상단 `sys.path.insert(0, "backend")`, `python test_*.py`로 실행, assert 기반.
- 시술명/카테고리 문자열 리터럴: `dermatology` / `plastic_surgery` / `dentistry`(신규). 한국어 라벨 `피부과` / `성형외과` / `치과`. 일본어 `皮膚科` / `整形外科` / `歯科`.

---

## File Structure

**생성:**
- `supabase/migrations/011_dentistry_category.sql` — 5개 CHECK 제약에 dentistry 추가 + 치과 키워드 seed(경계 미백 포함)
- `test_dentistry_prompts.py` — 분류/검증/writer 프롬프트에 치과 반영 여부 단위 검증(DB·LLM 무관)
- `test_dentistry_e2e.py` — 브랜치 DB 대상 end-to-end + 회귀(분류→RAG→R3/R4→DEV 콜백)

**수정:**
- `backend/agents/classifier.py` — 2분류→3분류 프롬프트 + 치과 키워드/미백 경계 규칙
- `backend/agents/validator.py` — dentistry 인지
- `backend/agents/report_writer.py:78-82` — R4 `category_note` 치과 분기
- `backend/agents/r3_director_writer.py:60` — R3 `category_label` 치과
- `backend/agents/pipeline.py` — 폴백 빌더 3곳 `category_ko/ja` 치과 대응
- `backend/scripts/build_pubmed_vectors.py` — `DENTISTRY_QUERIES` + FAQ 프롬프트 치과 용어 변환

**변경 없음(확인 완료):** `rag_agent.py`, `search_faq` RPC, `report_reviewer.py`, `services/ippeo_callback.py`, `services/dev_report_format.py`.

---

### Task 1: DB 마이그레이션 011 (dentistry CHECK + 치과 키워드 seed)

**Files:**
- Create: `supabase/migrations/011_dentistry_category.sql`

**Interfaces:**
- Produces: `consultations.classification`, `faq_vectors.category`, `youtube_sources.category`, `classification_keywords.category` CHECK 제약이 `'dentistry'`를 허용. `classification_keywords`에 치과 명확 키워드 16종 + 경계 미백 1종(context_keywords JSON) seed.

- [ ] **Step 1: 마이그레이션 SQL 작성**

`supabase/migrations/011_dentistry_category.sql`:

```sql
-- ============================================
-- 011: 치과(dentistry) 카테고리 확장
-- ============================================
-- 5개 CHECK 제약에 'dentistry' 추가 (가산적, 기존 값 무영향)
-- + 치과 명확 키워드 + 경계 미백 규칙 seed
-- search_faq RPC는 category 파라미터 방식이라 변경 불필요.

-- 1. consultations.classification
ALTER TABLE consultations DROP CONSTRAINT IF EXISTS consultations_classification_check;
ALTER TABLE consultations ADD CONSTRAINT consultations_classification_check
  CHECK (classification IN ('dermatology', 'plastic_surgery', 'dentistry', 'unclassified'));

-- 2. faq_vectors.category
ALTER TABLE faq_vectors DROP CONSTRAINT IF EXISTS faq_vectors_category_check;
ALTER TABLE faq_vectors ADD CONSTRAINT faq_vectors_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry'));

-- 3. youtube_sources.category
ALTER TABLE youtube_sources DROP CONSTRAINT IF EXISTS youtube_sources_category_check;
ALTER TABLE youtube_sources ADD CONSTRAINT youtube_sources_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry'));

-- 4. classification_keywords.category
ALTER TABLE classification_keywords DROP CONSTRAINT IF EXISTS classification_keywords_category_check;
ALTER TABLE classification_keywords ADD CONSTRAINT classification_keywords_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry', 'boundary'));

-- 5. 치과 명확 키워드 seed
INSERT INTO classification_keywords (category, keyword) VALUES
('dentistry', '임플란트'),
('dentistry', '치아교정'),
('dentistry', '투명교정'),
('dentistry', '라미네이트'),
('dentistry', '크라운'),
('dentistry', '신경치료'),
('dentistry', '충치치료'),
('dentistry', '스케일링'),
('dentistry', '치주치료'),
('dentistry', '잇몸치료'),
('dentistry', '치아미백'),
('dentistry', '사랑니'),
('dentistry', '발치'),
('dentistry', '틀니'),
('dentistry', '브릿지'),
('dentistry', '부정교합');

-- 6. 경계 규칙: 미백 (치아 맥락 → 치과, 피부 맥락 → 피부과)
INSERT INTO classification_keywords (category, keyword, context_keywords) VALUES
('boundary', '미백', '{"dentistry": ["치아", "잇몸", "구강", "치아미백", "누런 치아"], "dermatology": ["피부", "톤", "잡티", "색소", "피부톤"]}');
```

- [ ] **Step 2: 개발 브랜치 생성 + 브랜치에 마이그레이션 적용**

Supabase MCP로 `medihim_report`(`vkwdkjwiriqujfzjpxlp`)의 개발 브랜치를 생성한다(cost confirm 필요). 브랜치 ref를 `BRANCH_REF`로 기록.

- `mcp__supabase__create_branch`(project_id=`vkwdkjwiriqujfzjpxlp`, name=`dentistry-test`) → confirm_cost 후 생성.
- 브랜치는 운영 스키마 001~010 + 기존 4,784 벡터 + `search_faq` RPC를 복제한다.
- `mcp__supabase__apply_migration`(project_id=`BRANCH_REF`, name=`011_dentistry_category`, query=위 SQL) 적용.

- [ ] **Step 3: 브랜치에서 CHECK 제약 + seed 검증**

`mcp__supabase__execute_sql`(project_id=`BRANCH_REF`):

```sql
-- 치과 키워드 개수 확인 (16 기대)
SELECT count(*) FROM classification_keywords WHERE category='dentistry';
-- 경계 미백 확인 (1 기대)
SELECT keyword, context_keywords FROM classification_keywords WHERE keyword='미백';
-- dentistry INSERT 가능 여부 (제약 통과 확인)
INSERT INTO faq_vectors (category, question, answer, embedding)
VALUES ('dentistry', 'test q', 'test a', array_fill(0.0, ARRAY[768])::vector);
DELETE FROM faq_vectors WHERE question='test q' AND answer='test a';
```
Expected: 치과 키워드 count=16, 미백 context_keywords에 dentistry/dermatology 키 존재, INSERT/DELETE 성공(제약 위반 없음).

- [ ] **Step 4: 브랜치 접속 정보 확보**

파이프라인(Python)이 브랜치 DB를 읽도록 브랜치의 `SUPABASE_URL` + `service_role` 키를 확보한다.
- `mcp__supabase__get_project_url`(project_id=`BRANCH_REF`) → URL.
- service_role 키는 MCP로 노출되지 않을 수 있음 → 확보 불가 시 사용자에게 Supabase 대시보드(브랜치 → Settings → API → service_role) 값을 `!` 명령으로 요청.
- `backend/.env.branch` 파일에 기록(gitignore 대상, 커밋 금지):
  ```
  SUPABASE_URL=<branch url>
  SUPABASE_SERVICE_KEY=<branch service_role key>
  ```

- [ ] **Step 5: Commit (SQL 파일만)**

```bash
git add supabase/migrations/011_dentistry_category.sql
git commit -m "feat(치과): 마이그레이션 011 — dentistry CHECK 제약 + 치과 키워드 seed"
```

---

### Task 2: 분류·검증 에이전트 3분류 확장

**Files:**
- Modify: `backend/agents/classifier.py`
- Modify: `backend/agents/validator.py`
- Create: `test_dentistry_prompts.py`

**Interfaces:**
- Consumes: `classification_keywords` 테이블(치과 키워드/경계 미백 — Task 1).
- Produces: `classify_consultation()` / `validate_classification()`가 `classification ∈ {dermatology, plastic_surgery, dentistry, unclassified}` 반환. 함수 시그니처·반환 키 불변.

- [ ] **Step 1: 프롬프트 단위 검증 테스트 작성 (실패 확인용)**

`test_dentistry_prompts.py`:

```python
"""치과 확장 프롬프트/서브템플릿 단위 검증 (DB·LLM 무관).
실행: python test_dentistry_prompts.py
"""
import sys
sys.path.insert(0, "backend")

from agents.classifier import SYSTEM_INSTRUCTION as CLS_SYS
from agents.validator import SYSTEM_INSTRUCTION as VAL_SYS


def test_classifier_system_mentions_dentistry():
    assert "dentistry" in CLS_SYS, "분류 시스템 프롬프트에 dentistry 3분류가 없음"


def test_validator_system_mentions_dentistry():
    assert "dentistry" in VAL_SYS, "검증 시스템 프롬프트에 dentistry가 없음"


if __name__ == "__main__":
    test_classifier_system_mentions_dentistry()
    test_validator_system_mentions_dentistry()
    print("OK: dentistry prompt checks passed")
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python test_dentistry_prompts.py`
Expected: FAIL — `AssertionError: 분류 시스템 프롬프트에 dentistry 3분류가 없음`

- [ ] **Step 3: classifier.py 3분류로 수정**

`backend/agents/classifier.py`의 `SYSTEM_INSTRUCTION`을 교체:

```python
SYSTEM_INSTRUCTION = """당신은 의료 상담 분류 전문가입니다.
상담 내용을 분석하여 피부과(dermatology), 성형외과(plastic_surgery), 치과(dentistry) 중 하나로 분류하세요.

분류 원칙:
1. 단일 분류 원칙: 피부과 OR 성형외과 OR 치과. 혼합 분류 불가.
2. 핵심 의도(주소)가 기준.
3. 경계 시술(보톡스, 필러)은 동반 키워드로 판단.
4. 경계 시술(미백)은 치아 맥락이면 치과, 피부 맥락이면 피부과.
5. 맥락 단서 없으면 unclassified."""
```

그리고 `classify_consultation()` 내 프롬프트에 치과 키워드/규칙을 노출하도록 수정. 기존 키워드 정리부 아래에 치과 키워드 추가:

```python
    plastic_keywords = [k["keyword"] for k in keywords if k["category"] == "plastic_surgery"]
    derma_keywords = [k["keyword"] for k in keywords if k["category"] == "dermatology"]
    dental_keywords = [k["keyword"] for k in keywords if k["category"] == "dentistry"]
    boundary_keywords = [k for k in keywords if k["category"] == "boundary"]

    prompt = f"""다음 상담 내용을 피부과(dermatology), 성형외과(plastic_surgery), 치과(dentistry) 중 하나로 분류하세요.

== 분류 키워드 사전 ==
성형외과 키워드: {', '.join(plastic_keywords)}
피부과 키워드: {', '.join(derma_keywords)}
치과 키워드: {', '.join(dental_keywords)}
경계 시술: {json.dumps([b['keyword'] for b in boundary_keywords], ensure_ascii=False)}

== 경계 시술 분류 규칙 ==
보톡스/필러가 언급된 경우:
- 성형 맥락 동반 (코 높이기, 턱 끝, 윤곽, 이마 볼륨, 리프팅 실) → 성형외과
- 피부 관리 맥락 동반 (레이저, 하이푸, 울쎄라, 피부결, 주름 개선, 탄력, 리쥬란) → 피부과
- 맥락 단서 없음 → unclassified
미백이 언급된 경우:
- 치아/잇몸/구강 맥락 동반 → 치과 (치아미백)
- 피부/톤/색소 맥락 동반 → 피부과 (피부미백)

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 상담 내용 (한국어) ==
{translated_text}

JSON 형식으로 반환:
{{
    "classification": "dermatology" 또는 "plastic_surgery" 또는 "dentistry" 또는 "unclassified",
    "confidence": 0.0~1.0,
    "reason": "분류 근거 설명 (한국어)"
}}"""
```

- [ ] **Step 4: validator.py dentistry 인지로 수정**

`backend/agents/validator.py`의 `SYSTEM_INSTRUCTION` 교체:

```python
SYSTEM_INSTRUCTION = """당신은 의료 상담 분류 검증 전문가입니다.
분류 에이전트의 결과를 검증하여 최종 분류를 확정하거나, 관리자 검토가 필요한 경우 unclassified로 플래그합니다.

분류는 피부과(dermatology), 성형외과(plastic_surgery), 치과(dentistry) 중 하나입니다.

검증 기준:
- 신뢰도 0.8 이상 + 명확 키워드 매칭 → 확정
- 경계 시술이거나 신뢰도 0.8 미만 → 재검토
- 재검토 후에도 불확실 → unclassified"""
```

그리고 재검증 프롬프트의 JSON 형식 라인에 dentistry 추가:

```python
    "classification": "dermatology" 또는 "plastic_surgery" 또는 "dentistry" 또는 "unclassified",
```

- [ ] **Step 5: 테스트 실행하여 통과 확인**

Run: `python test_dentistry_prompts.py`
Expected: PASS — `OK: dentistry prompt checks passed`

- [ ] **Step 6: Commit**

```bash
git add backend/agents/classifier.py backend/agents/validator.py test_dentistry_prompts.py
git commit -m "feat(치과): classifier/validator 3분류(치과) 확장 + 미백 경계 규칙"
```

---

### Task 3: R3/R4 writer 치과 서브템플릿 + 폴백 라벨

**Files:**
- Modify: `backend/agents/report_writer.py:78-82`
- Modify: `backend/agents/r3_director_writer.py:60`
- Modify: `backend/agents/pipeline.py` (`_build_fallback_r4`, `_build_fallback_r4_ko`, `_build_fallback_r3`)
- Modify: `test_dentistry_prompts.py`

**Interfaces:**
- Consumes: `write_report(classification='dentistry', ...)`, `write_r3_report(classification='dentistry', ...)`.
- Produces: 치과 상담 시 R4 `category_note`가 치료 단계 중심 지시, R3 `category_label='치과'`. 반환 JSON 키 불변. 폴백 라벨 치과 대응.

- [ ] **Step 1: writer 서브템플릿 검증 테스트 추가 (실패 확인용)**

`test_dentistry_prompts.py`에 함수 추가하고 `__main__`에도 등록:

```python
def test_r4_category_note_has_dentistry_branch():
    import inspect
    from agents import report_writer
    src = inspect.getsource(report_writer.write_report)
    assert "dentistry" in src and "歯科" in src, "R4 writer에 치과(歯科) 분기가 없음"


def test_r3_category_label_has_dentistry_branch():
    import inspect
    from agents import r3_director_writer
    src = inspect.getsource(r3_director_writer.write_r3_report)
    assert "dentistry" in src and "치과" in src, "R3 writer에 치과 라벨 분기가 없음"
```

`__main__` 블록에 추가:

```python
    test_r4_category_note_has_dentistry_branch()
    test_r3_category_label_has_dentistry_branch()
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python test_dentistry_prompts.py`
Expected: FAIL — `AssertionError: R4 writer에 치과(歯科) 분기가 없음`

- [ ] **Step 3: report_writer.py (R4) 치과 분기 추가**

`backend/agents/report_writer.py` line 78-82 교체:

```python
    category_note = ""
    if classification == "plastic_surgery":
        category_note = "整形外科の相談です。構造的なアプローチを中心に記述してください。"
    elif classification == "dentistry":
        category_note = "歯科の相談です。治療ステップ・通院回数・材料の選択肢（インプラント/根管治療/セラミック/矯正/ホワイトニング等）を中心に記述してください。"
    else:
        category_note = "皮膚科の相談です。治療プロトコルを中心に記述してください。"
```

- [ ] **Step 4: r3_director_writer.py (R3) 치과 라벨 추가**

`backend/agents/r3_director_writer.py` line 60 교체:

```python
    if classification == "plastic_surgery":
        category_label = "성형외과"
    elif classification == "dentistry":
        category_label = "치과"
    else:
        category_label = "피부과"
```

- [ ] **Step 5: pipeline.py 폴백 라벨 치과 대응**

`backend/agents/pipeline.py`에서 3개 폴백 빌더의 카테고리 라벨을 치과 대응으로 수정.

`_build_fallback_r4` (line 25):
```python
    if classification == "dermatology":
        category_ja = "皮膚科"
    elif classification == "dentistry":
        category_ja = "歯科"
    else:
        category_ja = "美容整形"
```

`_build_fallback_r4_ko` (line 90):
```python
    if classification == "dermatology":
        category_ko = "피부과"
    elif classification == "dentistry":
        category_ko = "치과"
    else:
        category_ko = "미용성형"
```

`_build_fallback_r3` (line 156):
```python
    if classification == "dermatology":
        category_ko = "피부과"
    elif classification == "dentistry":
        category_ko = "치과"
    else:
        category_ko = "성형외과"
```

- [ ] **Step 6: 테스트 실행하여 통과 확인**

Run: `python test_dentistry_prompts.py`
Expected: PASS — `OK: dentistry prompt checks passed`

- [ ] **Step 7: Commit**

```bash
git add backend/agents/report_writer.py backend/agents/r3_director_writer.py backend/agents/pipeline.py test_dentistry_prompts.py
git commit -m "feat(치과): R3/R4 writer 치과 서브템플릿 + 폴백 라벨 대응"
```

---

### Task 4: PubMed 치과 쿼리 세트 + FAQ 용어 변환

**Files:**
- Modify: `backend/scripts/build_pubmed_vectors.py`
- Modify: `test_dentistry_prompts.py`

**Interfaces:**
- Produces: `DENTISTRY_QUERIES`(6영역 ~40쿼리, 각 `category='dentistry'`), `ALL_QUERIES = DERMATOLOGY_QUERIES + PLASTIC_SURGERY_QUERIES + DENTISTRY_QUERIES`, `CATEGORY_KR['dentistry']='치과 진료'`, FAQ 프롬프트 시술명 변환 규칙에 치과 용어 추가.

- [ ] **Step 1: 쿼리 세트 개수 검증 테스트 추가 (실패 확인용)**

`test_dentistry_prompts.py`에 추가 + `__main__` 등록:

```python
def test_dentistry_queries_defined():
    from scripts import build_pubmed_vectors as bpv
    assert hasattr(bpv, "DENTISTRY_QUERIES"), "DENTISTRY_QUERIES 미정의"
    assert len(bpv.DENTISTRY_QUERIES) >= 36, f"치과 쿼리 부족: {len(bpv.DENTISTRY_QUERIES)}"
    assert all(q["category"] == "dentistry" for q in bpv.DENTISTRY_QUERIES)
    assert all(q in bpv.ALL_QUERIES for q in bpv.DENTISTRY_QUERIES), "ALL_QUERIES에 치과 미포함"
    assert bpv.CATEGORY_KR.get("dentistry"), "CATEGORY_KR에 dentistry 라벨 없음"
```

`__main__` 블록에 추가:
```python
    test_dentistry_queries_defined()
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python test_dentistry_prompts.py`
Expected: FAIL — `AttributeError` 또는 `AssertionError: DENTISTRY_QUERIES 미정의`

- [ ] **Step 3: DENTISTRY_QUERIES 추가**

`backend/scripts/build_pubmed_vectors.py`의 `PLASTIC_SURGERY_QUERIES` 정의 직후, `ALL_QUERIES` 라인 **앞**에 삽입:

```python
DENTISTRY_QUERIES = [
    # --- 임플란트 ---
    {"name": "임플란트(생존율)", "query": "(dental implant[Title/Abstract]) AND (survival rate OR success rate[Title/Abstract]) AND (long-term OR follow-up[Title/Abstract])", "procedure": "임플란트", "category": "dentistry"},
    {"name": "임플란트(골유착)", "query": "(dental implant[Title/Abstract]) AND (osseointegration[Title/Abstract]) AND (outcome OR success[Title/Abstract])", "procedure": "임플란트", "category": "dentistry"},
    {"name": "임플란트(즉시식립)", "query": "(immediate loading OR immediate placement[Title/Abstract]) AND (dental implant[Title/Abstract]) AND (outcome OR survival[Title/Abstract])", "procedure": "임플란트(즉시식립)", "category": "dentistry"},
    {"name": "임플란트(올온4)", "query": "(All-on-4 OR all on four[Title/Abstract]) AND (implant[Title/Abstract]) AND (outcome OR satisfaction[Title/Abstract])", "procedure": "임플란트(올온4)", "category": "dentistry"},
    {"name": "상악동거상술", "query": "(sinus lift OR sinus augmentation[Title/Abstract]) AND (dental implant[Title/Abstract]) AND (outcome OR success[Title/Abstract])", "procedure": "상악동거상술", "category": "dentistry"},
    {"name": "임플란트(주위염)", "query": "(peri-implantitis[Title/Abstract]) AND (treatment OR prevalence OR risk factor[Title/Abstract])", "procedure": "임플란트주위염", "category": "dentistry"},
    {"name": "임플란트(심미/전치부)", "query": "(anterior dental implant OR esthetic implant[Title/Abstract]) AND (outcome OR satisfaction OR pink esthetic[Title/Abstract])", "procedure": "전치부 임플란트", "category": "dentistry"},
    # --- 교정 ---
    {"name": "투명교정(인비절라인)", "query": "(clear aligner OR Invisalign[Title/Abstract]) AND (efficacy OR outcome OR satisfaction[Title/Abstract])", "procedure": "투명교정", "category": "dentistry"},
    {"name": "교정(발치)", "query": "(orthodontic treatment[Title/Abstract]) AND (extraction[Title/Abstract]) AND (outcome OR profile change[Title/Abstract])", "procedure": "발치교정", "category": "dentistry"},
    {"name": "설측교정", "query": "(lingual orthodontics[Title/Abstract]) AND (efficacy OR outcome OR satisfaction[Title/Abstract])", "procedure": "설측교정", "category": "dentistry"},
    {"name": "자가결찰교정", "query": "(self-ligating bracket[Title/Abstract]) AND (efficacy OR treatment time OR outcome[Title/Abstract])", "procedure": "자가결찰교정", "category": "dentistry"},
    {"name": "교정용미니스크류(TAD)", "query": "(temporary anchorage device OR miniscrew OR TAD[Title/Abstract]) AND (orthodontic[Title/Abstract]) AND (success OR outcome[Title/Abstract])", "procedure": "교정미니스크류", "category": "dentistry"},
    {"name": "성인교정", "query": "(adult orthodontic treatment[Title/Abstract]) AND (outcome OR satisfaction OR quality of life[Title/Abstract])", "procedure": "성인교정", "category": "dentistry"},
    {"name": "부정교합", "query": "(malocclusion[Title/Abstract]) AND (orthodontic treatment[Title/Abstract]) AND (outcome OR quality of life[Title/Abstract])", "procedure": "부정교합교정", "category": "dentistry"},
    # --- 심미(라미네이트/미백/크라운) ---
    {"name": "라미네이트(베니어)", "query": "(porcelain veneer OR laminate veneer[Title/Abstract]) AND (survival OR longevity OR satisfaction[Title/Abstract])", "procedure": "라미네이트", "category": "dentistry"},
    {"name": "세라믹크라운", "query": "(ceramic crown OR zirconia crown[Title/Abstract]) AND (survival OR success OR longevity[Title/Abstract])", "procedure": "세라믹크라운", "category": "dentistry"},
    {"name": "치아미백", "query": "(tooth whitening OR dental bleaching[Title/Abstract]) AND (efficacy OR color change OR sensitivity[Title/Abstract])", "procedure": "치아미백", "category": "dentistry"},
    {"name": "디지털스마일디자인", "query": "(digital smile design[Title/Abstract]) AND (esthetic OR outcome OR satisfaction[Title/Abstract])", "procedure": "디지털스마일디자인", "category": "dentistry"},
    {"name": "심미수복(복합레진)", "query": "(composite resin restoration[Title/Abstract]) AND (anterior OR esthetic[Title/Abstract]) AND (longevity OR outcome[Title/Abstract])", "procedure": "심미수복", "category": "dentistry"},
    {"name": "치은성형(잇몸심미)", "query": "(gingival contouring OR crown lengthening OR gummy smile[Title/Abstract]) AND (esthetic OR outcome[Title/Abstract])", "procedure": "잇몸성형", "category": "dentistry"},
    # --- 보존(신경치료/충치) ---
    {"name": "신경치료(근관)", "query": "(root canal treatment OR endodontic treatment[Title/Abstract]) AND (success rate OR outcome[Title/Abstract])", "procedure": "신경치료", "category": "dentistry"},
    {"name": "재신경치료", "query": "(endodontic retreatment[Title/Abstract]) AND (success OR outcome OR prognosis[Title/Abstract])", "procedure": "재신경치료", "category": "dentistry"},
    {"name": "치근단수술", "query": "(apicoectomy OR endodontic microsurgery[Title/Abstract]) AND (success OR outcome[Title/Abstract])", "procedure": "치근단수술", "category": "dentistry"},
    {"name": "충치(복합레진충전)", "query": "(dental caries[Title/Abstract]) AND (composite restoration[Title/Abstract]) AND (longevity OR survival[Title/Abstract])", "procedure": "충치치료", "category": "dentistry"},
    {"name": "인레이/온레이", "query": "(inlay OR onlay[Title/Abstract]) AND (ceramic OR composite[Title/Abstract]) AND (survival OR longevity[Title/Abstract])", "procedure": "인레이온레이", "category": "dentistry"},
    {"name": "치수보호(MTA)", "query": "(pulp capping OR MTA[Title/Abstract]) AND (vital pulp therapy[Title/Abstract]) AND (success OR outcome[Title/Abstract])", "procedure": "치수치료", "category": "dentistry"},
    # --- 치주 ---
    {"name": "치주치료(스케일링/루트플레닝)", "query": "(scaling and root planing[Title/Abstract]) AND (periodontitis[Title/Abstract]) AND (outcome OR clinical attachment[Title/Abstract])", "procedure": "치주치료", "category": "dentistry"},
    {"name": "치주수술", "query": "(periodontal surgery OR flap surgery[Title/Abstract]) AND (outcome OR pocket depth[Title/Abstract])", "procedure": "치주수술", "category": "dentistry"},
    {"name": "잇몸이식", "query": "(gingival graft OR connective tissue graft[Title/Abstract]) AND (recession OR root coverage[Title/Abstract])", "procedure": "잇몸이식", "category": "dentistry"},
    {"name": "치주조직재생(GTR)", "query": "(guided tissue regeneration OR periodontal regeneration[Title/Abstract]) AND (outcome OR bone fill[Title/Abstract])", "procedure": "치주재생", "category": "dentistry"},
    {"name": "치주-전신질환", "query": "(periodontitis[Title/Abstract]) AND (diabetes OR cardiovascular[Title/Abstract]) AND (association OR risk[Title/Abstract])", "procedure": "치주건강", "category": "dentistry"},
    # --- 구강외과 ---
    {"name": "사랑니발치(매복)", "query": "(impacted third molar OR wisdom tooth extraction[Title/Abstract]) AND (complication OR recovery OR outcome[Title/Abstract])", "procedure": "사랑니발치", "category": "dentistry"},
    {"name": "발치후치유", "query": "(tooth extraction[Title/Abstract]) AND (socket healing OR dry socket[Title/Abstract]) AND (outcome OR prevention[Title/Abstract])", "procedure": "발치", "category": "dentistry"},
    {"name": "치조골이식(GBR)", "query": "(guided bone regeneration OR alveolar ridge augmentation[Title/Abstract]) AND (outcome OR bone gain[Title/Abstract])", "procedure": "골이식", "category": "dentistry"},
    {"name": "턱관절장애(TMD)", "query": "(temporomandibular disorder OR TMJ[Title/Abstract]) AND (treatment OR splint[Title/Abstract]) AND (outcome[Title/Abstract])", "procedure": "턱관절치료", "category": "dentistry"},
    {"name": "치성감염", "query": "(odontogenic infection[Title/Abstract]) AND (management OR antibiotic OR outcome[Title/Abstract])", "procedure": "치성감염", "category": "dentistry"},
    {"name": "발치후임플란트(치조제보존)", "query": "(socket preservation OR ridge preservation[Title/Abstract]) AND (implant[Title/Abstract]) AND (outcome[Title/Abstract])", "procedure": "치조제보존", "category": "dentistry"},
]
```

그리고 `ALL_QUERIES` 라인을 교체:

```python
ALL_QUERIES = DERMATOLOGY_QUERIES + PLASTIC_SURGERY_QUERIES + DENTISTRY_QUERIES
```

- [ ] **Step 4: CATEGORY_KR + FAQ 용어 변환 규칙 추가**

`CATEGORY_KR` 딕셔너리에 치과 추가:

```python
CATEGORY_KR = {
    "dermatology": "피부과 미용시술",
    "plastic_surgery": "성형외과 수술",
    "dentistry": "치과 진료",
}
```

`FAQ_PROMPT_TEMPLATE`의 "5. 영어 시술명은 한국어로 변환하세요" 목록 끝(`- etc.` 앞)에 치과 용어 추가:

```python
   - dental implant → 임플란트
   - root canal treatment → 신경치료
   - clear aligner / Invisalign → 투명교정
   - porcelain veneer / laminate veneer → 라미네이트
   - ceramic crown / zirconia crown → 세라믹 크라운
   - tooth whitening / bleaching → 치아미백
   - scaling and root planing → 치주치료(스케일링)
   - impacted third molar → 매복 사랑니
   - temporomandibular disorder / TMJ → 턱관절장애
```

- [ ] **Step 5: 검색 쿼리 개수 지정 확인**

기존 스크립트는 `retmax=30`(fetch_pubmed_articles 내부). 치과 목표 2,500~3,000 FAQ 확보를 위해 `Entrez.esearch` 호출의 `retmax=30`을 `retmax=40`으로 상향(전 카테고리 공통, 기존 카테고리는 이미 구축 완료라 중복 스킵되어 무영향):

`fetch_pubmed_articles` 내 `Entrez.esearch(... retmax=30 ...)` → `retmax=40`.

- [ ] **Step 6: 테스트 실행하여 통과 확인**

Run: `python test_dentistry_prompts.py`
Expected: PASS — `OK: dentistry prompt checks passed`

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/build_pubmed_vectors.py test_dentistry_prompts.py
git commit -m "feat(치과): PubMed 치과 쿼리 6영역 36+개 + FAQ 용어 변환 + retmax 40"
```

---

### Task 5: 치과 벡터 구축 (개발 브랜치, 2,500~3,000)

**Files:**
- 없음(스크립트 실행 태스크). `backend/scripts/pubmed_articles.json`(중간 산출물, gitignore) 생성.

**Interfaces:**
- Consumes: `DENTISTRY_QUERIES`(Task 4), 브랜치 DB 접속(`backend/.env.branch`, Task 1 Step 4).
- Produces: 브랜치 `faq_vectors`에 `category='dentistry'` FAQ 2,500~3,000건(실제 임베딩 768).

- [ ] **Step 1: 브랜치 접속으로 환경 전환**

브랜치 DB를 바라보도록 환경 설정. `backend/` 기준 실행 시 `.env`가 로드되므로, 안전하게 별도 실행:

```bash
cd backend
cp .env .env.prod.bak            # 운영 값 백업
cp .env.branch .env.override     # 참고용
# .env의 SUPABASE_URL / SUPABASE_SERVICE_KEY 두 줄만 브랜치 값으로 교체
```

> ⚠️ 주의: `.env`의 SUPABASE 두 줄만 브랜치 값으로 바꾼다. GEMINI_API_KEY/NCBI 등 나머지는 그대로. 작업 종료 후 Step 6에서 원복.

- [ ] **Step 2: PubMed 논문 수집 (step 1)**

```bash
cd backend
python -m scripts.build_pubmed_vectors --step 1
```
Expected: 콘솔에 치과 쿼리 36+개가 `(dentistry)`로 순회되며 논문 수집. `scripts/pubmed_articles.json`에 기존+치과 논문 누적 저장. 치과 신규 논문 ~900~1,100편 기대.

> 기존 피부/성형 PMID는 브랜치에 이미 있어 "all duplicates"로 스킵됨 → 실질 치과만 신규 수집.

- [ ] **Step 3: FAQ 변환 (step 2) — 백그라운드**

Gemini 15RPM 병목으로 수 시간 소요 → 백그라운드 실행.

```bash
cd backend
nohup python -m scripts.build_pubmed_vectors --step 2 > ../dentistry_faq_build.log 2>&1 &
```
진행 모니터: `tail -f dentistry_faq_build.log`
Expected: 치과 논문별 `-> N FAQs saved`. 완료 시 `FAQ done: NNN articles -> MMMM FAQs`.

- [ ] **Step 4: 임베딩 (step 3)**

FAQ 변환 완료 후:

```bash
cd backend
python -m scripts.build_pubmed_vectors --step 3
```
Expected: 더미 임베딩이 실제 Gemini Embedding 768로 교체. `Embedding done: NNNN success / 0 failed`.

> step 3은 PubMed URL 패턴 전체를 대상으로 하므로, 이미 임베딩된 기존 PubMed FAQ도 재임베딩될 수 있음. 시간 절약을 위해 치과만 대상으로 하려면 임시로 `.like("youtube_url", ...)` 뒤에 `.eq("category","dentistry")` 필터를 추가해도 되나, **선택**. 기본은 스크립트 그대로 실행.

- [ ] **Step 5: 치과 벡터 개수 검증**

`mcp__supabase__execute_sql`(project_id=`BRANCH_REF`):

```sql
SELECT category, count(*) FROM faq_vectors GROUP BY category ORDER BY category;
-- dentistry가 2500~3000 범위인지 확인
SELECT count(*) FROM faq_vectors
WHERE category='dentistry' AND embedding <> array_fill(0.0, ARRAY[768])::vector;
-- 더미(미임베딩) 잔여 0 기대
SELECT count(*) FROM faq_vectors
WHERE category='dentistry' AND embedding = array_fill(0.0, ARRAY[768])::vector;
```
Expected: dentistry count 2,500~3,000, 더미 잔여 0. 부족 시 Task 4의 retmax 상향 또는 쿼리 추가 후 재실행.

- [ ] **Step 6: 환경 원복**

```bash
cd backend
cp .env.prod.bak .env            # 운영 값 복구
rm -f .env.override
```
Expected: `.env`의 SUPABASE_URL/KEY가 운영 값으로 복구됨. (`git status`로 .env 변경 없음 확인 — .env는 gitignore.)

> 커밋 대상 없음(산출물은 DB + gitignore 파일). 다음 태스크로 진행.

---

### Task 6: End-to-End + 회귀 테스트 (브랜치 + DEV 콜백)

**Files:**
- Create: `test_dentistry_e2e.py`

**Interfaces:**
- Consumes: 브랜치 DB(치과 벡터 완비), `run_pipeline`, `notify_report_ready`, `IPPEO_WEBHOOK_URL_DEV`.
- Produces: 치과 상담이 `classification='dentistry'`로 분류되고 R3+R4 생성 + DEV 콜백 200. 회귀로 피부/성형 정상.

- [ ] **Step 1: E2E 테스트 스크립트 작성**

`test_dentistry_e2e.py` (브랜치 `.env`로 실행). 상담을 DB에 직접 insert → `run_pipeline` → 결과 검증:

```python
"""치과 end-to-end + 회귀 테스트. 브랜치 DB 대상.
전제: backend/.env의 SUPABASE가 브랜치 값(Task 5 Step 1과 동일 전환) + IPPEO_WEBHOOK_URL_DEV 설정.
실행: cd backend && python ../test_dentistry_e2e.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from services.supabase_client import get_supabase
from agents.pipeline import run_pipeline

DENTAL_STT = """カウンセラー: こんにちは、本日のご相談内容をお聞かせください。
お客様: 奥歯が虫歯でだいぶ削れていて、インプラントを考えています。
カウンセラー: インプラントですね。骨の状態にもよりますが、治療期間は3〜6ヶ月ほどです。
お客様: 費用はどのくらいですか？何回くらい通院が必要ですか？
カウンセラー: 1本あたりの目安と通院回数は診察後にご案内します。まずは口腔内の検査が必要です。
お客様: 来月から始めたいです。セラミックの被せ物も気になっています。"""

DERMA_STT = """カウンセラー: 本日はどのようなご相談ですか？
お客様: 最近シミが増えてきて、ピコレーザーを考えています。毛穴も気になります。
カウンセラー: レーザートーニングが効果的です。3〜5回のコースが一般的です。"""

PLASTIC_STT = """カウンセラー: ご相談内容をお聞かせください。
お客様: 鼻が低くて、プロテーゼで高くしたいです。横顔のラインが気になります。
カウンセラー: 鼻筋を通す隆鼻術ですね。軟骨移植との組み合わせもご提案できます。"""


async def _run_case(name, stt, expected_class):
    db = get_supabase()
    ins = db.table("consultations").insert({
        "customer_name": f"E2E {name}",
        "customer_email": "e2e@example.com",
        "original_text": stt,
        "status": "registered",
        "consultation_round": 3,
        "ippeo_consultation_id": f"e2e_{name}_r3",
    }).execute()
    cid = ins.data[0]["id"]
    await run_pipeline(cid)

    row = db.table("consultations").select("classification, status").eq("id", cid).single().execute().data
    print(f"[{name}] classification={row['classification']} status={row['status']} (expected {expected_class})")
    assert row["classification"] == expected_class, f"{name} 분류 실패: {row['classification']}"

    reports = db.table("reports").select("report_type, report_data, access_token").eq("consultation_id", cid).execute().data
    types = {r["report_type"] for r in reports}
    assert "r3" in types and "r4" in types, f"{name} R3/R4 누락: {types}"

    r4 = next(r for r in reports if r["report_type"] == "r4")
    for k in ("section1_key_summary", "section8_cost_estimate", "section10_ippeo_message"):
        assert k in r4["report_data"], f"{name} R4 키 누락: {k}"
    print(f"[{name}] R3+R4 OK, R4 keys intact, token={r4['access_token'][:8]}")
    return cid


async def _check_rag_isolation():
    from agents.rag_agent import search_relevant_faq
    res = await search_relevant_faq(["임플란트", "신경치료", "치아교정"], "dentistry")
    assert res, "치과 RAG 결과 0건 — 벡터 구축/카테고리 확인 필요"
    print(f"[RAG] dentistry 검색 {len(res)}건, 첫 시술명={res[0].get('procedure_name')}")


async def main():
    await _check_rag_isolation()
    dental_cid = await _run_case("dental", DENTAL_STT, "dentistry")
    await _run_case("derma", DERMA_STT, "dermatology")
    await _run_case("plastic", PLASTIC_STT, "plastic_surgery")

    # DEV 콜백 실전송 (dental 케이스)
    from services.ippeo_callback import notify_report_ready
    await notify_report_ready(dental_cid)
    print("[Callback] dental DEV 콜백 전송 완료 (로그에서 200 확인)")
    print("\\nOK: 치과 E2E + 회귀 통과")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 브랜치 환경으로 전환 + DEV 콜백 URL 확인**

Task 5 Step 1과 동일하게 `.env`의 SUPABASE를 브랜치로 전환. 추가로 `.env`에 `IPPEO_WEBHOOK_URL_DEV`가 설정돼 있는지 확인(없으면 값 확보 후 설정). **`IPPEO_WEBHOOK_URL`(PROD)는 이 테스트 동안 비워두거나 유지** — 규칙상 콜백은 설정된 URL 모두로 감. PROD 라이브 유입 방지를 위해 테스트 중에는 `.env`에서 `IPPEO_WEBHOOK_URL`을 임시로 주석/공란 처리.

```bash
cd backend
# .env에서: SUPABASE_URL/KEY → 브랜치, IPPEO_WEBHOOK_URL → 임시 공란, IPPEO_WEBHOOK_URL_DEV 유지
```

- [ ] **Step 3: E2E 실행**

```bash
cd backend
python ../test_dentistry_e2e.py
```
Expected: 콘솔에
```
[RAG] dentistry 검색 N건, 첫 시술명=...
[dental] classification=dentistry status=report_ready (expected dentistry)
[dental] R3+R4 OK, R4 keys intact, token=...
[derma] classification=dermatology ...
[plastic] classification=plastic_surgery ...
[Callback:DEV] Report ready sent (... status=200)
OK: 치과 E2E + 회귀 통과
```

- [ ] **Step 4: 실패 시 디버깅 (systematic-debugging)**

분류가 틀리면 → classifier 프롬프트/키워드 seed 재확인. RAG 0건이면 → 벡터 개수/카테고리/임베딩 재확인. 콜백 non-200이면 → DEV URL/시크릿/payload 로그 확인. 근본 원인 수정 후 Step 3 재실행.

- [ ] **Step 5: 환경 원복 + Commit**

```bash
cd backend
cp .env.prod.bak .env    # 운영 값 + PROD 콜백 URL 복구
cd ..
git add test_dentistry_e2e.py
git commit -m "test(치과): E2E + 회귀 테스트 스크립트 (브랜치 DB + DEV 콜백)"
```

---

### Task 7: 운영 배포 (최종 승인 후)

**Files:**
- 없음(운영 반영 태스크). Task 1의 `011_dentistry_category.sql` + Task 2~4 코드 사용.

**Interfaces:**
- Consumes: 검증 완료된 코드(main 브랜치), 브랜치 치과 벡터, 마이그레이션 011.
- Produces: 운영 `medihim_report` + Cloud Run `ippo-backend`에 치과 확장 반영.

- [ ] **Step 1: 사용자 최종 승인 확인**

Task 6 통과 결과를 보고하고 배포 승인을 받는다. 승인 전에는 이하 진행 금지.

- [ ] **Step 2: 운영 DB에 마이그레이션 011 + 키워드 seed 적용**

`mcp__supabase__apply_migration`(project_id=`vkwdkjwiriqujfzjpxlp`, name=`011_dentistry_category`, query=Task1 SQL). 적용 후 검증:

```sql
SELECT count(*) FROM classification_keywords WHERE category='dentistry';  -- 16 기대
```

- [ ] **Step 3: 치과 벡터 rows를 브랜치→운영 복사 (재임베딩 없음)**

> 변경(2026-07-11 사용자 지시): 치과 전체 + **피부/성형 추가분**(retmax 40 상향으로 브랜치에만 생성된 약 1,200건, 운영에 없는 PMID 기준)도 함께 운영에 복사한다.

브랜치에서 치과 FAQ를 조회하여 운영에 삽입. `mcp__supabase__execute_sql`로 브랜치에서 배치 export(JSON) 후 운영에 insert하거나, 브랜치가 같은 조직이면 `postgres_fdw`/덤프. 간단한 경로:
- 브랜치에서 `SELECT category, question, answer, procedure_name, youtube_video_id, youtube_title, youtube_url, embedding FROM faq_vectors WHERE category='dentistry'` 결과를 배치로 운영에 INSERT.
- 페이지네이션(1000행) 준수. 임베딩 벡터 그대로 복사(재계산 불필요).

복사 후 운영 검증:
```sql
SELECT count(*) FROM faq_vectors WHERE category='dentistry';  -- 브랜치와 동일 기대
```

- [ ] **Step 4: 코드 배포 (--no-traffic --tag)**

```bash
cd backend
gcloud run deploy ippo-backend --source . --project=ipp0-medhim --region=asia-northeast3 --allow-unauthenticated --no-traffic --tag dentistry
```
Expected: 새 리비전이 태그 URL로 생성(트래픽 0%).

- [ ] **Step 5: 태그 URL에서 회귀 스모크 + 치과 검증**

태그 URL로 치과/피부/성형 각 1건 webhook 유입 → 리포트 생성 + **DEV 콜백** 200 확인(PROD 콜백은 라이브 영향 → 태그 검증 단계에서는 DEV만 확인). 기존 2개과 회귀 정상 확인.

- [ ] **Step 6: 트래픽 전환**

```bash
gcloud run services update-traffic ippo-backend --project=ipp0-medhim --region=asia-northeast3 --to-latest
```
Expected: 최신 리비전 100% 트래픽.
롤백: `gcloud run services update-traffic ippo-backend --project=ipp0-medhim --region=asia-northeast3 --to-revisions <이전리비전>=100`

- [ ] **Step 7: 브랜치 정리 + CLAUDE.md/메모리 업데이트**

- `mcp__supabase__delete_branch`(branch_id=`BRANCH_REF`)로 개발 브랜치 삭제(비용 정지).
- CLAUDE.md "다음 작업" 섹션을 완료로 갱신, 치과 확장 완료 항목 추가.
- 메모리 `project_dental_expansion.md` 완료 상태로 업데이트.

```bash
git add CLAUDE.md
git commit -m "docs(치과): 치과 카테고리 확장 완료 반영"
```

---

## Self-Review 결과

**Spec coverage:**
- §3 코드 영향 → Task 1(마이그레이션/seed), Task 2(classifier/validator), Task 3(R3/R4/폴백), Task 4(PubMed 쿼리) ✓
- §4 브랜치 테스트 환경 → Task 1 Step 2~4, Task 5/6 브랜치 실행 ✓
- §4 배포 시 rows 복사 → Task 7 Step 3 ✓
- §5 벡터 구축 → Task 4(쿼리) + Task 5(실행) ✓
- §6 경계 미백만 → Task 1 seed + Task 2 프롬프트 ✓
- §7 서브템플릿 → Task 3 ✓
- §8 E2E 6단계 + 회귀 → Task 6 ✓
- §9 배포 → Task 7 ✓
- §10 범위 밖(프론트/YouTube) → 미포함 ✓

**Placeholder scan:** 코드 스텝 모두 실제 코드 포함. "적절히 처리" 류 없음.

**Type consistency:** `classification` 문자열 리터럴 dentistry 일관. `DENTISTRY_QUERIES`/`ALL_QUERIES`/`CATEGORY_KR['dentistry']` 명명 Task 4↔5↔6 일치. `write_report`/`write_r3_report` 시그니처 불변.

**주의(비-TDD 특성):** 파이프라인은 LLM 기반이라 Task 6은 순수 단위테스트가 아닌 통합 검증. 결정적 부분(프롬프트 내용/JSON 키/쿼리 개수/CHECK 제약)은 Task 1~4에서 단위 검증(`test_dentistry_prompts.py`)으로 선검증.
