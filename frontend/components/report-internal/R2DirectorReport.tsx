// @ts-nocheck
// [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
"use client";

import { R2ReportData } from "@/lib/api";

interface Props {
  data: R2ReportData;
}

export default function R2DirectorReport({ data }: Props) {
  const s1 = data.section1_procedure_summary;
  const s2 = data.section2_resource_requirements;
  const s3 = data.section3_cost_planning;
  const s4 = data.section4_scheduling;
  const s5 = data.section5_patient_readiness;

  return (
    <div className="space-y-5">
      {/* 타이틀 */}
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold text-gray-800">{data.title}</h2>
        <p className="text-sm text-gray-500">{data.date}</p>
      </div>

      {/* Section 1: 시술 요약 */}
      {s1 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-xs">1</span>
            시술 요약
          </h3>
          {s1.doctor_opinion && <p className="text-sm text-gray-700 mb-3">{s1.doctor_opinion}</p>}
          {s1.recommended_procedures?.length > 0 && (
            <div className="space-y-2">
              {s1.recommended_procedures.map((proc, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3 flex items-start justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-800">{proc.name}</span>
                    <p className="text-xs text-gray-600 mt-0.5">{proc.note}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    proc.priority === 'primary' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'
                  }`}>{proc.priority === 'primary' ? '1차' : '2차'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Section 2: 필요 리소스 */}
      {s2 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-xs">2</span>
            필요 리소스
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">장비</span>
              {s2.equipment?.map((e, i) => (
                <p key={i} className="text-gray-700">• {e}</p>
              ))}
            </div>
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">재료</span>
              {s2.materials?.map((m, i) => (
                <p key={i} className="text-gray-700">• {m}</p>
              ))}
            </div>
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">인력</span>
              <p className="text-gray-700">{s2.staff}</p>
            </div>
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">예상 시간</span>
              <p className="text-gray-700">{s2.estimated_duration}</p>
            </div>
          </div>
        </div>
      )}

      {/* Section 3: 비용 계획 */}
      {s3 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-xs">3</span>
            비용 계획
          </h3>
          {s3.items?.length > 0 && (
            <div className="space-y-2 mb-3">
              {s3.items.map((item, i) => (
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
          {s3.total_estimate && (
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              <span className="text-sm font-medium text-gray-800">총 추정 비용</span>
              <span className="text-sm font-bold text-indigo-700">{s3.total_estimate}</span>
            </div>
          )}
          {s3.note && <p className="text-xs text-gray-500 mt-2">{s3.note}</p>}
        </div>
      )}

      {/* Section 4: 일정 계획 */}
      {s4 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-xs">4</span>
            일정 계획
          </h3>
          <div className="text-sm space-y-2">
            <div><span className="text-gray-500">환자 희망일:</span> <span className="font-medium">{s4.patient_preferred_date}</span></div>
            {s4.hospitalization && (
              <div><span className="text-gray-500">입원 기간:</span> <span className="font-medium">{s4.hospitalization}</span></div>
            )}
            {s4.pre_tests?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500">사전 검사:</span>
                <ul className="mt-1 space-y-1">
                  {s4.pre_tests.map((t, i) => (
                    <li key={i} className="text-gray-700">• {t}</li>
                  ))}
                </ul>
              </div>
            )}
            {s4.follow_up?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500">후속 일정:</span>
                <ul className="mt-1 space-y-1">
                  {s4.follow_up.map((f, i) => (
                    <li key={i} className="text-gray-700">• {f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Section 5: 환자 준비도 */}
      {s5 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-indigo-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-xs">5</span>
            환자 준비도
          </h3>
          <div className="text-sm space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">CTA:</span>
              <span className={`font-medium ${
                s5.cta_level === 'HOT' || s5.cta_level === 'hot' ? 'text-red-600' :
                s5.cta_level === 'WARM' || s5.cta_level === 'warm' ? 'text-yellow-600' : 'text-blue-600'
              }`}>{s5.cta_level?.toUpperCase()}</span>
            </div>
            {s5.decision_factors?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-green-600">결정 요인</span>
                {s5.decision_factors.map((f, i) => (
                  <p key={i} className="text-gray-700 mt-0.5">+ {f}</p>
                ))}
              </div>
            )}
            {s5.barriers?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-red-600">장벽</span>
                {s5.barriers.map((b, i) => (
                  <p key={i} className="text-gray-700 mt-0.5">- {b}</p>
                ))}
              </div>
            )}
            {s5.recommended_actions?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-indigo-600">권장 조치</span>
                {s5.recommended_actions.map((a, i) => (
                  <p key={i} className="text-gray-700 mt-0.5">&rarr; {a}</p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
