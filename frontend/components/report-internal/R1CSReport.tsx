"use client";

interface R1ReportData {
  title: string;
  date: string;
  section1_customer_profile: {
    name: string;
    consultation_date: string;
    classification: string;
    summary: string;
  };
  section2_customer_needs: {
    main_concerns: string[];
    desired_outcome: string;
    mentioned_procedures: string[];
    urgency: string;
  };
  section3_consultation_context: {
    current_state: string;
    key_questions: string[];
    emotional_tone: string;
  };
  section4_next_steps: {
    recommended_topics: string[];
    additional_checks: string[];
    notes: string | null;
  };
}

interface Props {
  data: R1ReportData;
}

export default function R1CSReport({ data }: Props) {
  const s1 = data.section1_customer_profile;
  const s2 = data.section2_customer_needs;
  const s3 = data.section3_consultation_context;
  const s4 = data.section4_next_steps;

  const urgencyColor = (u: string) => {
    if (u === "급함") return "bg-red-100 text-red-700";
    if (u === "보통") return "bg-amber-100 text-amber-700";
    return "bg-blue-100 text-blue-700";
  };

  return (
    <div className="min-h-screen bg-[#F0F4F8]">
      <div className="max-w-[480px] mx-auto bg-[#F0F4F8] min-h-screen shadow-[0_0_20px_rgba(0,0,0,0.05)]">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md sticky top-0 z-40 border-b border-blue-100 px-5 py-5">
          <div className="flex items-center justify-center gap-2 mb-4">
            <img src="/ippeo-logo.png" alt="IPPEO" className="w-5 h-5 rounded" />
            <h1 className="text-xs font-bold text-gray-500 tracking-tight">
              IPPEO | 1차 사전상담 리포트
            </h1>
            <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              상담실장
            </span>
          </div>
          <div className="text-center">
            <h2 className="text-xl font-black text-gray-800 leading-tight">{data.title}</h2>
            <p className="text-[11px] text-gray-400 mt-2 font-medium">
              {data.date?.startsWith("작성일") ? data.date : `작성일: ${data.date}`}
            </p>
          </div>
        </header>

        {/* Sections */}
        <div className="px-4 py-6 space-y-8">

          {/* Section 1: 고객 프로필 */}
          {s1 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-blue-500 rounded-full"></span>
                <span className="text-blue-600 font-black mr-0.5">01</span>
                고객 프로필
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)] border-l-4 border-blue-400">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">고객명</p>
                    <p className="font-bold text-gray-800 text-base">{s1.name}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">상담일</p>
                    <p className="font-medium text-gray-700">{s1.consultation_date}</p>
                  </div>
                  <div className="space-y-1 col-span-2">
                    <p className="text-xs text-gray-400 font-medium">분류</p>
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-gray-700">
                      {s1.classification === "성형외과" ? "🏥" : "💊"} {s1.classification}
                    </span>
                  </div>
                </div>
                {s1.summary && (
                  <div className="mt-4 pt-4 border-t border-blue-50">
                    <p className="text-sm text-gray-700 leading-relaxed">{s1.summary}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 2: 고객 니즈 */}
          {s2 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-blue-500 rounded-full"></span>
                <span className="text-blue-600 font-black mr-0.5">02</span>
                고객 니즈
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s2.main_concerns?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">핵심 고민</p>
                    <ul className="space-y-2">
                      {s2.main_concerns.map((c, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="mt-1 w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <span className="text-blue-500 text-[10px] font-bold">{i + 1}</span>
                          </span>
                          <span className="text-sm text-gray-700 leading-relaxed">{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {s2.desired_outcome && (
                  <div className="bg-blue-50 rounded-lg p-3 mb-4">
                    <p className="text-xs font-medium text-blue-600 mb-1">희망 결과</p>
                    <p className="text-sm text-gray-700">{s2.desired_outcome}</p>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  {s2.mentioned_procedures?.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-400 font-medium mb-1">언급 시술</p>
                      <div className="flex flex-wrap gap-1">
                        {s2.mentioned_procedures.map((p, i) => (
                          <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">{p}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {s2.urgency && (
                    <div>
                      <p className="text-xs text-gray-400 font-medium mb-1">긴급도</p>
                      <span className={`text-xs font-bold px-3 py-1 rounded-full ${urgencyColor(s2.urgency)}`}>
                        {s2.urgency}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* Section 3: 상담 맥락 */}
          {s3 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-blue-500 rounded-full"></span>
                <span className="text-blue-600 font-black mr-0.5">03</span>
                상담 맥락
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s3.current_state && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">현재 상태</p>
                    <p className="text-sm text-gray-700">{s3.current_state}</p>
                  </div>
                )}
                {s3.key_questions?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">고객 질문</p>
                    {s3.key_questions.map((q, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg px-3 py-2 mb-2 flex items-start gap-2">
                        <span className="text-gray-400 text-sm mt-0.5">Q.</span>
                        <p className="text-sm text-gray-700">{q}</p>
                      </div>
                    ))}
                  </div>
                )}
                {s3.emotional_tone && (
                  <div className="bg-blue-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-blue-600 mb-1">고객 태도/감정</p>
                    <p className="text-sm text-gray-700">{s3.emotional_tone}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 4: 사전 준비사항 */}
          {s4 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-blue-500 rounded-full"></span>
                <span className="text-blue-600 font-black mr-0.5">04</span>
                사전 준비사항
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s4.recommended_topics?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">다음 상담 주제</p>
                    <ul className="space-y-2">
                      {s4.recommended_topics.map((t, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="mt-0.5 w-4 h-4 bg-green-100 rounded flex items-center justify-center flex-shrink-0">
                            <span className="text-green-600 text-[10px]">+</span>
                          </span>
                          <span className="text-sm text-gray-700">{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {s4.additional_checks?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">추가 확인</p>
                    <ul className="space-y-1">
                      {s4.additional_checks.map((c, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-amber-500 mt-0.5">&#x25B6;</span> {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {s4.notes && (
                  <div className="bg-amber-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-amber-600 mb-1">참고사항</p>
                    <p className="text-sm text-gray-700">{s4.notes}</p>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

      </div>
    </div>
  );
}
