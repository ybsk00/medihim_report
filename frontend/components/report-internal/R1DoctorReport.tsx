// @ts-nocheck
// [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
"use client";

import { R1ReportData } from "@/lib/api";

interface Props {
  data: R1ReportData;
}

export default function R1DoctorReport({ data }: Props) {
  const s1 = data.section1_patient_overview;
  const s2 = data.section2_chief_complaints;
  const s3 = data.section3_mentioned_procedures;
  const s4 = data.section4_medical_context;
  const s5 = data.section5_patient_concerns;
  const s6 = data.section6_visit_intent;
  const s7 = data.section7_doctor_notes;

  return (
    <div className="space-y-5">
      {/* 타이틀 */}
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold text-gray-800">{data.title}</h2>
        <p className="text-sm text-gray-500">{data.date}</p>
      </div>

      {/* Section 1: 환자 개요 */}
      {s1 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">1</span>
            환자 개요
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-gray-500">이름:</span> <span className="font-medium">{s1.name}</span></div>
            <div><span className="text-gray-500">분류:</span> <span className="font-medium">{s1.classification}</span></div>
            <div><span className="text-gray-500">CTA:</span> <span className={`font-medium ${s1.cta_level === 'HOT' || s1.cta_level === 'hot' ? 'text-red-600' : s1.cta_level === 'WARM' || s1.cta_level === 'warm' ? 'text-yellow-600' : 'text-blue-600'}`}>{s1.cta_level?.toUpperCase()}</span></div>
            <div><span className="text-gray-500">상담일:</span> <span className="font-medium">{s1.consultation_date}</span></div>
          </div>
          {s1.summary && <p className="text-sm text-gray-700 mt-3 pt-3 border-t border-gray-100">{s1.summary}</p>}
        </div>
      )}

      {/* Section 2: 핵심 호소 */}
      {s2 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">2</span>
            핵심 호소
          </h3>
          {s2.summary && <p className="text-sm text-gray-700 mb-3">{s2.summary}</p>}
          <ul className="space-y-1.5">
            {s2.points?.map((p, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-purple-400 mt-0.5">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Section 3: 언급 시술 */}
      {s3 && s3.procedures?.length > 0 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">3</span>
            언급 시술
          </h3>
          <div className="space-y-3">
            {s3.procedures.map((proc, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-800">{proc.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    proc.patient_attitude === '적극적' ? 'bg-green-100 text-green-700' :
                    proc.patient_attitude === '관심' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{proc.patient_attitude}</span>
                </div>
                <p className="text-xs text-gray-600">{proc.context}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 4: 의학적 맥락 */}
      {s4 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">4</span>
            의학적 맥락
          </h3>
          <p className="text-sm text-gray-700 mb-2">{s4.current_state}</p>
          {s4.related_history && (
            <p className="text-sm text-gray-600 mb-2">
              <span className="text-gray-500">관련 병력:</span> {s4.related_history}
            </p>
          )}
          {s4.key_concerns?.length > 0 && (
            <ul className="space-y-1.5 mt-2">
              {s4.key_concerns.map((c, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-orange-400 mt-0.5">!</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Section 5: 환자 우려사항 */}
      {s5 && s5.concerns?.length > 0 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">5</span>
            환자 우려사항
          </h3>
          <div className="space-y-2">
            {s5.concerns.map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={`text-xs px-1.5 py-0.5 rounded mt-0.5 ${
                  item.priority === 'high' ? 'bg-red-100 text-red-700' :
                  item.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{item.priority === 'high' ? '높음' : item.priority === 'medium' ? '보통' : '낮음'}</span>
                <span className="text-gray-700">{item.concern}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 6: 내원 의지 */}
      {s6 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">6</span>
            내원 의지
          </h3>
          <div className="text-sm space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">CTA:</span>
              <span className={`font-medium ${
                s6.cta_level === 'HOT' || s6.cta_level === 'hot' ? 'text-red-600' :
                s6.cta_level === 'WARM' || s6.cta_level === 'warm' ? 'text-yellow-600' : 'text-blue-600'
              }`}>{s6.cta_level?.toUpperCase()}</span>
            </div>
            <div><span className="text-gray-500">예상 방문:</span> <span className="font-medium">{s6.expected_visit}</span></div>
            {s6.evidence?.length > 0 && (
              <div className="mt-2 space-y-1">
                <span className="text-xs text-gray-500">근거 발화:</span>
                {s6.evidence.map((e, i) => (
                  <p key={i} className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">&ldquo;{e}&rdquo;</p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Section 7: 사전 참고사항 */}
      {s7 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs">7</span>
            사전 참고사항
          </h3>
          {s7.preliminary_opinion && (
            <p className="text-sm text-gray-700 mb-3">{s7.preliminary_opinion}</p>
          )}
          {s7.recommended_tests?.length > 0 && (
            <div className="mb-2">
              <span className="text-xs font-medium text-gray-500">추천 검사:</span>
              <ul className="mt-1 space-y-1">
                {s7.recommended_tests.map((t, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">+</span><span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {s7.cautions?.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-500">주의점:</span>
              <ul className="mt-1 space-y-1">
                {s7.cautions.map((c, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-orange-400 mt-0.5">!</span><span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
