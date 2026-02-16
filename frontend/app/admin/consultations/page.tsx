"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { consultationAPI, type Consultation } from "@/lib/api";

const CLASSIFICATION_MAP: Record<string, string> = {
  plastic_surgery: "🏥 성형외과",
  dermatology: "💊 피부과",
  unclassified: "⚠️ 미분류",
};

const CTA_MAP: Record<string, { label: string; color: string }> = {
  hot: { label: "Hot", color: "bg-red-100 text-red-800" },
  warm: { label: "Warm", color: "bg-amber-100 text-amber-800" },
  cool: { label: "Cool", color: "bg-slate-100 text-slate-800" },
};

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  processing: { label: "처리 중", color: "text-blue-500" },
  classification_pending: { label: "분류 대기", color: "text-slate-400" },
  report_generating: { label: "리포트 생성 중", color: "text-blue-500" },
  report_ready: { label: "승인 대기", color: "text-amber-600" },
  report_approved: { label: "승인 완료", color: "text-emerald-600" },
  report_sent: { label: "발송 완료", color: "text-emerald-600" },
  report_failed: { label: "처리 실패", color: "text-red-500" },
};

export default function ConsultationsPage() {
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(pageSize),
      };
      if (categoryFilter !== "all") params.classification = categoryFilter;
      if (statusFilter !== "all") params.status = statusFilter;

      const result = await consultationAPI.list(params);
      setConsultations(result.data);
      setTotal(result.total);
    } catch {
      setConsultations([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, categoryFilter, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = search
    ? consultations.filter(
        (c) =>
          c.customer_name.includes(search) || c.customer_email.includes(search)
      )
    : consultations;

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
        <h2 className="text-xl font-bold text-slate-800">상담 관리</h2>
        <div className="flex items-center gap-4">
          <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full relative">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <div className="h-8 w-[1px] bg-slate-200 mx-2"></div>
          <div className="flex items-center gap-3">
            <p className="text-sm font-semibold text-slate-700">관리자님</p>
            <div className="size-9 rounded-full bg-primary flex items-center justify-center text-white text-sm font-bold">
              A
            </div>
          </div>
        </div>
      </header>

      <div className="p-8 max-w-[1400px] mx-auto w-full space-y-6">
        {/* Action Bar */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-1">
            <div className="relative flex-1 max-w-sm">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">
                search
              </span>
              <input
                type="text"
                placeholder="고객명 또는 이메일 검색..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(1);
              }}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">분류 전체</option>
              <option value="plastic_surgery">🏥 성형외과</option>
              <option value="dermatology">💊 피부과</option>
              <option value="unclassified">⚠️ 미분류</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">상태 전체</option>
              <option value="report_sent">발송 완료</option>
              <option value="report_ready">승인 대기</option>
              <option value="classification_pending">분류 대기</option>
              <option value="processing">처리 중</option>
              <option value="report_failed">처리 실패</option>
            </select>
          </div>
          <Link
            href="/admin/consultations/new"
            className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-lg">add</span>
            새 상담 등록
          </Link>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-6 py-3 border-b w-10">
                        <input type="checkbox" className="rounded border-slate-300" />
                      </th>
                      <th className="px-6 py-3 border-b">고객명</th>
                      <th className="px-6 py-3 border-b">이메일</th>
                      <th className="px-6 py-3 border-b">분류</th>
                      <th className="px-6 py-3 border-b">CTA</th>
                      <th className="px-6 py-3 border-b">상태</th>
                      <th className="px-6 py-3 border-b">등록일</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-sm">
                    {filtered.map((item) => {
                      const st = STATUS_MAP[item.status] || { label: item.status, color: "text-slate-500" };
                      const cta = item.cta_level ? CTA_MAP[item.cta_level] : null;
                      return (
                        <tr key={item.id} className="hover:bg-slate-50 transition-colors cursor-pointer">
                          <td className="px-6 py-4">
                            <input type="checkbox" className="rounded border-slate-300" />
                          </td>
                          <td className="px-6 py-4">
                            <Link
                              href={`/admin/consultations/${item.id}`}
                              className="font-medium text-slate-900 hover:text-primary"
                            >
                              {item.customer_name}
                            </Link>
                          </td>
                          <td className="px-6 py-4 text-slate-500">{item.customer_email}</td>
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
                    {filtered.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                          상담 데이터가 없습니다
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  전체 {total}건 중 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)}건 표시
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &lt;
                  </button>
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-3 py-1 text-sm rounded ${
                        p === page ? "bg-primary text-white" : "text-slate-500 hover:bg-slate-100"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="px-3 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &gt;
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
