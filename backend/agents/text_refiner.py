"""STT 텍스트 전처리 + LLM 정제 에이전트.

1. preprocess_stt_dialog(): 규칙 기반 전처리 (LLM 불필요)
   - 의사(숫자)/환자(숫자) 형식의 타임스탬프 제거
   - 화자 라벨 통일 (의사→상담사, 환자→고객)
   - '???', '?' 등 의미 없는 발화 제거
   - 화자별 발화 분리

2. refine_stt_text(): LLM 기반 텍스트 정제
   - STT 오인식 수정
   - 끊어진 짧은 문장 병합
   - 문법 교정
"""

import logging
import re

from services.gemini_client import generate_text

logger = logging.getLogger(__name__)

# 화자 라벨 매핑
_COUNSELOR_LABELS = {"의사", "상담사", "カウンセラー", "counselor"}
_CUSTOMER_LABELS = {"환자", "고객", "相談者", "お客様", "customer"}

# STT 타임스탬프 패턴: 의사(660) : / 환자(1920) :
_SPEAKER_TS_PATTERN = re.compile(
    r"^(의사|환자|상담사|고객|カウンセラー|相談者|お客様)\s*\(\d+\)\s*[:：]\s*(.*)"
)
# 라벨만 있는 패턴: 상담사: / 고객:
_SPEAKER_PATTERN = re.compile(
    r"^(의사|환자|상담사|고객|カウンセラー|相談者|お客様|counselor|customer)\s*[:：]\s*(.*)"
)

# 제거할 무의미 발화
_NOISE_UTTERANCES = {"???", "??", "?", "…", "...", ""}


def preprocess_stt_dialog(text: str) -> dict:
    """규칙 기반 STT 전처리. LLM 호출 없음.

    Returns:
        {
            "cleaned_text": str,           # 정리된 전체 텍스트
            "has_speaker_labels": bool,     # 화자 라벨 감지 여부
            "speaker_segments": list|None,  # [{"speaker": "counselor"/"customer", "text": "..."}]
            "customer_utterances": str|None, # 고객 발화만
            "counselor_utterances": str|None,# 상담사 발화만
        }
    """
    lines = text.strip().split("\n")
    if not lines:
        return _empty_result(text)

    # 타임스탬프 패턴 감지 비율 확인
    ts_matches = sum(1 for line in lines if _SPEAKER_TS_PATTERN.match(line.strip()))
    label_matches = sum(1 for line in lines if _SPEAKER_PATTERN.match(line.strip()))
    total_non_empty = sum(1 for line in lines if line.strip())

    if total_non_empty == 0:
        return _empty_result(text)

    # 50% 이상이 라벨 형식이면 전처리 수행
    has_labels = (ts_matches + label_matches) / total_non_empty > 0.4

    if not has_labels:
        return _empty_result(text)

    counselor_lines = []
    customer_lines = []
    segments = []
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 타임스탬프 패턴 먼저, 그다음 일반 라벨 패턴
        m = _SPEAKER_TS_PATTERN.match(line) or _SPEAKER_PATTERN.match(line)
        if not m:
            # 라벨 없는 줄은 그대로 유지
            cleaned_lines.append(line)
            continue

        speaker_label = m.group(1)
        utterance = m.group(2).strip()

        # 무의미 발화 제거
        if utterance in _NOISE_UTTERANCES:
            continue

        if speaker_label in _COUNSELOR_LABELS:
            counselor_lines.append(utterance)
            segments.append({"speaker": "counselor", "text": utterance})
            cleaned_lines.append(f"상담사: {utterance}")
        elif speaker_label in _CUSTOMER_LABELS:
            customer_lines.append(utterance)
            segments.append({"speaker": "customer", "text": utterance})
            cleaned_lines.append(f"고객: {utterance}")

    cleaned_text = "\n".join(cleaned_lines)

    logger.info(
        f"[Preprocess] {len(lines)} lines → {len(cleaned_lines)} lines, "
        f"counselor={len(counselor_lines)}, customer={len(customer_lines)}"
    )

    return {
        "cleaned_text": cleaned_text,
        "has_speaker_labels": True,
        "speaker_segments": segments,
        "customer_utterances": "\n".join(customer_lines),
        "counselor_utterances": "\n".join(counselor_lines),
    }


def _empty_result(text: str) -> dict:
    return {
        "cleaned_text": text,
        "has_speaker_labels": False,
        "speaker_segments": None,
        "customer_utterances": None,
        "counselor_utterances": None,
    }


# LLM 정제: 텍스트가 너무 길면 스킵 (비용/시간 절약)
_MAX_REFINE_CHARS = 15000


async def refine_stt_text(text: str) -> str:
    """LLM 기반 STT 텍스트 정제.
    오인식 수정, 짧은 문장 병합, 문법 교정.
    15,000자 초과 시 스킵하고 원문 반환.
    """
    if len(text) > _MAX_REFINE_CHARS:
        logger.info(f"[Refine] Text too long ({len(text)} chars), skipping refinement")
        return text

    system_instruction = """당신은 의료 상담 STT(음성인식) 텍스트 교정 전문가입니다.
오직 아래 사항만 수정하세요. 원래 내용과 의미를 절대 변경하지 마세요.

수정 사항:
1. 명백한 음성인식 오류 수정 (예: "아노" → "저기요(あの)", 의미 불명 단어 → 문맥상 추정 단어)
2. 같은 화자의 연속된 짧은 문장 합치기 (의미 단위로 병합)
3. 깨진 문법 자연스럽게 교정
4. 화자 라벨(상담사:/고객:)은 반드시 유지

금지 사항:
- 의료 내용 추가/변경/삭제 금지
- 새로운 문장 창작 금지
- 화자 라벨 제거 금지"""

    prompt = f"""다음 STT 텍스트를 정제해주세요. 정제된 텍스트만 반환하세요.

{text}"""

    try:
        result = await generate_text(prompt, system_instruction)
        refined = result.strip()
        if len(refined) < len(text) * 0.3:
            # 비정상적으로 짧아졌으면 원문 유지
            logger.warning("[Refine] Result too short, keeping original")
            return text
        logger.info(f"[Refine] {len(text)} → {len(refined)} chars")
        return refined
    except Exception as e:
        logger.warning(f"[Refine] Failed, keeping original: {str(e)[:100]}")
        return text
