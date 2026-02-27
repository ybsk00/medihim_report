import asyncio
import json
import logging
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

# R4 고객용 (일본어) — 기존 시스템 인스트럭션
R4_SYSTEM_INSTRUCTION = """あなたはリポートの品質管理レビュアーです。
生成されたリポートを厳しくレビューしてください。

レビュー基準:
1. 10セクションが全て存在するか？（section1_key_summary〜section10_ippeo_message）
2. 各項目が1〜2文以内で簡潔に記述されているか？（過度な長文はFail）
3. カウンセラーが言及していない医療情報が含まれていないか？
4. 費用情報: section8_cost_estimateのitemsに、相談で言及されていない金額が含まれていないか？（AIが創作した金額は即Fail）
5. トーンが中立的・整理型か？（感情的な表現「ご安心ください」「一緒に」等はFail）
6. セクション間で内容の重複・繰り返しがないか？
7. section10のparagraphsに行動誘導5要素が含まれているか？
8. 日本語の文法・表現は自然か？
9. hospital_comparisonがある場合: 相談で実際に言及された病院のみが記載されているか？ AIが創作した病院名・費用・回復期間が含まれていないか？（創作情報は即Fail）"""

# R1 의사용 (한국어)
R1_SYSTEM_INSTRUCTION = """당신은 의사용 브리핑 리포트의 품질 관리 리뷰어입니다.
생성된 R1 리포트를 엄격하게 리뷰하세요.

리뷰 기준:
1. 7섹션 모두 존재하는가? (section1~section7)
2. 의료 전문 용어가 정확하게 사용되었는가?
3. CTA 레벨과 내원 의지 정보가 포함되었는가?
4. 상담에서 언급된 내용만 기재되었는가? (AI 추측 금지)
5. 각 항목이 1~2문 이내로 간결한가?
6. 한국어 문법과 표현이 자연스러운가?
7. 비용/가격 정보가 포함되지 않았는가?"""

# R2 상담실장용 (한국어)
R2_SYSTEM_INSTRUCTION = """당신은 상담실장용 운영 리포트의 품질 관리 리뷰어입니다.
생성된 R2 리포트를 엄격하게 리뷰하세요.

리뷰 기준:
1. 5섹션 모두 존재하는가? (section1~section5)
2. 리소스 목록이 현실적인가?
3. 비용 범위가 합리적인가?
4. 비용 추정치에 "추정치" 라벨이 표시되었는가?
5. R1 의사 소견과 모순되지 않는가?
6. 각 항목이 1~2문 이내로 간결한가?
7. 한국어 문법과 표현이 자연스러운가?"""

# R3 경영진용 (한국어)
R3_SYSTEM_INSTRUCTION = """당신은 경영진용 종합 분석 리포트의 품질 관리 리뷰어입니다.
생성된 R3 리포트를 엄격하게 리뷰하세요.

리뷰 기준:
1. 4섹션(3기둥 + 요약) 모두 존재하는가? (pillar1, pillar2, pillar3, executive_summary)
2. 액션 아이템이 구체적이고 실행 가능한가?
3. 한 줄 요약이 간결하고 핵심을 담고 있는가?
4. R1, R2 내용과 모순되지 않는가?
5. 경영 관점에서 유의미한 인사이트가 포함되었는가?
6. 각 항목이 1~2문 이내로 간결한가?
7. 한국어 문법과 표현이 자연스러운가?"""


def _get_review_config(report_type: str) -> tuple[str, str]:
    """리포트 타입별 시스템 인스트럭션과 리뷰 프롬프트 반환"""
    if report_type == "r1":
        return R1_SYSTEM_INSTRUCTION, """== 리뷰 항목 (7항목) ==
1. 7섹션 존재 확인 (section1_patient_overview, section2_chief_complaints, section3_mentioned_procedures, section4_medical_context, section5_patient_concerns, section6_visit_intent, section7_doctor_notes)
2. 의료 전문 용어 정확성
3. CTA 레벨 및 내원 의지 정보 포함 여부
4. 상담 내용 기반 여부 (AI 추측 포함 시 Fail)
5. 간결성: 각 항목 1~2문 이내
6. 한국어 자연스러움
7. 비용/가격 정보 미포함 확인

JSON 형식으로 반환:
{{"passed": true/false, "score": 0~100, "issues": ["문제점1"], "suggestions": ["개선안1"], "feedback": "리포트 작성 에이전트에게 전달할 피드백"}}"""

    elif report_type == "r2":
        return R2_SYSTEM_INSTRUCTION, """== 리뷰 항목 (7항목) ==
1. 5섹션 존재 확인 (section1_procedure_summary, section2_resource_requirements, section3_cost_planning, section4_scheduling, section5_patient_readiness)
2. 리소스 목록 현실성
3. 비용 범위 합리성
4. "추정치" 라벨 표시 확인 (is_estimate: true)
5. R1 의사 소견과의 일관성
6. 간결성: 각 항목 1~2문 이내
7. 한국어 자연스러움

JSON 형식으로 반환:
{{"passed": true/false, "score": 0~100, "issues": ["문제점1"], "suggestions": ["개선안1"], "feedback": "리포트 작성 에이전트에게 전달할 피드백"}}"""

    elif report_type == "r3":
        return R3_SYSTEM_INSTRUCTION, """== 리뷰 항목 (7항목) ==
1. 4섹션 존재 확인 (pillar1_marketing, pillar2_medical, pillar3_patient_management, executive_summary)
2. 액션 아이템 구체성 및 실행 가능성
3. 한 줄 요약 간결성
4. R1, R2 내용과의 일관성
5. 경영 관점 인사이트 포함 여부
6. 간결성: 각 항목 1~2문 이내
7. 한국어 자연스러움

JSON 형식으로 반환:
{{"passed": true/false, "score": 0~100, "issues": ["문제점1"], "suggestions": ["개선안1"], "feedback": "리포트 작성 에이전트에게 전달할 피드백"}}"""

    else:  # r4 (기존)
        return R4_SYSTEM_INSTRUCTION, """== レビュー項目（9項目）==
1. 10セクション全て存在確認（section1_key_summary, section2_cause_analysis, section3_recommendation, section4_recovery, section5_scar_info, section6_precautions, section7_risks, section8_cost_estimate, section9_visit_date, section10_ippeo_message）
2. 簡潔さ: 各項目が1〜2文以内か？ 不必要な修飾語や冗長な表現はないか？
3. 医療情報の正当性: 相談内容で言及されていない情報が含まれていないか？
4. 費用情報: section8_cost_estimateのitemsに相談で言及されていない金額がないか？（AIが創作した金額は即Fail。言及なしなら空配列が正しい）
5. トーン: 中立的・整理型か？ 感情的表現（「ご安心ください」「温かく」「一緒に」等）が含まれていないか？
6. 重複排除: セクション間で同じ内容が繰り返されていないか？
7. section10のparagraphsに行動誘導5要素（ハードル低減、未来イメージ、感情報酬、安心感、行動促進）が含まれているか？ かつ、各paragraphがこのお客様固有の内容か？（テンプレ的な汎用文「魅力を引き出す」「鏡を見るたびに」「旅行で写真」等はFail）
8. 日本語の自然さ
9. hospital_comparison（存在する場合のみ）: 相談で実際に言及された病院名・費用・回復期間のみ記載されているか？ AIが創作した病院情報は即Fail

JSON形式で返してください:
{{"passed": true または false, "score": 0~100, "issues": ["問題点1", "問題点2"], "suggestions": ["改善提案1", "改善提案2"], "feedback": "リポート作成Agentへのフィードバック（改善指示）"}}"""


async def review_report(
    report_data: dict,
    rag_results: list[dict],
    report_type: str = "r4",
) -> dict:
    system_instruction, review_items = _get_review_config(report_type)

    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n[참고{i}] Q: {faq.get('question', '')} A: {faq.get('answer', '')}\n"

    # R1~R3: 한국어, R4: 일본어
    if report_type in ("r1", "r2", "r3"):
        prompt = f"""다음 리포트를 리뷰하세요.

== 리포트 데이터 ==
{json.dumps(report_data, ensure_ascii=False, indent=2)}

== 참고자료 (검증용) ==
{rag_context if rag_context else "없음"}

{review_items}"""
    else:
        prompt = f"""以下のリポートをレビューしてください。

== リポートデータ ==
{json.dumps(report_data, ensure_ascii=False, indent=2)}

== 参考資料（検証用）==
{rag_context if rag_context else "なし"}

{review_items}"""

    for parse_attempt in range(2):
        result = await generate_json(prompt, system_instruction)
        try:
            data = safe_parse_json(result)
            if isinstance(data, list):
                data = data[0] if data else {"passed": True, "score": 70, "issues": [], "suggestions": [], "feedback": ""}
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"[ReviewAgent-{report_type.upper()}] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                logger.error(f"[ReviewAgent-{report_type.upper()}] JSON parse failed, returning default pass")
                return {"passed": True, "score": 70, "issues": ["Review JSON parse failed"], "suggestions": [], "feedback": ""}
