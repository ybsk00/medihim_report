"use client";

import { R1ReportData } from "@/lib/api";

interface Props {
  data: R1ReportData;
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

export default function R1DoctorReport({ data }: Props) {
  const s1 = data.section1_patient_overview;
  const s2 = data.section2_chief_complaints;
  const s3 = data.section3_mentioned_procedures;
  const s4 = data.section4_medical_context;
  const s5 = data.section5_patient_concerns;
  const s6 = data.section6_visit_intent;
  const s7 = data.section7_doctor_notes;

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
            IPPEO | 의사용 상담 브리핑
          </h1>
          <span className="text-[10px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
            Doctor
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

        {/* Section 1: 환자 개요 */}
        {s1 && (
          <section>
            <SectionTitle number={1} title="환자 개요" />
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
                  <p className="text-xs text-gray-400 font-medium">내원 의지 (CTA)</p>
                  <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full ${ctaColor(s1.cta_level)}`}>
                    {ctaLabel(s1.cta_level)}
                  </span>
                </div>
              </div>
              {s1.summary && (
                <div className="mt-4 pt-4 border-t border-purple-50">
                  <p className="text-sm text-gray-700 leading-relaxed">{s1.summary}</p>
                </div>
              )}
            </Card>
          </section>
        )}

        {/* Section 2: 핵심 호소 */}
        {s2 && (
          <section>
            <SectionTitle number={2} title="핵심 호소" />
            <Card>
              {s2.summary && (
                <p className="text-sm text-gray-700 leading-relaxed mb-4">{s2.summary}</p>
              )}
              {s2.points?.length > 0 && (
                <ul className="space-y-3">
                  {s2.points.map((p, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="mt-1 w-5 h-5 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-purple-500 text-[10px] font-bold">{i + 1}</span>
                      </span>
                      <span className="text-sm text-gray-700 leading-relaxed">{p}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </section>
        )}

        {/* Section 3: 언급 시술 */}
        {s3 && s3.procedures?.length > 0 && (
          <section>
            <SectionTitle number={3} title="언급 시술" />
            <div className="space-y-3">
              {s3.procedures.map((proc, i) => (
                <Card key={i} className="border-l-4 border-purple-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-gray-800">{proc.name}</span>
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                      proc.patient_attitude === "적극적"
                        ? "bg-green-100 text-green-700"
                        : proc.patient_attitude === "관심"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}>
                      {proc.patient_attitude}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{proc.context}</p>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Section 4: 의학적 맥락 */}
        {s4 && (
          <section>
            <SectionTitle number={4} title="의학적 맥락" />
            <Card>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">{s4.current_state}</p>
              {s4.related_history && (
                <div className="bg-purple-50 rounded-lg p-3 mb-4">
                  <p className="text-xs font-medium text-purple-600 mb-1">관련 병력</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{s4.related_history}</p>
                </div>
              )}
              {s4.key_concerns?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">주요 관심사항</p>
                  {s4.key_concerns.map((c, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="mt-0.5 w-4 h-4 bg-amber-100 rounded flex items-center justify-center flex-shrink-0">
                        <span className="text-amber-600 text-[10px]">!</span>
                      </span>
                      <span className="text-sm text-gray-700 leading-relaxed">{c}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </section>
        )}

        {/* Section 5: 환자 우려사항 */}
        {s5 && s5.concerns?.length > 0 && (
          <section>
            <SectionTitle number={5} title="환자 우려사항" />
            <Card>
              <div className="space-y-3">
                {s5.concerns.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full mt-0.5 flex-shrink-0 ${
                      item.priority === "high"
                        ? "bg-red-100 text-red-700"
                        : item.priority === "medium"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-gray-200 text-gray-600"
                    }`}>
                      {item.priority === "high" ? "높음" : item.priority === "medium" ? "보통" : "낮음"}
                    </span>
                    <span className="text-sm text-gray-700 leading-relaxed">{item.concern}</span>
                  </div>
                ))}
              </div>
            </Card>
          </section>
        )}

        {/* Section 6: 내원 의지 */}
        {s6 && (
          <section>
            <SectionTitle number={6} title="내원 의지 분석" />
            <Card className="border-l-4 border-purple-400">
              <div className="flex items-center gap-4 mb-4">
                <div className="space-y-1">
                  <p className="text-xs text-gray-400 font-medium">CTA 레벨</p>
                  <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full ${ctaColor(s6.cta_level)}`}>
                    {ctaLabel(s6.cta_level)}
                  </span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-400 font-medium">예상 방문</p>
                  <p className="text-sm font-medium text-gray-800">{s6.expected_visit}</p>
                </div>
              </div>
              {s6.evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">근거 발화</p>
                  <div className="space-y-2">
                    {s6.evidence.map((e, i) => (
                      <div key={i} className="bg-purple-50 rounded-lg px-3 py-2 flex items-start gap-2">
                        <span className="text-purple-400 text-sm mt-0.5">&ldquo;</span>
                        <p className="text-sm text-gray-700 leading-relaxed italic">{e}</p>
                        <span className="text-purple-400 text-sm mt-0.5">&rdquo;</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </section>
        )}

        {/* Section 7: 사전 참고사항 */}
        {s7 && (
          <section>
            <SectionTitle number={7} title="사전 참고사항" />
            <Card>
              {s7.preliminary_opinion && (
                <div className="bg-purple-50 border border-purple-100 rounded-lg p-4 mb-4">
                  <p className="text-xs font-bold text-purple-600 mb-1">사전 소견</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{s7.preliminary_opinion}</p>
                </div>
              )}
              {s7.recommended_tests?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">추천 검사</p>
                  <ul className="space-y-2">
                    {s7.recommended_tests.map((t, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="mt-0.5 w-4 h-4 bg-green-100 rounded flex items-center justify-center flex-shrink-0">
                          <span className="text-green-600 text-[10px]">+</span>
                        </span>
                        <span className="text-sm text-gray-700 leading-relaxed">{t}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {s7.cautions?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">주의점</p>
                  <ul className="space-y-2">
                    {s7.cautions.map((c, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="mt-0.5 w-4 h-4 bg-amber-100 rounded flex items-center justify-center flex-shrink-0">
                          <span className="text-amber-600 text-[10px]">!</span>
                        </span>
                        <span className="text-sm text-gray-700 leading-relaxed">{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </section>
        )}
      </div>

      </div>
    </div>
  );
}
