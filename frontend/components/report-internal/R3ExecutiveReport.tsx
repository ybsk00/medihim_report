// @ts-nocheck
// [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
"use client";

import { R3ReportData } from "@/lib/api";

interface Props {
  data: R3ReportData;
}

export default function R3ExecutiveReport({ data }: Props) {
  const p1 = data.pillar1_marketing;
  const p2 = data.pillar2_medical;
  const p3 = data.pillar3_patient_management;
  const es = data.executive_summary;

  return (
    <div className="space-y-5">
      {/* 타이틀 */}
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold text-gray-800">{data.title}</h2>
        <p className="text-sm text-gray-500">{data.date}</p>
      </div>

      {/* Executive Summary — 상단 하이라이트 */}
      {es && (
        <div className="bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl p-5 border border-orange-200">
          <h3 className="text-sm font-bold text-orange-700 mb-2">경영진 요약</h3>
          <p className="text-sm font-medium text-gray-800 mb-3">{es.one_liner}</p>
          {es.action_items?.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-orange-600">액션 아이템</span>
              {es.action_items.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-orange-500 font-bold">{i + 1}.</span>
                  <span className="text-gray-700">{item}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pillar 1: 마케팅 분석 */}
      {p1 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-orange-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-xs">1</span>
            마케팅 분석
          </h3>
          <div className="text-sm space-y-3">
            {p1.cta_assessment && (
              <div><span className="text-xs font-medium text-gray-500">CTA 평가</span><p className="text-gray-700 mt-0.5">{p1.cta_assessment}</p></div>
            )}
            {p1.patient_needs?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500">핵심 니즈</span>
                <ul className="mt-1 space-y-1">
                  {p1.patient_needs.map((n, i) => (
                    <li key={i} className="text-gray-700">• {n}</li>
                  ))}
                </ul>
              </div>
            )}
            {p1.visit_likelihood && (
              <div><span className="text-xs font-medium text-gray-500">방문 가능성</span><p className="text-gray-700 mt-0.5">{p1.visit_likelihood}</p></div>
            )}
            {p1.conversion_factors?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500">전환 요인</span>
                <ul className="mt-1 space-y-1">
                  {p1.conversion_factors.map((f, i) => (
                    <li key={i} className="text-gray-700">+ {f}</li>
                  ))}
                </ul>
              </div>
            )}
            {p1.approach_strategy && (
              <div><span className="text-xs font-medium text-gray-500">접근 전략</span><p className="text-gray-700 mt-0.5">{p1.approach_strategy}</p></div>
            )}
          </div>
        </div>
      )}

      {/* Pillar 2: 의료 분석 */}
      {p2 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-orange-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-xs">2</span>
            의료 분석
          </h3>
          <div className="text-sm space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div><span className="text-gray-500">분류:</span> <span className="font-medium">{p2.classification}</span></div>
              <div><span className="text-gray-500">복잡도:</span> <span className="font-medium">{p2.procedure_complexity}</span></div>
            </div>
            {p2.resource_summary && <p className="text-gray-700">{p2.resource_summary}</p>}
            {p2.risk_level && (
              <div><span className="text-gray-500">리스크:</span> <span className="font-medium">{p2.risk_level}</span></div>
            )}
            {p2.expected_outcome && (
              <div><span className="text-gray-500">예상 결과:</span> <span className="font-medium">{p2.expected_outcome}</span></div>
            )}
          </div>
        </div>
      )}

      {/* Pillar 3: 환자 관리 전략 */}
      {p3 && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-orange-700 mb-3 flex items-center gap-2">
            <span className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center text-xs">3</span>
            환자 관리 전략
          </h3>
          <div className="text-sm space-y-3">
            {p3.follow_up_strategy && (
              <div><span className="text-xs font-medium text-gray-500">후속 전략</span><p className="text-gray-700 mt-0.5">{p3.follow_up_strategy}</p></div>
            )}
            {p3.upsell_opportunities?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-500">업셀 기회</span>
                <ul className="mt-1 space-y-1">
                  {p3.upsell_opportunities.map((u, i) => (
                    <li key={i} className="text-gray-700">+ {u}</li>
                  ))}
                </ul>
              </div>
            )}
            {p3.visit_inducement && (
              <div><span className="text-xs font-medium text-gray-500">방문 유도</span><p className="text-gray-700 mt-0.5">{p3.visit_inducement}</p></div>
            )}
            {p3.cautions?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-red-500">유의사항</span>
                <ul className="mt-1 space-y-1">
                  {p3.cautions.map((c, i) => (
                    <li key={i} className="text-gray-700">! {c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
