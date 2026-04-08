"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Props {
  data: any;
  round?: number;
}

function SectionTitle({ number, title }: { number: number; title: string }) {
  return (
    <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
      <span className="block w-1 h-6 bg-purple-500 rounded-full"></span>
      <span className="text-purple-600 font-black mr-0.5">{String(number).padStart(2, "0")}</span>
      {title}
    </h3>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)] ${className}`}>
      {children}
    </div>
  );
}

export default function R3DirectorReport({ data, round = 3 }: Props) {
  const roundLabel = `${round}차`;
  const roleLabel = round === 2 ? "의사" : "상담실장";
  const s1 = data.section1_consultation_summary || data.section1_patient_overview;
  const s2 = data.section2_procedure_plan || data.section2_chief_complaints;
  const s3 = data.section3_cost_estimate || data.section3_mentioned_procedures;
  const s4 = data.section4_scheduling || data.section4_medical_context;
  const s5 = data.section5_considerations || data.section5_patient_concerns;
  const s6 = data.section6_action_items || data.section6_visit_intent;

  // 새 형식 (6섹션) vs 기존 형식 (7섹션) 판별
  const isNewFormat = !!data.section1_consultation_summary;

  const ctaColor = (level: string | undefined) => {
    const l = (level || "").toLowerCase();
    if (l === "hot") return "bg-red-500 text-white";
    if (l === "warm") return "bg-amber-400 text-white";
    return "bg-blue-400 text-white";
  };

  const ctaLabel = (level: string | undefined) => {
    const l = (level || "").toLowerCase();
    if (l === "hot") return "HOT";
    if (l === "warm") return "WARM";
    return "COOL";
  };

  return (
    <div className="min-h-screen bg-[#F4F2F7]">
      <div className="max-w-[480px] mx-auto bg-[#F4F2F7] min-h-screen shadow-[0_0_20px_rgba(0,0,0,0.05)]">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md sticky top-0 z-40 border-b border-purple-100 px-5 py-5">
          <div className="flex items-center justify-center gap-2 mb-4">
            <img src="/ippeo-logo.png" alt="IPPEO" className="w-5 h-5 rounded" />
            <h1 className="text-xs font-bold text-gray-500 tracking-tight">
              IPPEO | {roundLabel} 상담리포트
            </h1>
            <span className="text-[10px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
              {roleLabel}
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

          {/* Section 1: 상담 요약 */}
          {s1 && (
            <section>
              <SectionTitle number={1} title={isNewFormat ? "상담 요약" : "환자 개요"} />
              <Card className="border-l-4 border-purple-400">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">환자명</p>
                    <p className="font-bold text-gray-800 text-base">{s1.name}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">상담일</p>
                    <p className="font-medium text-gray-700">{s1.consultation_date}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">분류</p>
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-gray-700">
                      {s1.classification === "성형외과" ? "🏥" : "💊"} {s1.classification}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">CTA</p>
                    <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full ${ctaColor(s1.cta_level)}`}>
                      {ctaLabel(s1.cta_level)}
                    </span>
                  </div>
                </div>
                {(s1.round_summary || s1.summary) && (
                  <div className="mt-4 pt-4 border-t border-purple-50">
                    <p className="text-sm text-gray-700 leading-relaxed">{s1.round_summary || s1.summary}</p>
                  </div>
                )}
              </Card>
            </section>
          )}

          {/* Section 2 — 새 형식: 시술 계획, 기존: 핵심 호소 */}
          {s2 && isNewFormat && (
            <section>
              <SectionTitle number={2} title="시술 계획" />
              {Array.isArray(s2.primary_procedures) && s2.primary_procedures.length > 0 && (
                <div className="space-y-3 mb-4">
                  {s2.primary_procedures.map((proc: any, i: number) => (
                    <Card key={i} className="border-l-4 border-purple-300">
                      <span className="text-sm font-bold text-gray-800">{proc.name}</span>
                      <p className="text-sm text-gray-600 mt-1">{proc.description}</p>
                    </Card>
                  ))}
                </div>
              )}
              {Array.isArray(s2.additional_options) && s2.additional_options.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-500 mb-2 px-1 uppercase tracking-wider">추가 옵션</p>
                  <div className="space-y-2">
                    {s2.additional_options.map((opt: any, i: number) => (
                      <Card key={i}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-800">{opt.name}</span>
                          {opt.recommended && (
                            <span className="text-[10px] font-bold bg-green-100 text-green-700 px-2 py-0.5 rounded-full">추천</span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">{opt.description}</p>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Section 3 — 새 형식: 비용 견적 */}
          {s3 && isNewFormat && (
            <section>
              <SectionTitle number={3} title="비용 견적" />
              <Card>
                {Array.isArray(s3.items) && s3.items.length > 0 && (
                  <div className="space-y-2 mb-4">
                    {s3.items.map((item: any, i: number) => (
                      <div key={i} className="bg-gray-50 rounded-lg p-3 flex items-center justify-between">
                        <span className="text-sm text-gray-800">{item.procedure}</span>
                        <div className="text-right">
                          <span className="text-sm font-medium text-gray-800">{item.estimated_cost}</span>
                          {item.is_estimate && (
                            <span className="text-xs text-orange-600 ml-1">(추정치)</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {Array.isArray(s3.package_options) && s3.package_options.length > 0 && s3.package_options[0] && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-2">패키지 옵션</p>
                    {s3.package_options.map((p: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">• {p}</p>
                    ))}
                  </div>
                )}
                {s3.total_estimate && (
                  <div className="flex items-center justify-between pt-3 border-t border-gray-200 mb-2">
                    <span className="text-sm font-medium text-gray-800">총 예상 비용</span>
                    <span className="text-sm font-bold text-purple-700">{s3.total_estimate}</span>
                  </div>
                )}
                {s3.note && <p className="text-xs text-gray-500">{s3.note}</p>}
              </Card>
            </section>
          )}

          {/* Section 4 — 새 형식: 일정 계획 */}
          {s4 && isNewFormat && (
            <section>
              <SectionTitle number={4} title="일정 계획" />
              <Card>
                <div className="text-sm space-y-3">
                  <div>
                    <span className="text-gray-500">환자 희망일:</span>{" "}
                    <span className="font-medium">{s4.preferred_date}</span>
                  </div>
                  {s4.treatment_timeline && (
                    <div>
                      <span className="text-gray-500">시술 일정:</span>{" "}
                      <span className="font-medium">{s4.treatment_timeline}</span>
                    </div>
                  )}
                  {Array.isArray(s4.follow_up_plan) && s4.follow_up_plan.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">후속 일정</p>
                      <ul className="space-y-1">
                        {s4.follow_up_plan.map((f: string, i: number) => (
                          <li key={i} className="text-gray-700">• {f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </Card>
            </section>
          )}

          {/* Section 5 — 새 형식: 고려사항 */}
          {s5 && isNewFormat && (
            <section>
              <SectionTitle number={5} title="고려사항" />
              <Card>
                {Array.isArray(s5.patient_concerns) && s5.patient_concerns.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">환자 우려</p>
                    {s5.patient_concerns.map((c: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 mb-1">
                        <span className="mt-0.5 w-4 h-4 bg-amber-100 rounded flex items-center justify-center flex-shrink-0">
                          <span className="text-amber-600 text-[10px]">!</span>
                        </span>
                        <span className="text-sm text-gray-700">{c}</span>
                      </div>
                    ))}
                  </div>
                )}
                {Array.isArray(s5.negotiation_points) && s5.negotiation_points.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">협상 포인트</p>
                    {s5.negotiation_points.map((n: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">&rarr; {n}</p>
                    ))}
                  </div>
                )}
                {s5.risk_communication && (
                  <div className="bg-red-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-red-600 mb-1">리스크 전달 포인트</p>
                    <p className="text-sm text-gray-700">{s5.risk_communication}</p>
                  </div>
                )}
              </Card>
            </section>
          )}

          {/* Section 6 — 새 형식: 액션 아이템 */}
          {s6 && isNewFormat && (
            <section>
              <SectionTitle number={6} title="액션 아이템" />
              <Card>
                {Array.isArray(s6.before_visit) && s6.before_visit.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-green-600 mb-2">내원 전</p>
                    {s6.before_visit.map((a: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">✓ {a}</p>
                    ))}
                  </div>
                )}
                {Array.isArray(s6.during_consultation) && s6.during_consultation.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-purple-600 mb-2">상담 시</p>
                    {s6.during_consultation.map((a: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">✓ {a}</p>
                    ))}
                  </div>
                )}
                {Array.isArray(s6.after_consultation) && s6.after_consultation.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-blue-600 mb-2">상담 후</p>
                    {s6.after_consultation.map((a: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">✓ {a}</p>
                    ))}
                  </div>
                )}
              </Card>
            </section>
          )}

          {/* === 기존 형식(7섹션) 하위호환 렌더링 === */}
          {!isNewFormat && data.section2_chief_complaints && (
            <>
              <section>
                <SectionTitle number={2} title="핵심 호소" />
                <Card>
                  {data.section2_chief_complaints.summary && (
                    <p className="text-sm text-gray-700 mb-3">{data.section2_chief_complaints.summary}</p>
                  )}
                  {data.section2_chief_complaints.points?.map((p: string, i: number) => (
                    <p key={i} className="text-sm text-gray-700 mb-1">• {p}</p>
                  ))}
                </Card>
              </section>
              {data.section3_mentioned_procedures?.procedures?.length > 0 && (
                <section>
                  <SectionTitle number={3} title="언급 시술" />
                  {data.section3_mentioned_procedures.procedures.map((proc: any, i: number) => (
                    <Card key={i} className="mb-2 border-l-4 border-purple-200">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-bold text-gray-800">{proc.name}</span>
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{proc.patient_attitude}</span>
                      </div>
                      <p className="text-sm text-gray-600">{proc.context}</p>
                    </Card>
                  ))}
                </section>
              )}
              {data.section7_doctor_notes && (
                <section>
                  <SectionTitle number={7} title="사전 참고사항" />
                  <Card>
                    {data.section7_doctor_notes.preliminary_opinion && (
                      <div className="bg-purple-50 rounded-lg p-3 mb-3">
                        <p className="text-xs font-bold text-purple-600 mb-1">사전 소견</p>
                        <p className="text-sm text-gray-700">{data.section7_doctor_notes.preliminary_opinion}</p>
                      </div>
                    )}
                    {data.section7_doctor_notes.cautions?.map((c: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700 mb-1">• {c}</p>
                    ))}
                  </Card>
                </section>
              )}
            </>
          )}

        </div>
      </div>
    </div>
  );
}
