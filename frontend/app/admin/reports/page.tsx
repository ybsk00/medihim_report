"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { reportAPI, type Report } from "@/lib/api";

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  draft: { label: "생성 완료", color: "bg-blue-100 text-blue-800" },
  approved: { label: "승인 완료", color: "bg-amber-100 text-amber-800" },
  rejected: { label: "반려", color: "bg-red-100 text-red-800" },
  sent: { label: "발송 완료", color: "bg-emerald-100 text-emerald-800" },
};

const CLASSIFICATION_MAP: Record<string, string> = {
  plastic_surgery: "🏥 성형외과",
  dermatology: "💊 피부과",
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reportAPI
      .list()
      .then((res) => setReports(res.data))
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <h2 className="text-xl font-bold text-slate-800">리포트 관리</h2>
      </header>

      <div className="p-8 max-w-[1400px] mx-auto w-full space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : reports.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-2 block">description</span>
              <p className="text-lg font-medium">생성된 리포트가 없습니다</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3 border-b">고객명</th>
                    <th className="px-6 py-3 border-b">분류</th>
                    <th className="px-6 py-3 border-b">상태</th>
                    <th className="px-6 py-3 border-b">발송일</th>
                    <th className="px-6 py-3 border-b">열람</th>
                    <th className="px-6 py-3 border-b text-right">액션</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {reports.map((report) => {
                    const badge = STATUS_BADGE[report.status] || {
                      label: report.status,
                      color: "bg-slate-100 text-slate-800",
                    };
                    const consultation = report.consultations;
                    return (
                      <tr key={report.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 font-medium text-slate-900">
                          {consultation?.customer_name || "—"}
                        </td>
                        <td className="px-6 py-4 text-slate-600">
                          {CLASSIFICATION_MAP[consultation?.classification || ""] || "—"}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.color}`}
                          >
                            {badge.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-500">
                          {report.email_sent_at
                            ? new Date(report.email_sent_at).toLocaleString("ko-KR", {
                                month: "2-digit",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "—"}
                        </td>
                        <td className="px-6 py-4">
                          {report.email_opened_at ? (
                            <span className="text-emerald-600 flex items-center gap-1">
                              <span className="material-symbols-outlined text-sm">visibility</span>
                              열람
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Link
                            href={`/admin/reports/${report.id}`}
                            className="text-primary text-sm font-medium hover:underline"
                          >
                            {report.status === "sent" ? "보기" : "검토"}
                          </Link>
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
