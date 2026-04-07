"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Props {
  data: any;
}

export default function R2DirectorReport({ data }: Props) {
  const s1 = data.section1_patient_summary;
  const s2 = data.section2_medical_assessment;
  const s3 = data.section3_treatment_options;
  const s4 = data.section4_clinical_considerations;
  const s5 = data.section5_pre_consultation_notes;

  return (
    <div className="min-h-screen bg-[#EEEDF5]">
      <div className="max-w-[480px] mx-auto bg-[#EEEDF5] min-h-screen shadow-[0_0_20px_rgba(0,0,0,0.05)]">
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-md sticky top-0 z-40 border-b border-indigo-100 px-5 py-5">
          <div className="flex items-center justify-center gap-2 mb-4">
            <img src="/ippeo-logo.png" alt="IPPEO" className="w-5 h-5 rounded" />
            <h1 className="text-xs font-bold text-gray-500 tracking-tight">
              IPPEO | 2차 의사용 리포트
            </h1>
            <span className="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
              의사
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

          {/* Section 1: 환자 요약 */}
          {s1 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-indigo-500 rounded-full"></span>
                <span className="text-indigo-600 font-black mr-0.5">01</span>
                환자 요약
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)] border-l-4 border-indigo-400">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium">환자명</p>
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
                {s1.chief_complaint && (
                  <div className="mt-4 pt-4 border-t border-indigo-50">
                    <p className="text-xs font-medium text-indigo-600 mb-1">주소 (Chief Complaint)</p>
                    <p className="text-sm text-gray-700 leading-relaxed">{s1.chief_complaint}</p>
                  </div>
                )}
                {s1.consultation_history && (
                  <div className="mt-3 bg-indigo-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-indigo-600 mb-1">이전 상담 이력</p>
                    <p className="text-sm text-gray-700">{s1.consultation_history}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 2: 의학적 평가 */}
          {s2 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-indigo-500 rounded-full"></span>
                <span className="text-indigo-600 font-black mr-0.5">02</span>
                의학적 평가
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s2.current_condition && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">현재 상태</p>
                    <p className="text-sm text-gray-700 leading-relaxed">{s2.current_condition}</p>
                  </div>
                )}
                {s2.relevant_history && (
                  <div className="bg-indigo-50 rounded-lg p-3 mb-4">
                    <p className="text-xs font-medium text-indigo-600 mb-1">관련 병력</p>
                    <p className="text-sm text-gray-700">{s2.relevant_history}</p>
                  </div>
                )}
                {s2.key_findings?.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">핵심 소견</p>
                    <ul className="space-y-2">
                      {s2.key_findings.map((f: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="mt-0.5 w-4 h-4 bg-indigo-100 rounded flex items-center justify-center flex-shrink-0">
                            <span className="text-indigo-600 text-[10px] font-bold">{i + 1}</span>
                          </span>
                          <span className="text-sm text-gray-700">{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 3: 시술 옵션 */}
          {s3 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-indigo-500 rounded-full"></span>
                <span className="text-indigo-600 font-black mr-0.5">03</span>
                시술 옵션
              </h3>
              <div className="space-y-3">
                {s3.recommended_procedures?.map((proc: any, i: number) => (
                  <div key={i} className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)] border-l-4 border-indigo-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-bold text-gray-800">{proc.name}</span>
                      <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                        proc.priority === "primary" ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600"
                      }`}>
                        {proc.priority === "primary" ? "1차 추천" : "대안"}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{proc.rationale}</p>
                  </div>
                ))}
                {s3.alternative_approaches?.length > 0 && s3.alternative_approaches[0] && (
                  <div className="bg-white rounded-xl p-4 shadow-sm">
                    <p className="text-xs font-medium text-gray-500 mb-2">대안 접근법</p>
                    {s3.alternative_approaches.map((a: string, i: number) => (
                      <p key={i} className="text-sm text-gray-700">• {a}</p>
                    ))}
                  </div>
                )}
                {s3.contraindications?.length > 0 && s3.contraindications[0] && (
                  <div className="bg-red-50 rounded-xl p-4">
                    <p className="text-xs font-medium text-red-600 mb-2">금기사항/주의</p>
                    {s3.contraindications.map((c: string, i: number) => (
                      <p key={i} className="text-sm text-red-700">⚠ {c}</p>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 4: 임상 고려사항 */}
          {s4 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-indigo-500 rounded-full"></span>
                <span className="text-indigo-600 font-black mr-0.5">04</span>
                임상 고려사항
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s4.risk_factors?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">위험 요소</p>
                    {s4.risk_factors.map((r: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 mb-1">
                        <span className="mt-0.5 w-4 h-4 bg-amber-100 rounded flex items-center justify-center flex-shrink-0">
                          <span className="text-amber-600 text-[10px]">!</span>
                        </span>
                        <span className="text-sm text-gray-700">{r}</span>
                      </div>
                    ))}
                  </div>
                )}
                {s4.expected_outcome && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">예상 결과</p>
                    <p className="text-sm text-gray-700">{s4.expected_outcome}</p>
                  </div>
                )}
                {s4.recovery_overview && (
                  <div className="bg-green-50 rounded-lg p-3">
                    <p className="text-xs font-medium text-green-600 mb-1">회복 개요</p>
                    <p className="text-sm text-gray-700">{s4.recovery_overview}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Section 5: 진료 전 참고 */}
          {s5 && (
            <section>
              <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-indigo-500 rounded-full"></span>
                <span className="text-indigo-600 font-black mr-0.5">05</span>
                진료 전 참고
              </h3>
              <div className="bg-white rounded-xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                {s5.recommended_tests?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">추천 검사</p>
                    <ul className="space-y-2">
                      {s5.recommended_tests.map((t: string, i: number) => (
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
                {s5.patient_readiness && (
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 mb-1">환자 준비도</p>
                    <p className="text-sm text-gray-700">{s5.patient_readiness}</p>
                  </div>
                )}
                {s5.doctor_notes && (
                  <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
                    <p className="text-xs font-bold text-indigo-600 mb-1">의사 참고 메모</p>
                    <p className="text-sm text-gray-700 leading-relaxed">{s5.doctor_notes}</p>
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
