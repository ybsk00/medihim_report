"use client";

import { useState, useEffect } from "react";
import { unclassifiedAPI, consultationAPI, type UnclassifiedItem } from "@/lib/api";

export default function UnclassifiedPage() {
  const [items, setItems] = useState<UnclassifiedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalData, setModalData] = useState<UnclassifiedItem | null>(null);
  const [showFull, setShowFull] = useState(false);
  const [selected, setSelected] = useState<"dermatology" | "plastic_surgery" | null>(null);
  const [classifying, setClassifying] = useState(false);

  const fetchData = () => {
    setLoading(true);
    unclassifiedAPI
      .list()
      .then((res) => setItems(res.data))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleClassify = async () => {
    if (!selected || !modalData) return;
    setClassifying(true);
    try {
      await consultationAPI.classify(modalData.id, selected);
      setModalData(null);
      setSelected(null);
      setShowFull(false);
      fetchData();
    } catch (err) {
      alert(`분류 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setClassifying(false);
    }
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <h2 className="text-xl font-bold text-slate-800">미분류 처리</h2>
        <span className="ml-3 bg-red-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full">
          {items.length}건
        </span>
      </header>

      <div className="p-8 max-w-[1200px] mx-auto w-full space-y-6">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <span className="material-symbols-outlined text-amber-600">info</span>
          <p className="text-sm text-amber-800">
            AI가 자동 분류하지 못한 상담입니다. 수동으로 분류하면 AI 파이프라인이 자동으로 재개됩니다.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : items.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-2 block">check_circle</span>
              <p className="text-lg font-medium">미분류 건이 없습니다</p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 border-b">고객명</th>
                  <th className="px-6 py-3 border-b">등록일</th>
                  <th className="px-6 py-3 border-b">주요 키워드 (AI 추출)</th>
                  <th className="px-6 py-3 border-b text-right">액션</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900">{item.name}</td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(item.date).toLocaleDateString("ko-KR")}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1.5 flex-wrap">
                        {item.keywords.map((kw) => (
                          <span
                            key={kw}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => {
                          setModalData(item);
                          setSelected(null);
                          setShowFull(false);
                        }}
                        className="bg-primary text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                      >
                        분류하기
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal */}
      {modalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setModalData(null)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-800">수동 분류 — {modalData.name}</h3>
              <button onClick={() => setModalData(null)} className="text-slate-400 hover:text-slate-600">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Keywords */}
            <div>
              <p className="text-sm text-slate-500 mb-2">AI 추출 키워드:</p>
              <div className="flex gap-2 flex-wrap">
                {modalData.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>

            {/* Preview */}
            <div>
              <p className="text-sm text-slate-500 mb-2">상담 원문 미리보기:</p>
              <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-700 leading-relaxed">
                {showFull ? modalData.full_text : modalData.preview}
                {!showFull && modalData.full_text.length > modalData.preview.length && (
                  <button
                    onClick={() => setShowFull(true)}
                    className="ml-1 text-primary font-medium hover:underline"
                  >
                    전체 보기
                  </button>
                )}
              </div>
            </div>

            {/* Classification Buttons */}
            <div>
              <p className="text-sm text-slate-500 mb-3">분류 선택:</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setSelected("dermatology")}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    selected === "dermatology"
                      ? "border-primary bg-primary/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <span className="text-2xl">💊</span>
                  <p className="text-sm font-bold mt-1">피부과</p>
                </button>
                <button
                  onClick={() => setSelected("plastic_surgery")}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    selected === "plastic_surgery"
                      ? "border-primary bg-primary/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <span className="text-2xl">🏥</span>
                  <p className="text-sm font-bold mt-1">성형외과</p>
                </button>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleClassify}
                disabled={!selected || classifying}
                className={`px-6 py-2.5 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 ${
                  selected && !classifying
                    ? "bg-primary text-white hover:bg-primary/90"
                    : "bg-slate-100 text-slate-400 cursor-not-allowed"
                }`}
              >
                {classifying && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                )}
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
