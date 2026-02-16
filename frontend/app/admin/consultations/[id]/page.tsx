"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { use } from "react";
import { consultationAPI, type Consultation } from "@/lib/api";

const CLASSIFICATION_MAP: Record<string, string> = {
  plastic_surgery: "🏥 성형외과",
  dermatology: "💊 피부과",
  unclassified: "⚠️ 미분류",
};

const CTA_BADGE: Record<string, { emoji: string; color: string }> = {
  hot: { emoji: "🔴", color: "bg-red-100 text-red-800" },
  warm: { emoji: "🟡", color: "bg-amber-100 text-amber-800" },
  cool: { emoji: "🔵", color: "bg-slate-100 text-slate-800" },
};

export default function ConsultationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<Consultation | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<"ja" | "ko">("ja");
  const [ctaLevel, setCtaLevel] = useState("");
  const [ctaSaving, setCtaSaving] = useState(false);

  useEffect(() => {
    consultationAPI
      .get(id)
      .then((c) => {
        setData(c);
        setCtaLevel(c.cta_level || "cool");
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [id]);

  const handleCtaChange = async (newLevel: string) => {
    setCtaLevel(newLevel);
    setCtaSaving(true);
    try {
      await consultationAPI.updateCTA(id, newLevel);
    } catch {
      // revert on error
      if (data) setCtaLevel(data.cta_level || "cool");
    } finally {
      setCtaSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <div className="text-center">
          <span className="material-symbols-outlined text-5xl mb-2 block">error</span>
          <p>상담 데이터를 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  const segments =
    lang === "ja"
      ? data.speaker_segments || []
      : (data.speaker_segments || []).map((seg, i) => {
          // translated_segments가 없으면 원본 사용
          return seg;
        });

  const ctaBadge = data.cta_level ? CTA_BADGE[data.cta_level] : null;

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <Link
          href="/admin/consultations"
          className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mr-4"
        >
          <span className="material-symbols-outlined">arrow_back</span>
          <span className="text-sm">목록으로</span>
        </Link>
        <h2 className="text-xl font-bold text-slate-800">
          {data.customer_name} 상담 상세
        </h2>
      </header>

      <div className="p-8 max-w-[1200px] mx-auto w-full space-y-6">
        {/* Top 2 Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 고객 정보 */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">person</span>
              고객 정보
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">플랫폼 ID</span>
                <span className="text-sm font-medium text-slate-800">
                  {data.customer_id || "—"}
                </span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">이름</span>
                <span className="text-sm font-medium text-slate-800">{data.customer_name}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">이메일</span>
                <span className="text-sm font-medium text-slate-800">{data.customer_email}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">LINE ID</span>
                <span className="text-sm font-medium text-slate-800">
                  {data.customer_line_id || "—"}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-slate-500">등록일</span>
                <span className="text-sm font-medium text-slate-800">
                  {new Date(data.created_at).toLocaleDateString("ko-KR")}
                </span>
              </div>
            </div>
          </div>

          {/* AI 분석 결과 */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">psychology</span>
              AI 분석 결과
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-500">분류</span>
                <span className="text-sm font-bold">
                  {CLASSIFICATION_MAP[data.classification || ""] || "—"}
                </span>
              </div>
              {data.classification_reason && (
                <p className="text-xs text-slate-500 bg-slate-50 p-2 rounded">
                  {data.classification_reason}
                </p>
              )}
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-500">CTA</span>
                {ctaBadge ? (
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${ctaBadge.color}`}
                  >
                    {ctaBadge.emoji} {data.cta_level?.toUpperCase()}
                  </span>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </div>

              {data.cta_signals && data.cta_signals.length > 0 && (
                <div>
                  <p className="text-sm text-slate-500 mb-2">CTA 판단 근거 (고객 발화):</p>
                  <ul className="space-y-1.5">
                    {data.cta_signals.map((signal, i) => (
                      <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                        <span className="text-slate-400 mt-0.5">•</span>
                        <span className="italic">&ldquo;{signal}&rdquo;</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <span className="text-sm text-slate-500">CTA 수동 변경</span>
                <select
                  value={ctaLevel}
                  onChange={(e) => handleCtaChange(e.target.value)}
                  disabled={ctaSaving}
                  className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                >
                  <option value="hot">🔴 Hot</option>
                  <option value="warm">🟡 Warm</option>
                  <option value="cool">🔵 Cool</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* 상담 원문 */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">description</span>
                상담 원문
              </h3>
              <div className="flex bg-slate-100 rounded-lg p-0.5">
                <button
                  onClick={() => setLang("ja")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    lang === "ja"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  일본어 원문
                </button>
                <button
                  onClick={() => setLang("ko")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    lang === "ko"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  한국어 번역
                </button>
              </div>
            </div>
          </div>
          <div className="p-6 space-y-3 max-h-[500px] overflow-y-auto">
            {segments.length > 0 ? (
              segments.map((seg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 p-3 rounded-lg ${
                    seg.speaker === "counselor"
                      ? "bg-slate-50"
                      : "bg-white border border-slate-100"
                  }`}
                >
                  <span className="text-lg mt-0.5">
                    {seg.speaker === "counselor" ? "👤" : "👩"}
                  </span>
                  <div>
                    <span className="text-xs font-semibold text-slate-400 uppercase">
                      {seg.speaker === "counselor" ? "상담사" : "고객"}
                    </span>
                    <p className="text-sm text-slate-700 mt-0.5">{seg.text}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center">
                {lang === "ko" && data.translated_text ? (
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">{data.translated_text}</p>
                ) : (
                  <p className="text-sm text-slate-600 whitespace-pre-wrap">{data.original_text}</p>
                )}
              </div>
            )}
          </div>
          <div className="p-4 border-t border-slate-100 text-right">
            <Link
              href={`/admin/reports/${id}`}
              className="text-primary text-sm font-semibold hover:underline inline-flex items-center gap-1"
            >
              리포트 보기
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
