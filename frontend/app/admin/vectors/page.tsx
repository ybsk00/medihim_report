"use client";

import { useState, useEffect, useCallback } from "react";
import { vectorAPI, type VectorItem } from "@/lib/api";

const CATEGORY_MAP: Record<string, string> = {
  dermatology: "피부과",
  plastic_surgery: "성형외과",
};

export default function VectorsPage() {
  const [vectors, setVectors] = useState<VectorItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const pageSize = 50;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(pageSize),
      };
      if (categoryFilter !== "all") params.category = categoryFilter;

      const result = await vectorAPI.list(params);
      setVectors(result.data);
      setTotal(result.total);
    } catch {
      setVectors([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, categoryFilter]);

  useEffect(() => {
    fetchData();
    setSelected(new Set());
  }, [fetchData]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === vectors.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(vectors.map((v) => v.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirm(`${selected.size}건의 벡터를 삭제하시겠습니까?`)) return;

    setDeleting(true);
    try {
      await vectorAPI.bulkDelete(Array.from(selected));
      setSelected(new Set());
      await fetchData();
    } catch (err) {
      alert(`삭제 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setDeleting(false);
    }
  };

  const getSourceLabel = (item: VectorItem) => {
    if (item.youtube_url?.includes("pubmed.ncbi.nlm.nih.gov")) return "PubMed";
    if (item.youtube_url?.includes("youtube.com") || item.youtube_video_id) return "YouTube";
    return "기타";
  };

  // 페이지 버튼 범위 계산
  const getPageRange = () => {
    const range: number[] = [];
    let start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + 4);
    start = Math.max(1, end - 4);
    for (let i = start; i <= end; i++) range.push(i);
    return range;
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold text-slate-800">벡터DB 관리</h2>
          <span className="text-sm text-slate-400 font-medium">
            총 {total.toLocaleString()}건
          </span>
        </div>
      </header>

      <div className="p-8 max-w-[1400px] mx-auto w-full space-y-6">
        {/* Filter + Actions */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(1);
              }}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">카테고리 전체</option>
              <option value="dermatology">피부과</option>
              <option value="plastic_surgery">성형외과</option>
            </select>
          </div>
          {selected.size > 0 && (
            <button
              onClick={handleBulkDelete}
              disabled={deleting}
              className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {deleting && (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              )}
              <span className="material-symbols-outlined text-lg">delete</span>
              {selected.size}건 삭제
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : vectors.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-2 block">
                database
              </span>
              <p className="text-lg font-medium">벡터 데이터가 없습니다</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3 border-b w-10">
                        <input
                          type="checkbox"
                          checked={selected.size === vectors.length && vectors.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-slate-300"
                        />
                      </th>
                      <th className="px-4 py-3 border-b">카테고리</th>
                      <th className="px-4 py-3 border-b">시술명</th>
                      <th className="px-4 py-3 border-b min-w-[200px]">질문</th>
                      <th className="px-4 py-3 border-b min-w-[250px]">답변</th>
                      <th className="px-4 py-3 border-b">출처</th>
                      <th className="px-4 py-3 border-b">등록일</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-sm">
                    {vectors.map((item) => (
                      <tr
                        key={item.id}
                        className={`hover:bg-slate-50 transition-colors ${
                          selected.has(item.id) ? "bg-primary/5" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selected.has(item.id)}
                            onChange={() => toggleSelect(item.id)}
                            className="rounded border-slate-300"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              item.category === "dermatology"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-purple-100 text-purple-800"
                            }`}
                          >
                            {CATEGORY_MAP[item.category] || item.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-600 text-xs">
                          {item.procedure_name || "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-800">
                          <p className="line-clamp-2 text-xs leading-relaxed">
                            {item.question}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          <p className="line-clamp-2 text-xs leading-relaxed">
                            {item.answer}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                              getSourceLabel(item) === "PubMed"
                                ? "bg-green-100 text-green-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {getSourceLabel(item)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                          {new Date(item.created_at).toLocaleDateString("ko-KR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  전체 {total.toLocaleString()}건 중{" "}
                  {((page - 1) * pageSize + 1).toLocaleString()}-
                  {Math.min(page * pageSize, total).toLocaleString()}건
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(1)}
                    disabled={page <= 1}
                    className="px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &laquo;
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &lt;
                  </button>
                  {getPageRange().map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-3 py-1 text-sm rounded ${
                        p === page
                          ? "bg-primary text-white"
                          : "text-slate-500 hover:bg-slate-100"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &gt;
                  </button>
                  <button
                    onClick={() => setPage(totalPages)}
                    disabled={page >= totalPages}
                    className="px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 rounded disabled:opacity-30"
                  >
                    &raquo;
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
