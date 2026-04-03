// [비활성화] 1차 상담리포트 - 사전상담 CS용. 추후 활성화 예정
"use client";

interface R1CSReportData {
  title: string;
  date: string;
  section1_consultation_overview: {
    name: string;
    classification: string;
    consultation_date: string;
    summary: string;
  };
  section2_customer_needs: {
    main_concerns: string[];
    desired_procedures: string[];
    expectations: string;
  };
  section3_follow_up: {
    next_steps: string[];
    additional_checks: string[];
  };
}

interface Props {
  data: R1CSReportData;
}

export default function R1CSReport({ data }: Props) {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[480px] mx-auto bg-gray-50 min-h-screen p-4">
        <header className="bg-white rounded-xl p-5 mb-4 shadow-sm">
          <h1 className="text-xs font-bold text-gray-500 mb-2">IPPEO | 1차 상담리포트</h1>
          <h2 className="text-lg font-black text-gray-800">{data.title}</h2>
          <p className="text-xs text-gray-400 mt-1">{data.date}</p>
        </header>

        {data.section1_consultation_overview && (
          <div className="bg-white rounded-xl p-5 mb-4 shadow-sm">
            <h3 className="text-sm font-bold text-gray-800 mb-3">01 상담 개요</h3>
            <p className="text-sm text-gray-700">{data.section1_consultation_overview.summary}</p>
          </div>
        )}

        {data.section2_customer_needs && (
          <div className="bg-white rounded-xl p-5 mb-4 shadow-sm">
            <h3 className="text-sm font-bold text-gray-800 mb-3">02 고객 요구사항</h3>
            <ul className="space-y-1">
              {data.section2_customer_needs.main_concerns?.map((c, i) => (
                <li key={i} className="text-sm text-gray-700">• {c}</li>
              ))}
            </ul>
            {data.section2_customer_needs.expectations && (
              <p className="text-sm text-gray-600 mt-2">{data.section2_customer_needs.expectations}</p>
            )}
          </div>
        )}

        {data.section3_follow_up && (
          <div className="bg-white rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-gray-800 mb-3">03 후속 조치</h3>
            <ul className="space-y-1">
              {data.section3_follow_up.next_steps?.map((s, i) => (
                <li key={i} className="text-sm text-gray-700">• {s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
