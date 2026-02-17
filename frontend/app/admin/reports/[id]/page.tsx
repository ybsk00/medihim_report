"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { use } from "react";
import { reportAPI, isV2Report, type Report, type ReportData } from "@/lib/api";

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

  const reportData: ReportData | null =
    lang === "ko" ? report.report_data_ko : report.report_data;
  const consultation = report.consultations;
  const customerName = consultation?.customer_name || "고객";
  const customerEmail = consultation?.customer_email || "";

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

  const v2 = isV2Report(reportData);

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
                  <div className="bg-coral p-1 rounded">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 48 48">
                      <path d="M6 6H42L36 24L42 42H6L12 24L6 6Z" fill="currentColor" />
                    </svg>
                  </div>
                  <h1 className="text-sm font-bold text-text-dark tracking-tight font-[Noto_Sans_JP]">
                    イッポ | 化粧相談リポート
                  </h1>
                </div>
                <h2 className="text-xl font-black text-text-dark leading-tight font-[Noto_Sans_JP]">
                  {reportData.title}
                </h2>
                <p className="text-xs text-gray-500 mt-2 font-medium font-[Noto_Sans_JP]">
                  作成日：{reportData.date}
                </p>
              </div>

              <div className="p-5 space-y-8 font-[Noto_Sans_JP]">
                {/* Section 1 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "今回のご相談まとめ" : "이번 상담 정리"}
                  </h3>
                  <div className="bg-white rounded-lg p-4 card-shadow">
                    <p className="text-sm text-text-dark leading-[1.8] mb-3">
                      {reportData.section1_summary.text}
                    </p>
                    <ul className="space-y-2">
                      {reportData.section1_summary.points.map((p, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="material-symbols-outlined text-soft-blue text-[18px]">diamond</span>
                          <span className="text-sm text-text-dark">{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </section>

                {/* Section 2 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "ご希望されている方向" : "희망 방향"}
                  </h3>
                  {v2 && reportData.section2_direction.items ? (
                    <>
                      <div className="bg-white rounded-lg p-4 card-shadow mb-3">
                        <ul className="space-y-3">
                          {reportData.section2_direction.items.map((item, i) => (
                            <li key={i}>
                              <div className="flex items-start gap-2">
                                <span className="material-symbols-outlined text-coral text-[20px] flex-shrink-0 mt-0.5">check_circle</span>
                                <div>
                                  <span className="text-sm font-bold text-text-dark">{item.text}</span>
                                  {item.detail && (
                                    <p className="text-sm text-gray-600 mt-1 leading-relaxed">{item.detail}</p>
                                  )}
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                      {reportData.section2_direction.conclusion && (
                        <div className="bg-coral/10 border-l-4 border-coral p-3 rounded-r-lg mb-2">
                          <p className="text-sm text-text-dark leading-[1.8]">
                            {reportData.section2_direction.conclusion}
                          </p>
                        </div>
                      )}
                      {reportData.section2_direction.interpretation && (
                        <p className="text-sm text-gray-600 leading-relaxed px-1">
                          {reportData.section2_direction.interpretation}
                        </p>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="bg-white rounded-lg p-4 card-shadow mb-3">
                        <ul className="space-y-2">
                          {(reportData.section2_direction.desired || []).map((d, i) => (
                            <li key={i} className="flex items-center gap-2">
                              <span className="material-symbols-outlined text-coral text-[20px]">check_circle</span>
                              <span className="text-sm font-medium">{d}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      {reportData.section2_direction.quote && (
                        <div className="bg-coral/10 border-l-4 border-coral p-3 rounded-r-lg">
                          <p className="text-sm italic text-text-dark leading-relaxed">
                            {reportData.section2_direction.quote}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </section>

                {/* Section 3 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "特にお気にされていた点" : "특히 신경 쓰셨던 부분"}
                  </h3>
                  <div className="bg-white rounded-lg p-4 card-shadow space-y-3">
                    {reportData.section3_concerns.points.map((p, i) => (
                      <div key={i} className="flex items-start gap-2 border-b border-gray-50 pb-2 last:border-0">
                        <span className="material-symbols-outlined text-amber-500 flex-shrink-0">warning</span>
                        <div>
                          <p className="text-sm font-bold">{p.title}</p>
                          <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                            {p.description || p.sub}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                  {(reportData.section3_concerns.interpretation || reportData.section3_concerns.supplement) && (
                    <p className="text-sm text-gray-600 mt-3 leading-relaxed px-1">
                      {reportData.section3_concerns.interpretation || reportData.section3_concerns.supplement}
                    </p>
                  )}
                </section>

                {/* Section 4 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "医療的なご説明" : "의료적 설명"}
                  </h3>
                  {v2 ? (
                    <div className="space-y-4">
                      {reportData.section4_medical.explanations.map((e, i) => (
                        <div key={i} className="bg-white rounded-lg p-4 card-shadow">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="flex-shrink-0 w-6 h-6 bg-coral/10 text-coral rounded-full flex items-center justify-center text-xs font-bold">
                              {e.number || i + 1}
                            </span>
                            <h4 className="text-sm font-bold text-text-dark">{e.title}</h4>
                          </div>
                          <p className="text-sm text-text-dark leading-[1.8]">{e.text}</p>
                          {e.citation && (
                            <div className="mt-2 bg-slate-50 border-l-[3px] border-blue-400 rounded-r-lg p-2">
                              <p className="text-[11px] text-gray-500">
                                {e.citation.stat && (
                                  <span className="font-semibold text-blue-600">{e.citation.stat} — </span>
                                )}
                                <span className="text-gray-600">
                                  {e.citation.title}
                                  {(e.citation.journal || e.citation.year) && (
                                    <span className="text-gray-400">
                                      {" "}— {e.citation.journal || ""}{e.citation.year ? `(${e.citation.year})` : ""}
                                    </span>
                                  )}
                                </span>
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                      {reportData.section4_medical.footnote && (
                        <p className="text-[11px] text-gray-400 text-center leading-relaxed">
                          {reportData.section4_medical.footnote}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      {reportData.section4_medical.explanations.map((e, i) => (
                        <div key={i} className="bg-white p-3 rounded-lg card-shadow text-center">
                          <span className="material-symbols-outlined text-soft-blue mb-1 text-2xl">{e.icon}</span>
                          <p className="text-[10px] font-bold text-coral mb-0.5">{e.label}</p>
                          <p className="text-xs font-bold leading-tight">{e.title}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                {/* Section 5 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "ご提案の方向性" : "제안 방향"}
                  </h3>
                  <div className="space-y-3">
                    {reportData.section5_proposal.steps.map((s, i) => (
                      <div key={i} className="bg-white rounded-lg p-4 border-l-4 border-coral card-shadow">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-coral font-black text-lg italic">{s.step}</span>
                          <span className="text-sm font-bold text-text-dark">{s.title}</span>
                        </div>
                        <p className="text-sm text-gray-600 leading-[1.7]">{s.desc}</p>
                      </div>
                    ))}
                  </div>
                  {reportData.section5_proposal.context_note && (
                    <p className="text-sm text-gray-600 mt-3 leading-relaxed px-1">
                      {reportData.section5_proposal.context_note}
                    </p>
                  )}
                </section>

                {/* Section 6 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "選択肢の整理" : "선택지 정리"}
                  </h3>
                  <div className="space-y-2">
                    {/* Recommended */}
                    <OptionBlock
                      data={reportData.section6_options.recommended}
                      badge="RECOMMENDED"
                      badgeColor="bg-green-100 text-green-700"
                      borderColor="border-green-100"
                      v2={v2}
                    />
                    {/* Optional */}
                    <OptionBlock
                      data={reportData.section6_options.optional}
                      badge="SUGGESTION"
                      badgeColor="bg-blue-100 text-soft-blue"
                      borderColor="border-blue-100"
                      v2={v2}
                    />
                    {/* Unnecessary */}
                    <OptionBlock
                      data={reportData.section6_options.unnecessary}
                      badge="NOT NEEDED"
                      badgeColor="bg-gray-100 text-gray-500"
                      borderColor="border-gray-100"
                      v2={v2}
                      dimmed
                    />
                  </div>
                  {reportData.section6_options.comment && (
                    <p className="text-sm text-gray-600 text-center mt-3 leading-relaxed">
                      {reportData.section6_options.comment}
                    </p>
                  )}
                </section>

                {/* Section 7 */}
                <section>
                  <h3 className="text-base font-bold text-text-dark mb-3 flex items-center gap-2">
                    <span className="w-1 h-5 bg-coral rounded-full"></span>
                    {lang === "ja" ? "回復とスケジュールについて" : "회복 및 일정"}
                  </h3>
                  <div className="bg-white rounded-lg card-shadow overflow-hidden mb-3">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-gray-50 text-gray-500 font-bold">
                        <tr>
                          <th className="px-3 py-2">{lang === "ja" ? "期間" : "기간"}</th>
                          <th className="px-3 py-2">{lang === "ja" ? "状態・ケア" : "상태/케어"}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {reportData.section7_recovery.info.map((r, i) => (
                          <tr key={i}>
                            <td className="px-3 py-2 font-bold text-text-dark whitespace-nowrap">{r.period}</td>
                            <td className="px-3 py-2 leading-relaxed">{r.detail}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="bg-coral/5 p-4 rounded-lg border border-coral/20 text-center">
                    <p className="text-sm font-bold text-coral mb-1">
                      {lang === "ja" ? "次の一歩に向けて" : "다음 단계를 위해"}
                    </p>
                    <p className="text-sm text-text-dark leading-[1.8]">
                      {reportData.section7_recovery.closing}
                    </p>
                  </div>
                  {reportData.section7_recovery.gentle_note && (
                    <p className="text-sm text-gray-500 text-center mt-2 leading-relaxed">
                      {reportData.section7_recovery.gentle_note}
                    </p>
                  )}
                </section>
              </div>

              {/* Footer */}
              <div className="bg-white border-t border-gray-100 p-6 text-center font-[Noto_Sans_JP]">
                <div className="flex justify-center items-center gap-2 mb-4">
                  <div className="bg-coral p-1 rounded">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 48 48">
                      <path d="M6 6H42L36 24L42 42H6L12 24L6 6Z" fill="currentColor" />
                    </svg>
                  </div>
                  <span className="text-sm font-bold text-text-dark">イッポ | 化粧相談リポート</span>
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

/** 관리자 미리보기용 옵션 블록 */
function OptionBlock({
  data,
  badge,
  badgeColor,
  borderColor,
  v2,
  dimmed,
}: {
  data: { category_label?: string; items?: string[]; title?: string; desc?: string };
  badge: string;
  badgeColor: string;
  borderColor: string;
  v2: boolean;
  dimmed?: boolean;
}) {
  if (v2 && Array.isArray(data.items)) {
    return (
      <div className={`bg-white p-3 rounded-lg card-shadow border ${borderColor} ${dimmed ? "opacity-60" : ""}`}>
        <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded ${badgeColor}`}>{badge}</span>
        {data.category_label && (
          <p className={`text-sm font-bold mt-1 ${dimmed ? "text-gray-400" : "text-text-dark"}`}>
            {data.category_label}
          </p>
        )}
        <ul className="mt-1 space-y-1">
          {data.items.map((item, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className={`text-xs mt-0.5 ${dimmed ? "text-gray-300" : "text-gray-400"}`}>•</span>
              <span className={`text-sm leading-relaxed ${dimmed ? "text-gray-400" : "text-text-dark"}`}>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  // V1
  return (
    <div className={`bg-white p-3 rounded-lg card-shadow border ${borderColor} ${dimmed ? "opacity-60" : ""}`}>
      <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded ${badgeColor}`}>{badge}</span>
      <p className={`text-sm font-bold mt-1 ${dimmed ? "text-gray-400" : "text-text-dark"}`}>{data.title}</p>
      <p className={`text-[11px] mt-0.5 ${dimmed ? "text-gray-400" : "text-gray-500"}`}>{data.desc}</p>
    </div>
  );
}
