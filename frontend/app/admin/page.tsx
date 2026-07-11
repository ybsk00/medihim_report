"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { dashboardAPI, type DashboardStats } from "@/lib/api";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  registered: { label: "등록 완료", color: "text-slate-600" },
  processing: { label: "AI 분석 중", color: "text-blue-500" },
  classification_pending: { label: "분류 대기", color: "text-amber-500" },
  report_generating: { label: "리포트 생성 중", color: "text-blue-500" },
  report_ready: { label: "리포트 완료", color: "text-indigo-600" },
  report_approved: { label: "승인 완료", color: "text-emerald-600" },
  report_sent: { label: "발송 완료", color: "text-emerald-700" },
  report_failed: { label: "처리 실패", color: "text-red-500" },
};

const CLASSIFICATION_MAP: Record<string, string> = {
  plastic_surgery: "🏥 성형외과",
  dermatology: "💊 피부과",
  dentistry: "🦷 치과",
  unclassified: "⚠️ 미분류",
};

const CTA_MAP: Record<string, { label: string; color: string }> = {
  hot: { label: "Hot", color: "bg-red-100 text-red-800" },
  warm: { label: "Warm", color: "bg-amber-100 text-amber-800" },
  cool: { label: "Cool", color: "bg-slate-100 text-slate-800" },
};

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardAPI
      .stats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  const summaryCards = stats
    ? [
        {
          label: "총 상담",
          value: `${stats.total_consultations}건`,
          sub: "",
          subColor: "text-emerald-600",
          icon: "forum",
          iconBg: "bg-blue-50 text-blue-600",
        },
        {
          label: "미분류 대기",
          value: `${stats.unclassified_count}건`,
          sub: stats.unclassified_count > 0 ? "빠른 처리가 필요합니다" : "모두 처리 완료",
          subColor: stats.unclassified_count > 0 ? "text-amber-600" : "text-emerald-600",
          icon: "pending_actions",
          iconBg: "bg-amber-50 text-amber-600",
        },
        {
          label: "리포트 대기",
          value: `${stats.report_pending_count}건`,
          sub: "검토 대기 중",
          subColor: "text-slate-400",
          icon: "summarize",
          iconBg: "bg-purple-50 text-purple-600",
        },
        {
          label: "발송 완료",
          value: `${stats.sent_count}건`,
          sub: `열람률 ${stats.view_rate}%`,
          subColor: "text-primary",
          icon: "send",
          iconBg: "bg-emerald-50 text-emerald-600",
        },
      ]
    : [];

  const totalCta = stats ? stats.cta_hot + stats.cta_warm + stats.cta_cool : 0;

  return (
    <>
      {/* Header */}
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
        <h2 className="text-xl font-bold text-slate-800">대시보드</h2>
        <div className="flex items-center gap-4">
          <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full relative">
            <span className="material-symbols-outlined">notifications</span>
            {stats && stats.unclassified_count > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            )}
          </button>
          <div className="h-8 w-[1px] bg-slate-200 mx-2"></div>
          <div className="flex items-center gap-3 cursor-pointer">
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-700 leading-none">관리자님</p>
              <p className="text-xs text-slate-500 mt-1">최고 권한 계정</p>
            </div>
            <div className="size-9 rounded-full bg-primary flex items-center justify-center text-white text-sm font-bold">
              A
            </div>
          </div>
        </div>
      </header>

      <div className="p-8 max-w-[1400px] mx-auto w-full space-y-8">
        {loading && !stats ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : !stats ? (
          <div className="text-center py-20 text-slate-400">
            <span className="material-symbols-outlined text-5xl mb-4 block">cloud_off</span>
            <p className="text-lg font-medium">API 서버에 연결할 수 없습니다</p>
            <p className="text-sm mt-1">백엔드 서버가 실행 중인지 확인해주세요</p>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {summaryCards.map((card) => (
                <div
                  key={card.label}
                  className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-slate-500 text-sm font-medium">{card.label}</span>
                    <span className={`p-2 rounded-lg material-symbols-outlined ${card.iconBg}`}>
                      {card.icon}
                    </span>
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-slate-800">{card.value}</p>
                    {card.sub && (
                      <p className={`${card.subColor} text-xs font-semibold mt-1`}>{card.sub}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* CTA Analysis + Recent Table */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* CTA Analysis Card */}
              <div className="lg:col-span-1 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-lg font-bold text-slate-800 mb-6">CTA 분석 현황</h3>
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-slate-600">전체 리드 분류</span>
                      <span className="text-sm font-bold text-slate-800">{totalCta}건</span>
                    </div>
                    {totalCta > 0 && (
                      <div className="w-full h-10 bg-slate-100 rounded-lg overflow-hidden flex">
                        <div
                          className="h-full bg-red-500"
                          style={{ width: `${(stats.cta_hot / totalCta) * 100}%` }}
                        ></div>
                        <div
                          className="h-full bg-amber-400"
                          style={{ width: `${(stats.cta_warm / totalCta) * 100}%` }}
                        ></div>
                        <div
                          className="h-full bg-blue-400"
                          style={{ width: `${(stats.cta_cool / totalCta) * 100}%` }}
                        ></div>
                      </div>
                    )}
                  </div>
                  <div className="grid grid-cols-1 gap-4">
                    {[
                      { label: "Hot (적극적)", count: stats.cta_hot, pct: totalCta > 0 ? ((stats.cta_hot / totalCta) * 100).toFixed(1) : "0", color: "bg-red-500" },
                      { label: "Warm (관심)", count: stats.cta_warm, pct: totalCta > 0 ? ((stats.cta_warm / totalCta) * 100).toFixed(1) : "0", color: "bg-amber-400" },
                      { label: "Cool (잠재)", count: stats.cta_cool, pct: totalCta > 0 ? ((stats.cta_cool / totalCta) * 100).toFixed(1) : "0", color: "bg-blue-400" },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="flex items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50/50"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${item.color}`}></div>
                          <span className="text-sm text-slate-600">{item.label}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold">{item.count}건</p>
                          <p className="text-[10px] text-slate-400">{item.pct}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recent Consultations Table */}
              <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-800">최근 상담 목록</h3>
                  <Link href="/admin/consultations" className="text-primary text-sm font-semibold hover:underline">
                    전체보기
                  </Link>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                      <tr>
                        <th className="px-6 py-3 border-b">고객명</th>
                        <th className="px-6 py-3 border-b">분류</th>
                        <th className="px-6 py-3 border-b">CTA 상태</th>
                        <th className="px-6 py-3 border-b">리포트 상태</th>
                        <th className="px-6 py-3 border-b">등록일</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-sm">
                      {stats.recent_consultations.map((item) => {
                        const st = STATUS_MAP[item.status] || { label: item.status, color: "text-slate-500" };
                        const cta = item.cta_level ? CTA_MAP[item.cta_level] : null;
                        return (
                          <tr key={item.id} className="hover:bg-slate-50 transition-colors cursor-pointer">
                            <td className="px-6 py-4 font-medium text-slate-900">{item.customer_name}</td>
                            <td className="px-6 py-4 text-slate-600">
                              {CLASSIFICATION_MAP[item.classification || ""] || "—"}
                            </td>
                            <td className="px-6 py-4">
                              {cta ? (
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cta.color}`}>
                                  {cta.label}
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                            <td className={`px-6 py-4 font-medium ${st.color}`}>{st.label}</td>
                            <td className="px-6 py-4 text-slate-500">
                              {new Date(item.created_at).toLocaleDateString("ko-KR")}
                            </td>
                          </tr>
                        );
                      })}
                      {stats.recent_consultations.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                            등록된 상담이 없습니다
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-auto py-6 px-8 text-center text-slate-400 text-xs border-t border-slate-200 bg-white">
        &copy; 2026 Medihim Ippeo. All rights reserved.
      </footer>
    </>
  );
}
