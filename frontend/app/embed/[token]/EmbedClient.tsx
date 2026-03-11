"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
import R1DoctorReport from "@/components/report-internal/R1DoctorReport";
import { type ReportData, type R1ReportData, isV3Report } from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "/api";

export default function EmbedClient({
  token,
  lang,
}: {
  token: string;
  lang: string;
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [report, setReport] = useState<any>(null);
  const [reportType, setReportType] = useState<string>("r4");
  const [currentLang, setCurrentLang] = useState(lang);
  const containerRef = useRef<HTMLDivElement>(null);
  const sectionRefs = useRef<(HTMLElement | null)[]>([]);

  // postMessage로 부모 앱과 통신
  const postToParent = useCallback((type: string, data?: Record<string, unknown>) => {
    try {
      window.parent.postMessage({ type, ...data }, "*");
    } catch {
      // iframe 아닌 경우 무시
    }
  }, []);

  // 리포트 데이터 로드
  const fetchReport = useCallback(async (fetchLang: string) => {
    try {
      setLoading(true);
      const res = await fetch(
        `${API_BASE}/public/report/embed/${token}?lang=${fetchLang}`
      );
      if (!res.ok) {
        if (res.status === 404) throw new Error("404");
        if (res.status === 410) throw new Error("410");
        throw new Error(String(res.status));
      }
      const data = await res.json();
      setReport(data.report_data);
      setReportType(data.report_type || "r4");
      setError(null);
      postToParent("REPORT_LOADED", {
        token,
        lang: fetchLang,
        reportType: data.report_type,
      });
    } catch (err) {
      if (err instanceof Error && err.message.includes("404")) {
        setError("リポートが見つかりません。");
      } else if (err instanceof Error && err.message.includes("410")) {
        setError("閲覧期限が過ぎています。");
      } else {
        setError("読み込みに失敗しました。");
      }
    } finally {
      setLoading(false);
    }
  }, [token, postToParent]);

  // 초기 로드
  useEffect(() => {
    fetchReport(currentLang);
  }, [fetchReport, currentLang]);

  // 부모 앱에서 postMessage 수신 (언어 변경 등)
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === "CHANGE_LANG") {
        const newLang = event.data.lang === "ko" ? "ko" : "ja";
        setCurrentLang(newLang);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  // 높이 변경 감지 → 부모에게 REPORT_RESIZE 전달
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        postToParent("REPORT_RESIZE", {
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [postToParent]);

  // IntersectionObserver 로 fade-in
  useEffect(() => {
    if (loading || !report) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.15 }
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    const fallback = setTimeout(() => {
      sectionRefs.current.forEach((ref) => {
        if (ref) ref.classList.add("visible");
      });
    }, 800);

    return () => {
      observer.disconnect();
      clearTimeout(fallback);
    };
  }, [loading, report]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px] font-[Noto_Sans_JP]">
        <div className="text-center">
          <div className="w-8 h-8 border-3 border-coral border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-xs text-gray-500">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex items-center justify-center min-h-[200px] font-[Noto_Sans_JP]">
        <div className="text-center px-6">
          <p className="text-sm font-bold text-gray-700 mb-1">表示できません</p>
          <p className="text-xs text-gray-500">{error || "データがありません。"}</p>
        </div>
      </div>
    );
  }

  // R1 의사용 리포트 렌더링 (자체 헤더/푸터 포함)
  if (reportType === "r1") {
    return (
      <div ref={containerRef} className="font-[Pretendard,Noto_Sans_KR,sans-serif]">
        <R1DoctorReport data={report as R1ReportData} />
      </div>
    );
  }

  const isV3 = isV3Report(report);

  if (!isV3) {
    return (
      <div ref={containerRef} className="font-[Noto_Sans_JP] bg-[#FAFAFA]">
        <div className="px-4 py-6">
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <p className="text-sm text-gray-500 text-center">
              旧形式のリポートです。再生成をお勧めします。
            </p>
          </div>
        </div>
      </div>
    );
  }

  const data = report as ReportData;

  return (
    <div ref={containerRef} className="font-[Noto_Sans_JP] bg-[#FAFAFA]">
      {/* Header */}
      <ReportHeader title={data.title} date={data.date} />

      {/* Sections */}
      <div className="px-4 py-6 space-y-8">
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

        {/* 비용 섹션 (V4) */}
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
                {data.section8_cost_estimate.note && (
                  <p className="text-xs text-gray-400 mt-2">{data.section8_cost_estimate.note}</p>
                )}
              </div>
            </section>
          </div>
        )}

        {/* 내원 예정일 */}
        <div className="fade-in-section" ref={(el) => { sectionRefs.current[8] = el; }}>
          <Section8VisitDate
            date={(data.section9_visit_date?.date ?? data.section8_visit_date?.date) || "未定"}
            note={data.section9_visit_date?.note ?? data.section8_visit_date?.note}
          />
        </div>

        {/* 이뽀 메시지 */}
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
