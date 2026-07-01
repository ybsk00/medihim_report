"""dev_report_format.to_design_blocks 단위 테스트.

운영 무관 / DB 무관 — 순수 변환 로직만 검증.
실행: python test_dev_report_format.py
"""

import sys
sys.path.insert(0, "backend")

from services.dev_report_format import to_design_blocks  # noqa: E402

VALID_GUBUN = {"큰제목", "섹션제목", "본문", "리스트", "항목", "주석"}

R4_SAMPLE = {
    "title": "田中様 鼻のご相談リポート",
    "date": "作成日：2026年6月28日",
    "section1_key_summary": {"points": ["鼻先が尖って見える", "自然な仕上がりを希望", ""]},
    "section2_cause_analysis": {
        "intro": "原因の全体像です。",
        "causes": ["原因1の説明", "原因2の説明"],
        "conclusion": "核心整理です。",
    },
    "section3_recommendation": {
        "primary": {"label": "1次推奨", "items": ["推奨1", "推奨2"]},
        "secondary": {"label": "必要時併用", "items": ["追加1"]},
        "goal": "目標の要約。",
    },
    "section4_recovery": {
        "timeline": [
            {"period": "1〜3日", "detail": "腫れの時期"},
            {"period": "7日", "detail": "抜糸の時期"},
        ],
        "note": None,
    },
    "section5_scar_info": {"points": ["傷跡情報1"]},
    "section6_precautions": {"points": ["注意1", "注意2"]},
    "section7_risks": {"points": ["リスク1"]},
    "section8_cost_estimate": {
        "items": ["鼻尖形成術: 約200〜400万ウォン（参考・税別）"],
        "includes": "麻酔/検査費",
        "note": "正確な見積もりは診察後に。",
    },
    "section9_visit_date": {"date": "2026.07", "note": None},
    "section10_ippeo_message": {
        "paragraphs": ["メッセージ1", "メッセージ2"],
        "final_summary": "最終整理。",
    },
}

R3_SAMPLE = {
    "title": "田中 환자 — 성형외과 상담실장 리포트",
    "date": "2026-06-28",
    "section1_consultation_summary": {
        "name": "田中", "classification": "성형외과",
        "round_summary": "3차 상담 요약.", "cta_level": "hot",
    },
    "section2_procedure_plan": {
        "primary_procedures": [{"name": "코끝성형", "description": "추천 이유 설명"}],
        "additional_options": [{"name": "귀연골", "description": "병용 설명", "recommended": True}],
    },
    "section3_cost_estimate": {
        "items": [{"procedure": "코끝성형", "estimated_cost": "200~400만원", "is_estimate": True}],
        "package_options": ["패키지A 설명"],
        "total_estimate": "300~500만원",
        "note": "추정치입니다.",
    },
    "section4_scheduling": {
        "preferred_date": "미정", "treatment_timeline": "시술~회복 일정.",
        "follow_up_plan": ["1주 후 경과"],
    },
    "section5_considerations": {
        "patient_concerns": ["부자연스러움 우려"],
        "negotiation_points": ["패키지 할인"],
        "risk_communication": "리스크 화법.",
    },
    "section6_action_items": {
        "before_visit": ["사진 준비"], "during_consultation": ["견적 제시"],
        "after_consultation": ["팔로업 콜"],
    },
}


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_r4_ja():
    out = to_design_blocks(R4_SAMPLE, "r4", "田中様", 3, "ja")
    _assert(out["meta"]["리포트종류"] == "고객용", "R4 종류")
    _assert(out["meta"]["언어"] == "ja", "R4 언어 ja")
    _assert(out["meta"]["역할라벨"] is None, "R4 역할라벨 없음")
    gubuns = {blk["구분"] for blk in out["blocks"]}
    _assert(gubuns <= VALID_GUBUN, f"R4 구분 어휘 위반: {gubuns - VALID_GUBUN}")
    first = out["blocks"][0]
    _assert(first["구분"] == "큰제목", "R4 첫 블록 큰제목")
    headings = [b["내용"] for b in out["blocks"] if b["구분"] == "섹션제목"]
    _assert("ご相談の要点" in headings, "R4 ja 섹션제목 사전")
    # 빈 문자열 point는 리스트에서 제외되어야 함
    s1_list = next(b for b in out["blocks"] if b["구분"] == "리스트")
    _assert("" not in s1_list["내용"], "빈 값 제거")
    # 회복 timeline → 항목
    kvs = [b for b in out["blocks"] if b["구분"] == "항목"]
    _assert(any(b["라벨"] == "1〜3日" for b in kvs), "R4 회복 항목")
    print("  ✓ test_r4_ja")


def test_r4_ko_titles():
    out = to_design_blocks(R4_SAMPLE, "r4", "田中様", 3, "ko")
    _assert(out["meta"]["언어"] == "ko", "R4 언어 ko")
    headings = [b["내용"] for b in out["blocks"] if b["구분"] == "섹션제목"]
    _assert("핵심 요약" in headings, "R4 ko 제목 사전")
    _assert("ご相談の要点" not in headings, "R4 ko에 ja 제목 없어야")
    print("  ✓ test_r4_ko_titles")


def test_r3():
    out = to_design_blocks(R3_SAMPLE, "r3", "田中", 2, "ko")
    _assert(out["meta"]["리포트종류"] == "병원용", "R3 종류")
    _assert(out["meta"]["역할라벨"] == "의사", "R3 2차=의사")
    _assert(out["meta"]["언어"] == "ko", "R3 언어 ko")
    gubuns = {blk["구분"] for blk in out["blocks"]}
    _assert(gubuns <= VALID_GUBUN, f"R3 구분 어휘 위반: {gubuns - VALID_GUBUN}")
    kvs = [b for b in out["blocks"] if b["구분"] == "항목"]
    _assert(any(b["라벨"] == "코끝성형" for b in kvs), "R3 시술 항목")
    print("  ✓ test_r3")


def test_r3_role_label_by_round():
    out1 = to_design_blocks(R3_SAMPLE, "r3", "田中", 1, "ko")
    out3 = to_design_blocks(R3_SAMPLE, "r3", "田中", 3, "ko")
    _assert(out1["meta"]["역할라벨"] == "상담실장", "1차=상담실장")
    _assert(out3["meta"]["역할라벨"] == "상담실장", "3차=상담실장")
    print("  ✓ test_r3_role_label_by_round")


def test_defensive_empty_and_list_wrap():
    # 빈 dict
    out = to_design_blocks({}, "r4", "", 3, "ja")
    _assert(out["blocks"] == [] or all(b["구분"] in VALID_GUBUN for b in out["blocks"]), "빈 dict 방어")
    # Gemini [{...}] 래핑 방어
    out2 = to_design_blocks([R4_SAMPLE], "r4", "田中様", 3, "ja")
    _assert(out2["blocks"][0]["구분"] == "큰제목", "리스트 래핑 언랩")
    # None
    out3 = to_design_blocks(None, "r3", "X", 2, "ko")
    _assert(out3["meta"]["리포트종류"] == "병원용", "None 방어")
    print("  ✓ test_defensive_empty_and_list_wrap")


if __name__ == "__main__":
    print("test_dev_report_format:")
    test_r4_ja()
    test_r4_ko_titles()
    test_r3()
    test_r3_role_label_by_round()
    test_defensive_empty_and_list_wrap()
    print("ALL PASSED")
