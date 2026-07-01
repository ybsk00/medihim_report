"""DEV 전용: reports.report_data → 디자인용 라벨 블록 JSON 변환.

운영(PROD) 무관. 새 개발사(메디힘)가 내부 섹션 키 구조(section1_key_summary 등)를
몰라도, 각 블록의 '구분'(큰제목/섹션제목/본문/리스트/항목/주석) 라벨만 보고
자체 디자인을 입혀 렌더링할 수 있도록 순서가 있는 블록 리스트로 평탄화한다.

읽기 전용 — DB를 변경하지 않는다. 폴백/누락 키에도 죽지 않도록 방어적으로 처리한다.

블록 구분자(6종 고정 어휘):
  큰제목   {구분, 내용:str}
  섹션제목 {구분, 내용:str, 섹션키:str}
  본문     {구분, 내용:str}
  리스트   {구분, 내용:list[str]}
  항목     {구분, 라벨:str, 값:str}
  주석     {구분, 내용:str}
"""

# R4(고객용) 섹션 표시 제목 — 원본 report_data에는 없고 프론트 컴포넌트에 하드코딩되어 있어
# 변환 함수가 사전으로 보유한다.
R4_SECTION_TITLES = {
    "section1_key_summary":   {"ja": "ご相談の要点",       "ko": "핵심 요약"},
    "section2_cause_analysis": {"ja": "原因・背景の分析",   "ko": "원인 분석"},
    "section3_recommendation": {"ja": "おすすめの方向性",   "ko": "추천 방향"},
    "section4_recovery":      {"ja": "回復について",        "ko": "회복 정보"},
    "section5_scar_info":     {"ja": "傷跡について",        "ko": "흉터 정보"},
    "section6_precautions":   {"ja": "施術前後の注意点",     "ko": "시술 전후 주의점"},
    "section7_risks":         {"ja": "リスクについて",      "ko": "리스크"},
    "section8_cost_estimate": {"ja": "費用の目安",          "ko": "예상 비용"},
    "section9_visit_date":    {"ja": "ご来院の目安",        "ko": "내원 일정"},
    "section10_ippeo_message": {"ja": "イッポからのメッセージ", "ko": "이뻐 메시지"},
}

# R3(병원용) 섹션 표시 제목 — 한국어 고정.
R3_SECTION_TITLES = {
    "section1_consultation_summary": "상담 요약",
    "section2_procedure_plan":       "시술 계획",
    "section3_cost_estimate":        "비용 견적",
    "section4_scheduling":           "일정",
    "section5_considerations":       "고려사항",
    "section6_action_items":         "액션 아이템",
    "section7_voice_analysis":       "음성 분석",
}


def _txt(value):
    """문자열로 정규화. 비었거나 None이면 None 반환."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _str_list(value):
    """리스트를 비어있지 않은 문자열 리스트로 정규화. 없으면 []."""
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        s = _txt(v)
        if s:
            out.append(s)
    return out


class _Blocks:
    """블록 누적 + 빈 값 자동 스킵 헬퍼."""

    def __init__(self):
        self.items = []

    def title(self, value):
        s = _txt(value)
        if s:
            self.items.append({"구분": "큰제목", "내용": s})

    def heading(self, section_key, text):
        s = _txt(text)
        if s:
            self.items.append({"구분": "섹션제목", "섹션키": section_key, "내용": s})

    def para(self, value):
        s = _txt(value)
        if s:
            self.items.append({"구분": "본문", "내용": s})

    def bullets(self, value):
        lst = _str_list(value)
        if lst:
            self.items.append({"구분": "리스트", "내용": lst})

    def kv(self, label, value):
        lbl = _txt(label)
        val = _txt(value)
        if lbl and val:
            self.items.append({"구분": "항목", "라벨": lbl, "값": val})

    def note(self, value):
        s = _txt(value)
        if s:
            self.items.append({"구분": "주석", "내용": s})


def _build_r4_blocks(data, lang, b):
    def H(key):
        b.heading(key, R4_SECTION_TITLES.get(key, {}).get(lang))

    b.title(data.get("title"))

    s1 = data.get("section1_key_summary") or {}
    H("section1_key_summary")
    b.bullets(s1.get("points"))

    s2 = data.get("section2_cause_analysis") or {}
    H("section2_cause_analysis")
    b.para(s2.get("intro"))
    b.bullets(s2.get("causes"))
    b.para(s2.get("conclusion"))

    s3 = data.get("section3_recommendation") or {}
    H("section3_recommendation")
    primary = s3.get("primary") or {}
    if isinstance(primary, dict):
        b.para(primary.get("label"))
        b.bullets(primary.get("items"))
    elif isinstance(primary, list):
        b.bullets(primary)
    secondary = s3.get("secondary") or {}
    if isinstance(secondary, dict):
        b.para(secondary.get("label"))
        b.bullets(secondary.get("items"))
    elif isinstance(secondary, list):
        b.bullets(secondary)
    b.para(s3.get("goal"))

    s4 = data.get("section4_recovery") or {}
    H("section4_recovery")
    for row in (s4.get("timeline") or []):
        if isinstance(row, dict):
            b.kv(row.get("period"), row.get("detail"))
    b.note(s4.get("note"))

    for key in ("section5_scar_info", "section6_precautions", "section7_risks"):
        sec = data.get(key) or {}
        H(key)
        b.bullets(sec.get("points"))

    s8 = data.get("section8_cost_estimate") or {}
    H("section8_cost_estimate")
    b.bullets(s8.get("items"))
    b.note(s8.get("includes"))
    b.note(s8.get("note"))

    s9 = data.get("section9_visit_date") or {}
    H("section9_visit_date")
    b.para(s9.get("date"))
    b.note(s9.get("note"))

    s10 = data.get("section10_ippeo_message") or {}
    H("section10_ippeo_message")
    for p in (s10.get("paragraphs") or []):
        b.para(p)
    b.para(s10.get("final_summary"))


def _build_r3_blocks(data, b):
    def H(key):
        b.heading(key, R3_SECTION_TITLES.get(key))

    b.title(data.get("title"))

    s1 = data.get("section1_consultation_summary") or {}
    H("section1_consultation_summary")
    b.kv("분류", s1.get("classification"))
    b.kv("CTA", s1.get("cta_level"))
    b.para(s1.get("round_summary"))

    s2 = data.get("section2_procedure_plan") or {}
    H("section2_procedure_plan")
    for proc in (s2.get("primary_procedures") or []):
        if isinstance(proc, dict):
            b.kv(proc.get("name"), proc.get("description"))
    for opt in (s2.get("additional_options") or []):
        if isinstance(opt, dict):
            b.kv(opt.get("name"), opt.get("description"))

    s3 = data.get("section3_cost_estimate") or {}
    H("section3_cost_estimate")
    for item in (s3.get("items") or []):
        if isinstance(item, dict):
            b.kv(item.get("procedure"), item.get("estimated_cost"))
    b.bullets(s3.get("package_options"))
    b.kv("총 예상", s3.get("total_estimate"))
    b.note(s3.get("note"))

    s4 = data.get("section4_scheduling") or {}
    H("section4_scheduling")
    b.kv("희망일", s4.get("preferred_date"))
    b.para(s4.get("treatment_timeline"))
    b.bullets(s4.get("follow_up_plan"))

    s5 = data.get("section5_considerations") or {}
    H("section5_considerations")
    b.bullets(s5.get("patient_concerns"))
    b.bullets(s5.get("negotiation_points"))
    b.para(s5.get("risk_communication"))

    s6 = data.get("section6_action_items") or {}
    H("section6_action_items")
    b.bullets(s6.get("before_visit"))
    b.bullets(s6.get("during_consultation"))
    b.bullets(s6.get("after_consultation"))

    s7 = data.get("section7_voice_analysis")
    if isinstance(s7, dict) and s7:
        H("section7_voice_analysis")
        emo = s7.get("emotional_state") or {}
        b.para(emo.get("summary"))
        vcta = s7.get("voice_cta") or {}
        b.kv("음성 CTA", vcta.get("level"))


def to_design_blocks(report_data, report_type, customer_name,
                     consultation_round, lang):
    """report_data를 디자인용 라벨 블록 JSON으로 변환한다.

    report_type: 'r4'(고객용, ja/ko) | 'r3'(병원용, ko 고정)
    lang: 'ja' | 'ko'  (r3는 lang 무관하게 한국어 데이터)
    """
    # Gemini가 [{...}] 형태로 반환하는 경우 방어
    if isinstance(report_data, list):
        report_data = report_data[0] if report_data else {}
    if not isinstance(report_data, dict):
        report_data = {}

    rtype = (report_type or "r4").lower()
    lang = "ko" if lang == "ko" else "ja"

    b = _Blocks()
    if rtype == "r3":
        _build_r3_blocks(report_data, b)
        report_kind = "병원용"
        role_label = "의사" if consultation_round == 2 else "상담실장"
        meta_lang = "ko"
    else:
        _build_r4_blocks(report_data, lang, b)
        report_kind = "고객용"
        role_label = None
        meta_lang = lang

    return {
        "meta": {
            "이름": customer_name or "",
            "리포트종류": report_kind,
            "회차": consultation_round,
            "역할라벨": role_label,
            "언어": meta_lang,
            "리포트제목": _txt(report_data.get("title")) or "",
            "날짜": _txt(report_data.get("date")) or "",
        },
        "blocks": b.items,
    }
