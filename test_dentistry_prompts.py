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


if __name__ == "__main__":
    test_classifier_system_mentions_dentistry()
    test_validator_system_mentions_dentistry()
    test_r4_category_note_has_dentistry_branch()
    test_r3_category_label_has_dentistry_branch()
    print("OK: dentistry prompt checks passed")
