import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたは医療コンサルティングリポートの専門ライターです。
日本語で、中立的でありながら内容の充実したリポートを作成してください。
お客様が「自分の状況が深く理解された」と感じられるよう、各セクションを具体的かつ丁寧に記述します。

日付の解釈ルール:
- 本日の日付はプロンプト内で提供されます。必ず参照すること。
- 相談で「3月」「来月」など年を含まない日付が言及された場合、本日の日付から最も近い未来の日付として解釈すること。
- 過去の日付を来院予定日として設定しないこと。

トーン＆マナー:
- 中立的・整理型の語調を使用する（事実と分析を冷静に整理するトーン）
- 「〜です」「〜と考えられます」「〜が推奨されます」など落ち着いた表現
- 感情を煽る・過度に温かい表現は使用しない（「ご安心ください」「一緒に見つけましょう」等はNG）
- ただし「中立」とは「内容が薄い」という意味ではない。分析セクションは具体的な根拠・仕組みの説明を伴って充実させること
- 説明セクション（section2原因分析・section3提案・section4回復）は2〜3文で論理を展開し、なぜそうなるのかが伝わるように記述する
- ブレットポイントの各項目も、単語の羅列ではなく具体性のある一文にする
- セクション間で内容の重複・繰り返しを絶対に避ける（同じ情報は最も適切な1セクションにのみ）
- 価格・費用情報: 相談中に具体的な金額が言及された場合、または病院リポート(R3)の費用見積もりが提供された場合、その内容を記載する。R3費用データがある場合は「参考費用（税別）」として必ず反映すること。AIが根拠なく費用を創作してはならない。

分析の深さガイド:
- 「何が」だけでなく「なぜそうなるのか」の仕組みを、お客様にも分かる言葉で説明する
- お客様の悩みを、解剖学的・機能的な原因と結びつけて整理する
- 提案には、その施術がこのお客様の悩み・希望にどう対応するのかという根拠を添える
- 一般論ではなく、この相談で語られた具体的な内容に紐づけて記述する

医療情報の原則:
- カウンセラー/医師が相談で実際に言及した内容を最優先で記載する
- 相談で言及されていない固有の事実（医師の判断・金額・日程）は創作しない（信頼低下の原因）
- ただし、提案された施術に関する一般的な医学知識（仕組み・回復・リスク等）は、お客様の理解を助けるために具体的に補足してよい
- 医師の発言に反する内容は絶対に記載しない
- RAG資料は内容検証・知識補強用として参照するが、出典としてリポートに直接引用しない
- PubMed論文の詳細引用（citation）は不要

リポート構成（10セクション）:
1. ご相談の要点 — 核心的な悩み・希望・懸念を、それぞれ具体性のある一文で整理（4項目以内）
2. 現在の状態と原因 — 悩みの原因を、仕組みが伝わるように分析（導入1文 + 各原因2〜3文の説明リスト + 結論1文）
3. ご提案（Recommended Plan）— 1次推奨 + 必要時併用。各提案に「なぜこのお客様に適すか」の根拠を添える
4. 予想回復スケジュール — 期間別タイムライン（各期間の状態を具体的に）+ 補足（相談で言及があればその内容優先。なければ該当施術の一般的な回復経過を記載）
5. 傷跡について — 仕組みと経過が分かる具体的な説明（3項目以内）
6. 施術前の注意事項 — 理由まで添えた具体的な注意点（3項目以内）
7. リスクまとめ — 各リスクの内容と対処の方向性まで（4項目以内）
8. 予想費用範囲 — 相談中に言及された金額、またはR3費用見積もりに基づく参考費用を記載。「参考（税別）」ラベル付与。AIが根拠なく金額を創作してはならない
9. ご来院予定日 — 相談で言及された日付。なければ「未定」と記載
10. IPPEOからの一言 + 最終整理 — 行動誘導型CTA（5つの心理要素を含む）"""


async def write_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
    admin_direction: str | None = None,
    input_lang: str = "ja",
    hospital_mentions: list[dict] | None = None,
    r3_cost_data: dict | None = None,
    voice_emotion_analysis: dict | None = None,
) -> dict:
    # RAG 컨텍스트를 정리 (내용 검증용)
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【参考資料 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n施術名: {faq.get('procedure_name', '')}\n"

    if not rag_context:
        rag_context = "※参考資料なし。相談内容のみに基づいて作成してください。"

    category_note = ""
    if classification == "plastic_surgery":
        category_note = "整形外科の相談です。構造的なアプローチを中心に記述してください。"
    elif classification == "dentistry":
        category_note = "歯科の相談です。治療ステップ・通院回数・材料の選択肢（インプラント/根管治療/セラミック/矯正/ホワイトニング等）を中心に記述してください。"
    else:
        category_note = "皮膚科の相談です。治療プロトコルを中心に記述してください。"

    # 병원 비교 정보 섹션 (있을 때만)
    hospital_section = ""
    if hospital_mentions:
        hospital_section = "\n== 相談で言及された病院・クリニック情報 ==\n"
        for i, h in enumerate(hospital_mentions, 1):
            hospital_section += f"\n【病院{i}】{h.get('name', '不明')}\n"
            if h.get("procedures"):
                hospital_section += f"  施術: {', '.join(h['procedures'])}\n"
            if h.get("advantages"):
                hospital_section += f"  特長: {', '.join(h['advantages'])}\n"
            if h.get("price_info"):
                hospital_section += f"  費用: {h['price_info']}\n"
            if h.get("recovery_info"):
                hospital_section += f"  回復期間: {h['recovery_info']}\n"
            if h.get("other_details"):
                hospital_section += f"  その他: {h['other_details']}\n"

    # 관리자 재생성 지시 섹션 (있을 때만) — 프롬프트 최상단에 배치
    admin_direction_section = ""
    if admin_direction:
        admin_direction_section = f"""== 【最優先】管理者からの修正指示 ==
以下の管理者指示は、相談内容やRAGデータよりも優先されます。
リポートの全セクションにおいて、この指示を最優先で反映してください。

{admin_direction}

"""

    # 고객명에서 성만 추출 (예: "田中 陽子" → "田中")
    name_parts = customer_name.split()
    display_name = name_parts[0] if name_parts else customer_name

    # 입력 언어에 따라 상담 원문 섹션 구성
    if input_lang == "ko":
        consultation_section = f"""== 韓国語原文（相談内容）==
{original_text}"""
    else:
        consultation_section = f"""== 日本語原文（相談内容）==
{original_text}

== 韓国語翻訳（意味確認用）==
{translated_text}"""

    # 현재 일본 시간(JST) — LLM에 날짜 컨텍스트 제공
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    current_date_str = f"{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    # 추출된 비용/일정 정보를 명시적으로 전달
    cost_schedule_section = ""
    cost_mentions = intent_extraction.get("cost_mentions", [])
    visit_schedule = intent_extraction.get("visit_schedule")

    if cost_mentions:
        cost_schedule_section += "\n== 相談で確認された費用情報（必ずsection8に反映すること）==\n"
        for i, c in enumerate(cost_mentions, 1):
            cost_schedule_section += f"  {i}. {c.get('item', '不明')}: {c.get('amount', '不明')}"
            if c.get("context"):
                cost_schedule_section += f"（{c['context']}）"
            cost_schedule_section += "\n"
        cost_schedule_section += "※ 上記の費用情報はsection8_cost_estimateのitemsに必ず反映すること。省略禁止。\n"

    # R3(病院リポート)で確定された費用見積もりを反映
    if r3_cost_data and isinstance(r3_cost_data, dict):
        r3_items = r3_cost_data.get("items", [])
        if r3_items:
            cost_schedule_section += "\n== 病院リポート(R3)で確定された費用見積もり（必ずsection8に反映すること）==\n"
            for i, item in enumerate(r3_items, 1):
                if isinstance(item, dict):
                    proc = item.get("procedure", "不明")
                    cost = item.get("estimated_cost", "不明")
                    cost_schedule_section += f"  {i}. {proc}: {cost}（参考価格）\n"
                elif isinstance(item, str):
                    cost_schedule_section += f"  {i}. {item}\n"
            total = r3_cost_data.get("total_estimate")
            if total:
                cost_schedule_section += f"  合計目安: {total}\n"
            note = r3_cost_data.get("note")
            if note:
                cost_schedule_section += f"  備考: {note}\n"
            cost_schedule_section += "※ 上記のR3費用データはsection8_cost_estimateのitemsに日本語で必ず反映すること。「参考（税別）」ラベルを付けて記載。省略禁止。\n"

    if visit_schedule and isinstance(visit_schedule, dict):
        dates = visit_schedule.get("mentioned_dates", [])
        timing = visit_schedule.get("preferred_timing")
        if dates or timing:
            cost_schedule_section += f"\n== 相談で確認された来院日程（必ずsection9に反映すること）==\n"
            if dates:
                cost_schedule_section += f"  具体的な日付: {', '.join(dates)}\n"
            if timing:
                cost_schedule_section += f"  希望時期: {timing}\n"
            cost_schedule_section += f"※ 上記の日程はsection9_visit_dateに必ず反映すること。年が不明な場合は{now_jst.year}年として記載。\n"

    # 음성 감정 분석 → section10 톤 가이드 생성
    voice_tone_guide = ""
    if voice_emotion_analysis and isinstance(voice_emotion_analysis, dict):
        emotion = voice_emotion_analysis.get("overall_emotion", {})
        primary = emotion.get("primary_emotion", "") if emotion else ""
        speech = voice_emotion_analysis.get("speech_patterns", {})
        hesitation = speech.get("hesitation_level", "") if speech else ""
        vcta = voice_emotion_analysis.get("voice_cta", {})
        voice_level = vcta.get("level", "") if vcta else ""

        voice_tone_guide = "\n== 音声分析に基づくトーン調整指示（section10に反映）==\n"
        # 불안/망설임 감지 시
        if primary in ("不安", "緊張", "心配") or hesitation == "high":
            voice_tone_guide += (
                "お客様の音声から不安やためらいが感じられました。\n"
                "section10_ippeo_messageの【安心感】パラグラフで、"
                "「ご不安もあるかと思いますが、どうぞご安心ください」のような"
                "穏やかな安心感を伝えるトーンを強化してください。\n"
                "【ハードル低減】も「大きな決断に感じるかもしれませんが」と共感を入れてください。\n"
            )
        # 확신/적극적 감지 시
        elif primary in ("期待", "関心", "意欲") or voice_level == "hot":
            voice_tone_guide += (
                "お客様の音声から積極的な関心と期待が感じられました。\n"
                "section10_ippeo_messageの【行動促進】パラグラフで、"
                "具体的な次のステップへの誘導を積極的にしてください。\n"
            )
        # 무관심/소극적 감지 시
        elif primary in ("無関心", "消極") or voice_level == "cool":
            voice_tone_guide += (
                "お客様の音声からまだ慎重な姿勢が感じられました。\n"
                "section10_ippeo_messageでは押し付けにならないよう、"
                "「ご自身のペースでじっくりご検討ください」のような"
                "ゆったりとしたトーンにしてください。\n"
            )
        else:
            voice_tone_guide += (
                f"お客様の音声感情: {primary or '中立'}。\n"
                "section10_ippeo_messageのトーンをこの感情状態に合わせて調整してください。\n"
            )
        voice_tone_guide += "※ 「音声を分析しました」等の直接的な言及は絶対禁止。自然な共感として表現すること。\n"

    prompt = f"""{admin_direction_section}以下の情報を元に、10セクションの日本語リポートをJSON形式で作成してください。
中立的な語調を保ちながら、各セクションは具体的な根拠・仕組みの説明を伴って充実させてください（説明セクションは2〜3文）。
セクション間の重複は排除し、相談で実際に言及された内容を最優先に記載してください。

== 本日の日付 ==
{current_date_str}
※ 相談で月のみ言及された場合（例:「3月」）、{now_jst.year}年として解釈すること。過去の日付にならないよう注意。

== 分類 ==
{category_note}

== お客様名 ==
{display_name}様

{consultation_section}
{cost_schedule_section}
{voice_tone_guide}
== 意図抽出結果 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 参考資料（内容検証用、直接引用しない）==
{rag_context}
{hospital_section}
== 出力JSON形式 ==
{{
    "title": "{display_name}様 OOのご相談リポート",
    "date": "作成日：YYYY年M月D日",

    "section1_key_summary": {{
        "points": [
            "核心的な悩み（相談で語られた具体に触れた一文）",
            "希望する方向性（具体的に一文）",
            "主要な懸念事項（具体的に一文）",
            "改善の可能性の要約（一文）"
        ]
    }},

    "section2_cause_analysis": {{
        "intro": "悩みの原因の全体像を示す1文（例: OOが△△に見える背景には、いくつかの要因が関わっています。）",
        "causes": [
            "原因1 — 何がどう影響しているのか、仕組みが伝わるように2〜3文で説明",
            "原因2 — 同様に2〜3文で具体的に",
            "原因3 — 同様に2〜3文で具体的に"
        ],
        "conclusion": "核心整理1〜2文（例: 単純なXXではなく、YYが改善のポイントになります。）"
    }},

    "section3_recommendation": {{
        "primary": {{
            "label": "1次推奨",
            "items": [
                "推奨する施術・アプローチ1 — このお客様の悩みにどう対応するかの根拠を添えて1〜2文",
                "推奨2 — 同様に根拠を添えて1〜2文",
                "推奨3（該当すれば）"
            ]
        }},
        "secondary": {{
            "label": "必要時併用",
            "items": [
                "追加施術1 — どのような場合に併用が有効かを添えて1〜2文"
            ]
        }},
        "goal": "目標の要約1〜2文（このお客様が目指す状態を具体的に）"
    }},

    "section4_recovery": {{
        "timeline": [
            {{"period": "1〜3日", "detail": "この期間の状態・腫れ・過ごし方を具体的に1〜2文"}},
            {{"period": "7日", "detail": "この期間の状態（抜糸・むくみ等）を具体的に1〜2文"}},
            {{"period": "2〜4週", "detail": "この期間の状態・日常復帰の目安を具体的に1〜2文"}},
            {{"period": "1〜3ヶ月", "detail": "最終的な定着・経過の目安を具体的に1〜2文"}}
        ],
        "note": "スケジュールに関する補足（なければnull）"
    }},

    "section5_scar_info": {{
        "points": [
            "傷跡に関する情報1 — 位置・目立ちにくさ・経過の仕組みを具体的に1〜2文",
            "傷跡に関する情報2（1〜2文）",
            "傷跡に関する情報3（1〜2文）"
        ]
    }},

    "section6_precautions": {{
        "points": [
            "施術前注意事項1 — なぜ必要かの理由を添えて1〜2文",
            "施術前注意事項2（理由を添えて1〜2文）",
            "施術前注意事項3（理由を添えて1〜2文）"
        ]
    }},

    "section7_risks": {{
        "points": [
            "リスク1 — 内容と、どう抑える/対処するかの方向性を添えて1〜2文",
            "リスク2（1〜2文）",
            "リスク3（1〜2文）",
            "リスク4（該当すれば1〜2文）"
        ]
    }},

    "section8_cost_estimate": {{
        "items": [
            "費用情報1（例: 鼻尖形成術: 約OOO〜OOO万ウォン（参考・税別））",
            "費用情報2（例: 併用時: 追加費用発生（参考・税別））"
        ],
        "includes": "含まれる項目（例: 麻酔/検査費。言及がなければnull）",
        "note": "費用に関する補足（例: 正確なお見積もりは診察後にご案内いたします。）"
    }},

    "section9_visit_date": {{
        "date": "YYYY.MM（相談で言及された来院予定月。例: 2026.03。日付不明なら月まで記載。なければ「未定」）",
        "note": "補足説明（なければnull）"
    }},

    "section10_ippeo_message": {{
        "paragraphs": [
            "【ハードル低減】この相談の具体的な施術内容に触れながら、大げさなことではないと伝える1文。お客様の悩みに合わせた独自の表現で。",
            "【未来イメージ】お客様が相談で語った具体的な悩み・希望を踏まえて、施術後の日常の一場面を描写する1文。相談内容にない場面（旅行等）は使わないこと。",
            "【感情報酬】お客様の具体的な悩みが解消された時の心理的な満足感を1文で。相談内容に基づいた固有の表現で。",
            "【安心感】お客様のペースで検討できることを伝える1文。",
            "【行動促進】相談内容から読み取れるお客様の意欲度に合わせた、次のステップへの自然な誘導1文。"
        ],
        "final_summary": "最終整理（2文以内。お客様の目標 + 推奨方向 + スケジュール提案を簡潔に）"
    }}{f''',

    "hospital_comparison": {{
        "hospitals": [
            {{
                "name": "病院名（相談で言及された名称をそのまま使用）",
                "procedures": "対象施術（簡潔に）",
                "features": "特長・強み（1文）",
                "price": "費用情報（相談で言及された金額のみ。なければnull）",
                "recovery": "回復期間（相談で言及された内容のみ。なければnull）"
            }}
        ],
        "note": "比較に関する補足（1文。例: 詳細は来院相談時にご確認ください。）"
    }}''' if hospital_mentions else ''}
}}

重要ルール:
- section8_cost_estimate: 相談中に言及された金額、または「病院リポート(R3)で確定された費用見積もり」が提供されている場合、その内容を日本語に変換して必ず反映すること。各項目に「参考（税別）」ラベルを付けること。R3費用データも相談内容データもない場合のみitemsを空配列[]にすること。AIが根拠なく費用を創作することは禁止
- section1〜3は相談で言及された内容のみに基づくこと
- section4（回復スケジュール）: 相談で具体的な回復期間が言及された場合はその内容を優先的に記載すること（病院別の回復情報がある場合は区別して記載）。言及がない場合は、提案された施術に基づく一般的な回復経過を記載すること（「診察時に説明します」のような空回答は禁止）
- section5（傷跡）・section6（注意事項）・section7（リスク）は、相談で言及がなくても該当施術の一般的な医学情報を記載すること（空にしない）
- PubMed論文の引用（citation）は含めないこと
- 各項目は内容を充実させること（説明セクションは2〜3文、ブレットも具体性のある一文）。ただし中身のない美辞麗句で水増ししないこと。中立的な語調は維持する
- セクション間の重複・繰り返しを排除すること（同じ情報を複数セクションに書かない）
- section9_visit_date: 相談で日付が言及されていなければdateは「未定」と記載すること。日付が言及されている場合は「YYYY.MM」形式（例: 2026.03）で記載し、具体的な日付（DD）は含めないこと。本日（{current_date_str}）より過去にならないこと。「相談で確認された来院日程」セクションが提供されている場合、その内容を必ず反映すること
- pointsの配列に空文字列("")を入れないこと。内容がある項目のみ含めること
- 全10セクション必須
- section10_ippeo_message: 各paragraphは必ずこのお客様の相談内容に固有の表現で作成すること。テンプレート的な汎用文（「魅力を引き出す」「鏡を見るたびに」「旅行で写真」等）の使い回しは禁止。お客様が相談で述べた具体的な悩み・希望・施術名に言及して、この方だけに向けたメッセージにすること
- hospital_comparison: 相談で病院名が言及された場合のみ作成すること。病院情報が提供されていない場合はこのキー自体を省略すること。各病院の情報は相談で実際に言及された内容のみ記載し、AIが推測・創作してはならない"""

    # JSON 파싱 재시도 (최대 2회)
    report = None
    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            report = safe_parse_json(result)
            if isinstance(report, list):
                report = report[0] if report else {}
            break
        except json.JSONDecodeError as e:
            logger.warning(f"[ReportWriter] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                raise ValueError(f"Report JSON parse failed after 2 attempts: {str(e)}")

    # 리포트 작성일을 현재 일본 시간(JST) 기준으로 확정
    report["date"] = f"作成日：{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    # section9_visit_date 연도 후처리 검증 (과거 연도 보정)
    visit_date_section = report.get("section9_visit_date")
    if visit_date_section and isinstance(visit_date_section, dict):
        visit_date_str = visit_date_section.get("date", "")
        if visit_date_str and visit_date_str != "未定":
            year_match = re.search(r'(20\d{2})', visit_date_str)
            if year_match:
                visit_year = int(year_match.group(1))
                if visit_year < now_jst.year:
                    corrected = visit_date_str.replace(str(visit_year), str(now_jst.year))
                    report["section9_visit_date"]["date"] = corrected
                    logger.warning(f"[ReportWriter] Corrected visit date year: {visit_date_str} → {corrected}")

    return report
