"use client";

import { useState, useEffect, useRef, use } from "react";
import ReportHeader from "@/components/report/ReportHeader";
import Section1KeySummary from "@/components/report/Section1KeySummary";
import Section2CauseAnalysis from "@/components/report/Section2CauseAnalysis";
import Section3Recommendation from "@/components/report/Section3Recommendation";
import Section4Recovery from "@/components/report/Section4Recovery";
import Section5ScarInfo from "@/components/report/Section5ScarInfo";
import Section6Precautions from "@/components/report/Section6Precautions";
import Section7Risks from "@/components/report/Section7Risks";
import Section8VisitDate from "@/components/report/Section8VisitDate";
import Section9IppeoMessage from "@/components/report/Section9IppeoMessage";
import ReportFooter from "@/components/report/ReportFooter";
import { publicReportAPI, type ReportData, isV3Report } from "@/lib/api";

const sectionNames = [
  "要点",
  "原因",
  "提案",
  "回復",
  "傷跡",
  "注意",
  "リスク",
  "費用",
  "来院",
  "一言",
];

export default function ConsumerReportPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [report, setReport] = useState<any>(null);
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLElement | null)[]>([]);

  useEffect(() => {
    publicReportAPI
      .get(token)
      .then((res) => {
        setReport(res.report_data);
        publicReportAPI.opened(token).catch(() => {});
      })
      .catch((err) => {
        if (err instanceof Error && err.message.includes("404")) {
          setError("リポートが見つかりません。URLをご確認ください。");
        } else if (err instanceof Error && err.message.includes("410")) {
          setError("このリポートの閲覧期限が過ぎています。");
        } else {
          setError("リポートを読み込めません。しばらくしてからもう一度お試しください。");
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    if (loading || !report) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            const idx = sectionRefs.current.indexOf(
              entry.target as HTMLElement
            );
            if (idx >= 0) setActiveSection(idx);
          }
        });
      },
      { threshold: 0.2 }
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    const fallback = setTimeout(() => {
      sectionRefs.current.forEach((ref) => {
        if (ref) ref.classList.add("visible");
      });
    }, 1000);

    return () => {
      observer.disconnect();
      clearTimeout(fallback);
    };
  }, [loading, report]);

  if (loading) {
    return (
      <div className="mobile-container flex items-center justify-center font-[Noto_Sans_JP]">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-coral border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-sm text-gray-500">リポートを読み込んでいます...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="mobile-container flex items-center justify-center font-[Noto_Sans_JP]">
        <div className="text-center px-8">
          <span className="material-symbols-outlined text-5xl text-gray-300 mb-4">
            error_outline
          </span>
          <p className="text-base font-bold text-text-dark mb-2">
            リポートを表示できません
          </p>
          <p className="text-sm text-gray-500">{error || "データがありません。"}</p>
        </div>
      </div>
    );
  }

  // V3 (9섹션) vs V2 (레거시 7섹션) 판별
  const isV3 = isV3Report(report);

  if (!isV3) {
    // V2 레거시: 간단한 폴백 렌더링
    return (
      <div className="mobile-container font-[Noto_Sans_JP]">
        <ReportHeader title={report.title} date={report.date} />
        <div className="px-5 py-8">
          <div className="bg-white rounded-xl p-5 card-shadow">
            <p className="text-sm text-gray-500 text-center">
              このリポートは旧形式です。再生成をお勧めします。
            </p>
          </div>
        </div>
        <ReportFooter />
      </div>
    );
  }

  const data = report as ReportData;

  return (
    <div className="mobile-container font-[Noto_Sans_JP]">
      {/* Dot Navigation */}
      <nav className="dot-nav hidden sm:flex flex-col gap-2">
        {sectionNames.map((name, i) => (
          <button
            key={i}
            onClick={() =>
              sectionRefs.current[i]?.scrollIntoView({ behavior: "smooth" })
            }
            className="group flex items-center gap-2"
            title={name}
          >
            <span
              className={`block w-2 h-2 rounded-full transition-all ${
                activeSection === i
                  ? "bg-coral w-3 h-3"
                  : "bg-gray-300 group-hover:bg-gray-400"
              }`}
            ></span>
          </button>
        ))}
      </nav>

      {/* Header */}
      <ReportHeader title={data.title} date={data.date} />

      {/* Sections */}
      <div className="px-5 py-8 space-y-10">
        <div className="fade-in-section" ref={(el) => { sectionRefs.current[0] = el; }}>
          <Section1KeySummary points={data.section1_key_summary.points} />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[1] = el; }}>
          <Section2CauseAnalysis
            intro={data.section2_cause_analysis.intro}
            causes={data.section2_cause_analysis.causes}
            conclusion={data.section2_cause_analysis.conclusion}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[2] = el; }}>
          <Section3Recommendation
            primary={data.section3_recommendation.primary}
            secondary={data.section3_recommendation.secondary}
            goal={data.section3_recommendation.goal}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[3] = el; }}>
          <Section4Recovery
            timeline={data.section4_recovery.timeline}
            note={data.section4_recovery.note}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[4] = el; }}>
          <Section5ScarInfo points={data.section5_scar_info.points} />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[5] = el; }}>
          <Section6Precautions points={data.section6_precautions.points} />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[6] = el; }}>
          <Section7Risks points={data.section7_risks.points} />
        </div>

        {/* 비용 섹션 (V4, 상담에서 언급된 경우만) */}
        {data.section8_cost_estimate && data.section8_cost_estimate.items && data.section8_cost_estimate.items.length > 0 && (
          <div className="fade-in-section" ref={(el) => { sectionRefs.current[7] = el; }}>
            <section>
              <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
                <span className="block w-1 h-6 bg-coral rounded-full"></span>
                予想費用範囲
              </h3>
              <div className="bg-white rounded-xl p-5 card-shadow">
                <ul className="space-y-2">
                  {data.section8_cost_estimate.items.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                      <span className="text-sm text-text-dark">{item}</span>
                    </li>
                  ))}
                </ul>
                {data.section8_cost_estimate.includes && (
                  <p className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-100">
                    含む: {data.section8_cost_estimate.includes}
                  </p>
                )}
                {data.section8_cost_estimate.note && (
                  <p className="text-xs text-gray-400 mt-1">{data.section8_cost_estimate.note}</p>
                )}
              </div>
            </section>
          </div>
        )}

        {/* 내원 예정일 (V4: section9, V3: section8) */}
        <div className="fade-in-section" ref={(el) => { sectionRefs.current[8] = el; }}>
          <Section8VisitDate
            date={(data.section9_visit_date?.date ?? data.section8_visit_date?.date) || "未定"}
            note={data.section9_visit_date?.note ?? data.section8_visit_date?.note}
          />
        </div>

        {/* 이뻐 메시지 (V4: section10, V3: section9) */}
        <div className="fade-in-section" ref={(el) => { sectionRefs.current[9] = el; }}>
          <Section9IppeoMessage
            paragraphs={(data.section10_ippeo_message?.paragraphs ?? data.section9_ippeo_message?.paragraphs) || []}
            final_summary={(data.section10_ippeo_message?.final_summary ?? data.section9_ippeo_message?.final_summary) || ""}
          />
        </div>
      </div>

      {/* Footer */}
      <ReportFooter />
    </div>
  );
}
