"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { use } from "react";
import { reportAPI, isV3Report, type Report, type ReportData } from "@/lib/api";

export default function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<"ja" | "ko">("ja");
  const [translating, setTranslating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [showRegenModal, setShowRegenModal] = useState(false);
  const [regenDirection, setRegenDirection] = useState("");
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    reportAPI
      .get(id)
      .then((r) => setReport(r))
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [id]);

  const handleTranslate = async () => {
    if (!report) return;
    if (report.report_data_ko) {
      setLang("ko");
      return;
    }
    setTranslating(true);
    try {
      const result = await reportAPI.translate(id);
      setReport((prev) =>
        prev ? { ...prev, report_data_ko: result.report_data_ko } : prev
      );
      setLang("ko");
    } catch {
      alert("번역에 실패했습니다.");
    } finally {
      setTranslating(false);
    }
  };

  const handleApprove = async () => {
    if (!report) return;
    setApproving(true);
    try {
      const result = await reportAPI.approve(id);
      setReport((prev) =>
        prev
          ? {
              ...prev,
              status: "approved" as const,
              access_token: result.access_token,
            }
          : prev
      );
    } catch (err) {
      alert(`승인 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!report) return;
    setRejecting(true);
    try {
      await reportAPI.reject(id);
      setReport((prev) =>
        prev ? { ...prev, status: "rejected" as const } : prev
      );
    } catch (err) {
      alert(`반려 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setRejecting(false);
    }
  };

  const handleCopyLink = () => {
    if (!report?.access_token) return;
    const url = `${window.location.origin}/report/${report.access_token}`;
    navigator.clipboard.writeText(url);
    alert("링크가 복사되었습니다.");
    setShowShare(false);
  };

  const handleLineShare = () => {
    if (!report?.access_token) return;
    const url = `${window.location.origin}/report/${report.access_token}`;
    window.open(
      `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(url)}`,
      "_blank"
    );
    setShowShare(false);
  };

  const handleRegenerate = async () => {
    if (!report || !regenDirection.trim()) return;
    setRegenerating(true);
    try {
      await reportAPI.regenerate(id, regenDirection.trim());
      alert("리포트 재생성이 시작되었습니다. 잠시 후 페이지를 새로고침해주세요.");
      setShowRegenModal(false);
      setRegenDirection("");
      // 3초 후 자동 리로드
      setTimeout(() => {
        reportAPI
          .get(id)
          .then((r) => setReport(r))
          .catch(() => {});
      }, 3000);
    } catch (err) {
      alert(`재생성 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl mb-2 block">error</span>
          <p>리포트를 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const reportData: any = lang === "ko" ? report.report_data_ko : report.report_data;
  const consultation = report.consultations;
  const customerName = consultation?.customer_name || "고객";
  const customerEmail = consultation?.customer_email || "";
  const isV3 = reportData ? isV3Report(reportData) : false;

  if (!reportData) {
    return (
      <>
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
          <Link
            href="/admin/reports"
            className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mr-4"
          >
            <span className="material-symbols-outlined">arrow_back</span>
            <span className="text-sm">목록으로</span>
          </Link>
          <h2 className="text-xl font-bold text-slate-800">
            {customerName} 리포트
          </h2>
        </header>
        <div className="flex items-center justify-center py-20 text-slate-400">
          <div className="text-center">
            <span className="material-symbols-outlined text-5xl mb-2 block">description</span>
            <p>리포트 데이터가 없습니다</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <Link
          href="/admin/reports"
          className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mr-4"
        >
          <span className="material-symbols-outlined">arrow_back</span>
          <span className="text-sm">목록으로</span>
        </Link>
        <h2 className="text-xl font-bold text-slate-800">
          {customerName} 리포트 검토
        </h2>
      </header>

      <div className="p-8 max-w-[1200px] mx-auto w-full space-y-6">
        {/* Language Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => setLang("ja")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                lang === "ja" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500"
              }`}
            >
              일본어 원문
            </button>
            <button
              onClick={() => {
                if (lang === "ko") return;
                handleTranslate();
              }}
              disabled={translating}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1 ${
                lang === "ko"
                  ? "bg-white text-slate-800 shadow-sm"
                  : "text-slate-500"
              } ${translating ? "opacity-50" : ""}`}
            >
              {translating && (
                <div className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></div>
              )}
              한글 번역
            </button>
          </div>
        </div>

        {/* Report Preview in Mobile Frame */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
          <div className="mx-auto" style={{ maxWidth: "480px" }}>
            <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-lg bg-report-bg">
              {/* Header */}
              <div className="glass-header border-b border-gray-100 px-5 py-4">
                <div className="flex items-center gap-2 mb-3">
                  <img src="/ippeo-logo.png" alt="IPPEO" className="w-6 h-6 rounded" />
                  <h1 className="text-sm font-bold text-text-dark tracking-tight font-[Noto_Sans_JP]">
                    IPPEO | 化粧相談リポート
                  </h1>
                </div>
                <h2 className="text-xl font-black text-text-dark leading-tight font-[Noto_Sans_JP]">
                  {reportData.title}
                </h2>
                <p className="text-xs text-gray-500 mt-2 font-medium font-[Noto_Sans_JP]">
                  {reportData.date}
                </p>
              </div>

              <div className="p-5 space-y-8 font-[Noto_Sans_JP]">
                {isV3 ? (
                  <>
                    {/* V3: 9섹션 구조 */}
                    {/* Section 1 - 상담 핵심 요약 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "ご相談の要点" : "상담 핵심 요약"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow">
                        <ul className="space-y-2">
                          {reportData.section1_key_summary.points.map((p: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <img src="/heart-icon.png" alt="" className="w-4 h-4 mt-0.5" />
                              <span className="text-sm text-text-dark">{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>

                    {/* Section 2 - 현재 상태 및 원인 분석 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "現在の状態と原因" : "현재 상태 및 원인 분석"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow">
                        <p className="text-sm text-text-dark leading-relaxed mb-3">{reportData.section2_cause_analysis.intro}</p>
                        <ul className="space-y-2 mb-3">
                          {reportData.section2_cause_analysis.causes.map((c: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                              <span className="text-sm text-gray-700">{c}</span>
                            </li>
                          ))}
                        </ul>
                        <p className="text-sm font-medium text-text-dark">{reportData.section2_cause_analysis.conclusion}</p>
                      </div>
                    </section>

                    {/* Section 3 - 제안 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "ご提案 (Recommended Plan)" : "제안 결론"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow border-l-4 border-coral mb-3">
                        <p className="text-xs font-bold text-coral mb-2">&#x25C6; {reportData.section3_recommendation.primary.label}</p>
                        <ul className="space-y-1">
                          {reportData.section3_recommendation.primary.items.map((item: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                              <span className="text-sm text-text-dark">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      {reportData.section3_recommendation.secondary.items.length > 0 && (
                        <div className="bg-white rounded-lg p-4 card-shadow border-l-4 border-gray-300 mb-3">
                          <p className="text-xs font-bold text-gray-500 mb-2">&#x25C6; {reportData.section3_recommendation.secondary.label}</p>
                          <ul className="space-y-1">
                            {reportData.section3_recommendation.secondary.items.map((item: string, i: number) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                                <span className="text-sm text-gray-700">{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <p className="text-sm text-text-dark text-center font-medium">{reportData.section3_recommendation.goal}</p>
                    </section>

                    {/* Section 4 - 회복 일정 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "予想回復スケジュール" : "예상 회복 일정"}
                      </h3>
                      <div className="bg-white rounded-lg card-shadow overflow-hidden">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-gray-50 text-gray-500 font-bold">
                            <tr>
                              <th className="px-3 py-2">{lang === "ja" ? "期間" : "기간"}</th>
                              <th className="px-3 py-2">{lang === "ja" ? "状態・ケア" : "상태/케어"}</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {reportData.section4_recovery.timeline.map((r: {period: string; detail: string}, i: number) => (
                              <tr key={i}>
                                <td className="px-3 py-2 font-bold text-text-dark whitespace-nowrap">{r.period}</td>
                                <td className="px-3 py-2 leading-relaxed">{r.detail}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {reportData.section4_recovery.note && (
                        <p className="text-xs text-gray-500 mt-2 px-1">{reportData.section4_recovery.note}</p>
                      )}
                    </section>

                    {/* Section 5 - 흉터 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "傷跡について" : "흉터 관련 안내"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow">
                        <ul className="space-y-2">
                          {reportData.section5_scar_info.points.map((p: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                              <span className="text-sm text-gray-700">{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>

                    {/* Section 6 - 주의사항 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "施術前の注意事項" : "시술 전 주의사항"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow">
                        <ul className="space-y-2">
                          {reportData.section6_precautions.points.map((p: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-amber-500 text-sm">&#x26A0;</span>
                              <span className="text-sm text-gray-700">{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>

                    {/* Section 7 - 리스크 */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "リスクまとめ" : "리스크 요약"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow">
                        <ul className="space-y-2">
                          {reportData.section7_risks.points.map((p: string, i: number) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                              <span className="text-sm text-gray-700">{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>

                    {/* Section 8 - 예상 비용 범위 (V4, 상담에서 언급된 경우만) */}
                    {reportData.section8_cost_estimate?.items?.length > 0 && (
                      <section>
                        <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                          <span className="w-1 h-5 bg-coral rounded-full"></span>
                          {lang === "ja" ? "予想費用範囲" : "예상 비용 범위"}
                        </h3>
                        <div className="bg-white rounded-lg p-4 card-shadow">
                          <ul className="space-y-2">
                            {reportData.section8_cost_estimate.items.map((item: string, i: number) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                                <span className="text-sm text-text-dark">{item}</span>
                              </li>
                            ))}
                          </ul>
                          {reportData.section8_cost_estimate.includes && (
                            <p className="text-xs text-gray-500 mt-3 pt-2 border-t border-gray-100">
                              {lang === "ja" ? "含む" : "포함"}: {reportData.section8_cost_estimate.includes}
                            </p>
                          )}
                          {reportData.section8_cost_estimate.note && (
                            <p className="text-xs text-gray-400 mt-1">{reportData.section8_cost_estimate.note}</p>
                          )}
                        </div>
                      </section>
                    )}

                    {/* Section 9 - 내원 예정일 (V4: section9, V3: section8) */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "ご来院予定日" : "내원 예정일"}
                      </h3>
                      <div className="bg-white rounded-lg p-4 card-shadow text-center">
                        <p className="text-xl font-black text-text-dark">
                          {(reportData.section9_visit_date?.date ?? reportData.section8_visit_date?.date) || (lang === "ja" ? "未定" : "미정")}
                        </p>
                        {(reportData.section9_visit_date?.note ?? reportData.section8_visit_date?.note) && (
                          <p className="text-xs text-gray-500 mt-1">
                            {reportData.section9_visit_date?.note ?? reportData.section8_visit_date?.note}
                          </p>
                        )}
                      </div>
                    </section>

                    {/* Section 10 - 이뻐의 한마디 (V4: section10, V3: section9) */}
                    <section>
                      <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                        <span className="w-1 h-5 bg-coral rounded-full"></span>
                        {lang === "ja" ? "IPPEOからの一言" : "이뻐의 한마디"}
                      </h3>
                      <div className="bg-coral/5 border border-coral/20 rounded-lg p-4 space-y-3">
                        {(reportData.section10_ippeo_message?.paragraphs ?? reportData.section9_ippeo_message?.paragraphs ?? []).map((p: string, i: number) => (
                          <p key={i} className="text-sm text-text-dark leading-relaxed">{p}</p>
                        ))}
                      </div>
                      <div className="mt-4 bg-white rounded-lg p-4 card-shadow border-l-4 border-coral">
                        <p className="text-xs font-bold text-coral mb-1">&#x1F4CC; {lang === "ja" ? "最終整理" : "최종 정리"}</p>
                        <p className="text-sm font-medium text-text-dark leading-relaxed">
                          {(reportData.section10_ippeo_message?.final_summary ?? reportData.section9_ippeo_message?.final_summary) || ""}
                        </p>
                      </div>
                    </section>
                  </>
                ) : (
                  /* V2 레거시 렌더링 */
                  <div className="text-center py-8">
                    <p className="text-sm text-gray-500">이 리포트는 구 형식(V2)입니다. 재생성을 권장합니다.</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="bg-white border-t border-gray-100 p-6 text-center font-[Noto_Sans_JP]">
                <div className="flex justify-center items-center gap-2 mb-4">
                  <img src="/ippeo-logo.png" alt="IPPEO" className="w-6 h-6 rounded" />
                  <span className="text-sm font-bold text-text-dark">IPPEO | 化粧相談リポート</span>
                </div>
                <p className="text-[10px] text-gray-400 leading-relaxed">
                  本リポートはカウンセリング時の内容を元に作成されたものであり、確定的な診断や治療を保証するものではありません。
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        {report.status === "draft" && (
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={handleReject}
              disabled={rejecting}
              className="px-6 py-2.5 bg-red-500 text-white rounded-lg text-sm font-semibold hover:bg-red-600 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {rejecting && (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              )}
              <span className="material-symbols-outlined text-lg">close</span>
              반려
            </button>
            <button
              onClick={() => setShowRegenModal(true)}
              className="px-6 py-2.5 bg-amber-500 text-white rounded-lg text-sm font-semibold hover:bg-amber-600 transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-lg">refresh</span>
              재생성
            </button>
            <button
              onClick={handleApprove}
              disabled={approving}
              className="px-6 py-2.5 bg-emerald-500 text-white rounded-lg text-sm font-semibold hover:bg-emerald-600 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {approving && (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              )}
              <span className="material-symbols-outlined text-lg">check</span>
              승인
            </button>
          </div>
        )}

        {/* Approved Info */}
        {report.status === "approved" && (
          <div className="bg-white rounded-xl border border-emerald-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 text-emerald-600">
              <span className="material-symbols-outlined">check_circle</span>
              <span className="text-sm font-semibold">승인 완료</span>
            </div>
            <p className="text-sm text-slate-500">
              이메일 발송은 <Link href="/admin/emails" className="text-primary underline">이메일 발송</Link> 메뉴에서 진행하세요.
            </p>

            <div className="relative inline-block">
              <button
                onClick={() => setShowShare(!showShare)}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                <span className="material-symbols-outlined text-lg">share</span>
                URL 공유
              </button>
              {showShare && (
                <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-lg border border-slate-200 py-1 w-48 z-20">
                  <button
                    onClick={handleCopyLink}
                    className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-lg">content_copy</span>
                    링크 복사
                  </button>
                  <button
                    onClick={handleLineShare}
                    className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-lg">chat</span>
                    LINE으로 공유
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sent Info */}
        {report.status === "sent" && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 text-emerald-600">
              <span className="material-symbols-outlined">check_circle</span>
              <span className="text-sm font-semibold">
                이메일 발송 완료 ({customerEmail})
              </span>
            </div>

            <div className="relative inline-block">
              <button
                onClick={() => setShowShare(!showShare)}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                <span className="material-symbols-outlined text-lg">share</span>
                URL 공유
              </button>
              {showShare && (
                <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-lg border border-slate-200 py-1 w-48 z-20">
                  <button
                    onClick={handleCopyLink}
                    className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-lg">content_copy</span>
                    링크 복사
                  </button>
                  <button
                    onClick={handleLineShare}
                    className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                  >
                    <span className="material-symbols-outlined text-lg">chat</span>
                    LINE으로 공유
                  </button>
                </div>
              )}
            </div>

            <div className="border-t border-slate-100 pt-4 space-y-2">
              {report.email_sent_at && (
                <p className="text-sm text-slate-600 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm text-slate-400">email</span>
                  이메일 발송{" "}
                  {new Date(report.email_sent_at).toLocaleString("ko-KR", {
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}{" "}
                </p>
              )}
              {report.email_opened_at ? (
                <p className="text-sm text-emerald-600 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">visibility</span>
                  이메일 열람{" "}
                  {new Date(report.email_opened_at).toLocaleString("ko-KR", {
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              ) : (
                <p className="text-sm text-slate-400 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">visibility_off</span>
                  미열람
                </p>
              )}
            </div>
          </div>
        )}

        {/* Rejected Info */}
        {report.status === "rejected" && (
          <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center gap-2 text-red-600">
              <span className="material-symbols-outlined">cancel</span>
              <span className="text-sm font-semibold">반려된 리포트입니다</span>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowRegenModal(true)}
                className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-semibold hover:bg-amber-600 transition-colors flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-lg">refresh</span>
                피드백으로 재생성
              </button>
              <button
                onClick={handleApprove}
                disabled={approving}
                className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-semibold hover:bg-emerald-600 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-lg">check</span>
                이대로 승인
              </button>
            </div>
          </div>
        )}

        {/* Regeneration Modal */}
        {showRegenModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg mx-4">
              <h3 className="text-lg font-bold text-slate-800 mb-2">리포트 재생성</h3>
              <p className="text-sm text-slate-500 mb-4">
                원하는 수정 방향을 한국어로 입력해주세요. AI가 이 피드백을 반영하여 리포트를 다시 생성합니다.
              </p>
              <textarea
                value={regenDirection}
                onChange={(e) => setRegenDirection(e.target.value)}
                placeholder="예: 코 재수술 부분을 더 자세하게 설명하고, 회복기간을 강조해주세요"
                className="w-full h-32 border border-slate-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <div className="flex justify-end gap-3 mt-4">
                <button
                  onClick={() => {
                    setShowRegenModal(false);
                    setRegenDirection("");
                  }}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  취소
                </button>
                <button
                  onClick={handleRegenerate}
                  disabled={regenerating || !regenDirection.trim()}
                  className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-semibold hover:bg-amber-600 transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {regenerating ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <span className="material-symbols-outlined text-lg">smart_toy</span>
                  )}
                  재생성 시작
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

    </>
  );
}

