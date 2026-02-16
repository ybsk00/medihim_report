"use client";

import { useState, useEffect, useRef, use } from "react";
import ReportHeader from "@/components/report/ReportHeader";
import Section1Summary from "@/components/report/Section1Summary";
import Section2Direction from "@/components/report/Section2Direction";
import Section3Concerns from "@/components/report/Section3Concerns";
import Section4Medical from "@/components/report/Section4Medical";
import Section5Proposal from "@/components/report/Section5Proposal";
import Section6Options from "@/components/report/Section6Options";
import Section7Recovery from "@/components/report/Section7Recovery";
import ReportFooter from "@/components/report/ReportFooter";
import { publicReportAPI, type ReportData } from "@/lib/api";

const sectionNames = [
  "まとめ",
  "方向性",
  "懸念点",
  "医療説明",
  "提案",
  "選択肢",
  "回復",
];

export default function ConsumerReportPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ReportData | null>(null);
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLElement | null)[]>([]);

  useEffect(() => {
    publicReportAPI
      .get(token)
      .then((res) => {
        setReport(res.report_data);
        // 열람 추적
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

  // Intersection Observer로 현재 섹션 감지 + fade-in 애니메이션
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

    // 모바일 안전장치: 1초 후에도 보이지 않으면 전체 visible 처리
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

  // V1/V2 호환: section2
  const s2 = report.section2_direction;
  const s2Props = s2.items
    ? { items: s2.items, conclusion: s2.conclusion, interpretation: s2.interpretation }
    : { desired: s2.desired, quote: s2.quote };

  // V1/V2 호환: section3
  const s3 = report.section3_concerns;

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
      <ReportHeader title={report.title} date={report.date} />

      {/* Sections */}
      <div className="px-5 py-8 space-y-10">
        <div className="fade-in-section" ref={(el) => { sectionRefs.current[0] = el; }}>
          <Section1Summary
            text={report.section1_summary.text}
            points={report.section1_summary.points}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[1] = el; }}>
          <Section2Direction {...s2Props} />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[2] = el; }}>
          <Section3Concerns
            points={s3.points}
            interpretation={s3.interpretation}
            supplement={s3.supplement}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[3] = el; }}>
          <Section4Medical
            explanations={report.section4_medical.explanations}
            footnote={report.section4_medical.footnote}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[4] = el; }}>
          <Section5Proposal
            steps={report.section5_proposal.steps}
            context_note={report.section5_proposal.context_note}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[5] = el; }}>
          <Section6Options
            recommended={report.section6_options.recommended}
            optional={report.section6_options.optional}
            unnecessary={report.section6_options.unnecessary}
            comment={report.section6_options.comment}
          />
        </div>

        <div className="fade-in-section" ref={(el) => { sectionRefs.current[6] = el; }}>
          <Section7Recovery
            info={report.section7_recovery.info}
            closing={report.section7_recovery.closing}
            gentle_note={report.section7_recovery.gentle_note}
          />
        </div>
      </div>

      {/* Footer */}
      <ReportFooter />
    </div>
  );
}
