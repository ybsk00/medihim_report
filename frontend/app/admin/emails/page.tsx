"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { reportAPI, type Report } from "@/lib/api";

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  approved: {
    label: "발송 대기",
    className: "bg-amber-100 text-amber-800",
  },
  sent: {
    label: "발송 완료",
    className: "bg-emerald-100 text-emerald-800",
  },
};

export default function EmailsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [sendingId, setSendingId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "approved" | "sent">("all");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await reportAPI.list();
      // approved 또는 sent 상태만 필터
      const filtered = result.data.filter(
        (r) => r.status === "approved" || r.status === "sent"
      );
      setReports(filtered);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSendEmail = async (reportId: string) => {
    if (!confirm("이메일을 발송하시겠습니까?")) return;
    setSendingId(reportId);
    try {
      const result = await reportAPI.sendEmail(reportId);
      setReports((prev) =>
        prev.map((r) =>
          r.id === reportId
            ? {
                ...r,
                status: "sent" as const,
                email_sent_at: new Date().toISOString(),
                access_token: result.access_token,
              }
            : r
        )
      );
    } catch (err) {
      alert(
        `발송 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`
      );
    } finally {
      setSendingId(null);
    }
  };

  const handleCopyLink = (accessToken: string) => {
    const url = `${window.location.origin}/report/${accessToken}`;
    navigator.clipboard.writeText(url);
    alert("링크가 복사되었습니다.");
  };

  const filteredReports = reports.filter((r) => {
    if (filter === "all") return true;
    return r.status === filter;
  });

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold text-slate-800">이메일 발송</h2>
          <span className="text-sm text-slate-400 font-medium">
            {reports.filter((r) => r.status === "approved").length}건 발송 대기
          </span>
        </div>
      </header>

      <div className="p-8 max-w-[1200px] mx-auto w-full space-y-6">
        {/* Filter */}
        <div className="flex items-center gap-3">
          {(
            [
              ["all", "전체"],
              ["approved", "발송 대기"],
              ["sent", "발송 완료"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === value
                  ? "bg-primary text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {label}
              {value === "approved" && (
                <span className="ml-1.5 bg-white/20 px-1.5 py-0.5 rounded text-xs">
                  {reports.filter((r) => r.status === "approved").length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-2 block">
                mail
              </span>
              <p className="text-lg font-medium">
                {filter === "approved"
                  ? "발송 대기 중인 리포트가 없습니다"
                  : "이메일 발송 내역이 없습니다"}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3 border-b">고객명</th>
                    <th className="px-6 py-3 border-b">이메일</th>
                    <th className="px-6 py-3 border-b">분류</th>
                    <th className="px-6 py-3 border-b">상태</th>
                    <th className="px-6 py-3 border-b">발송일시</th>
                    <th className="px-6 py-3 border-b">열람</th>
                    <th className="px-6 py-3 border-b text-right">액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {filteredReports.map((report) => {
                    const consultation = report.consultations;
                    const statusInfo = STATUS_MAP[report.status] || {
                      label: report.status,
                      className: "bg-slate-100 text-slate-600",
                    };
                    return (
                      <tr
                        key={report.id}
                        className="hover:bg-slate-50 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium text-slate-800">
                          <Link
                            href={`/admin/reports/${report.id}`}
                            className="hover:text-primary"
                          >
                            {consultation?.customer_name || "—"}
                          </Link>
                        </td>
                        <td className="px-6 py-4 text-slate-600">
                          {consultation?.customer_email || "—"}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              consultation?.classification === "dermatology"
                                ? "bg-blue-100 text-blue-800"
                                : consultation?.classification ===
                                  "plastic_surgery"
                                ? "bg-purple-100 text-purple-800"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {consultation?.classification === "dermatology"
                              ? "피부과"
                              : consultation?.classification ===
                                "plastic_surgery"
                              ? "성형외과"
                              : "미분류"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusInfo.className}`}
                          >
                            {statusInfo.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-400 text-xs whitespace-nowrap">
                          {report.email_sent_at
                            ? new Date(report.email_sent_at).toLocaleString(
                                "ko-KR",
                                {
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                }
                              )
                            : "—"}
                        </td>
                        <td className="px-6 py-4">
                          {report.status === "sent" ? (
                            report.email_opened_at ? (
                              <span className="text-emerald-600 text-xs flex items-center gap-1">
                                <span className="material-symbols-outlined text-sm">
                                  visibility
                                </span>
                                열람
                              </span>
                            ) : (
                              <span className="text-slate-400 text-xs flex items-center gap-1">
                                <span className="material-symbols-outlined text-sm">
                                  visibility_off
                                </span>
                                미열람
                              </span>
                            )
                          ) : (
                            <span className="text-slate-300 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {report.status === "approved" && (
                              <button
                                onClick={() => handleSendEmail(report.id)}
                                disabled={sendingId === report.id}
                                className="px-3 py-1.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1"
                              >
                                {sendingId === report.id ? (
                                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                ) : (
                                  <span className="material-symbols-outlined text-sm">
                                    send
                                  </span>
                                )}
                                발송
                              </button>
                            )}
                            {report.status === "sent" &&
                              report.access_token && (
                                <button
                                  onClick={() =>
                                    handleCopyLink(report.access_token!)
                                  }
                                  className="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-200 transition-colors flex items-center gap-1"
                                >
                                  <span className="material-symbols-outlined text-sm">
                                    content_copy
                                  </span>
                                  링크
                                </button>
                              )}
                            <Link
                              href={`/admin/reports/${report.id}`}
                              className="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-200 transition-colors flex items-center gap-1"
                            >
                              <span className="material-symbols-outlined text-sm">
                                visibility
                              </span>
                              보기
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
