"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { use } from "react";
import { consultationAPI, type Consultation } from "@/lib/api";

const CLASSIFICATION_MAP: Record<string, string> = {
  plastic_surgery: "🏥 성형외과",
  dermatology: "💊 피부과",
  dentistry: "🦷 치과",
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
  const [ctaLang, setCtaLang] = useState<"ja" | "ko">("ja");
  const [ctaLevel, setCtaLevel] = useState("");
  const [ctaSaving, setCtaSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editForm, setEditForm] = useState({
    customer_name: "",
    customer_email: "",
    customer_line_id: "",
    customer_id: "",
  });
  // [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
  // const [reports, setReports] = useState<Report[]>([]);

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

  const startEditing = () => {
    if (!data) return;
    setEditForm({
      customer_name: data.customer_name || "",
      customer_email: data.customer_email || "",
      customer_line_id: data.customer_line_id || "",
      customer_id: data.customer_id || "",
    });
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
  };

  const saveEditing = async () => {
    if (!data) return;
    setSaving(true);
    try {
      const updated = await consultationAPI.update(id, editForm);
      setData({ ...data, ...updated });
      setEditing(false);
    } catch (err) {
      alert(`저장 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setSaving(false);
    }
  };

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

  const ctaBadge = data.cta_level ? CTA_BADGE[data.cta_level] : null;
  const isKoreanInput = data.input_language === "ko";

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
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">person</span>
                고객 정보
              </h3>
              {!editing ? (
                <button
                  onClick={startEditing}
                  className="text-sm text-primary hover:text-primary/80 font-medium flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-base">edit</span>
                  수정
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={cancelEditing}
                    disabled={saving}
                    className="text-sm text-slate-500 hover:text-slate-700 font-medium px-3 py-1 rounded-lg border border-slate-200"
                  >
                    취소
                  </button>
                  <button
                    onClick={saveEditing}
                    disabled={saving}
                    className="text-sm text-white bg-primary hover:bg-primary/90 font-medium px-3 py-1 rounded-lg flex items-center gap-1 disabled:opacity-50"
                  >
                    {saving && <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                    저장
                  </button>
                </div>
              )}
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">플랫폼 ID</span>
                {editing ? (
                  <input
                    type="text"
                    value={editForm.customer_id}
                    onChange={(e) => setEditForm({ ...editForm, customer_id: e.target.value })}
                    className="text-sm font-medium text-slate-800 border border-slate-200 rounded px-2 py-1 w-48 text-right focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                ) : (
                  <span className="text-sm font-medium text-slate-800">{data.customer_id || "—"}</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">이름</span>
                {editing ? (
                  <input
                    type="text"
                    value={editForm.customer_name}
                    onChange={(e) => setEditForm({ ...editForm, customer_name: e.target.value })}
                    className="text-sm font-medium text-slate-800 border border-slate-200 rounded px-2 py-1 w-48 text-right focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                ) : (
                  <span className="text-sm font-medium text-slate-800">{data.customer_name}</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">이메일</span>
                {editing ? (
                  <input
                    type="email"
                    value={editForm.customer_email}
                    onChange={(e) => setEditForm({ ...editForm, customer_email: e.target.value })}
                    className="text-sm font-medium text-slate-800 border border-slate-200 rounded px-2 py-1 w-48 text-right focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                ) : (
                  <span className="text-sm font-medium text-slate-800">{data.customer_email}</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-50">
                <span className="text-sm text-slate-500">LINE ID</span>
                {editing ? (
                  <input
                    type="text"
                    value={editForm.customer_line_id}
                    onChange={(e) => setEditForm({ ...editForm, customer_line_id: e.target.value })}
                    className="text-sm font-medium text-slate-800 border border-slate-200 rounded px-2 py-1 w-48 text-right focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                ) : (
                  <span className="text-sm font-medium text-slate-800">{data.customer_line_id || "—"}</span>
                )}
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
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-slate-500">CTA 판단 근거 (고객 발화):</p>
                    {!isKoreanInput && (
                      <div className="flex bg-slate-100 rounded-md p-0.5">
                        <button
                          onClick={() => setCtaLang("ja")}
                          className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            ctaLang === "ja"
                              ? "bg-white text-slate-800 shadow-sm"
                              : "text-slate-500 hover:text-slate-700"
                          }`}
                        >
                          일본어
                        </button>
                        <button
                          onClick={() => setCtaLang("ko")}
                          className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            ctaLang === "ko"
                              ? "bg-white text-slate-800 shadow-sm"
                              : "text-slate-500 hover:text-slate-700"
                          }`}
                        >
                          한국어
                        </button>
                      </div>
                    )}
                  </div>
                  {isKoreanInput ? (
                    <ul className="space-y-1.5">
                      {data.cta_signals.map((signal, i) => (
                        <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                          <span className="text-slate-400 mt-0.5">•</span>
                          <span className="italic">&ldquo;{signal}&rdquo;</span>
                        </li>
                      ))}
                    </ul>
                  ) : ctaLang === "ja" ? (
                    <ul className="space-y-1.5">
                      {data.cta_signals.map((signal, i) => (
                        <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                          <span className="text-slate-400 mt-0.5">•</span>
                          <span className="italic">&ldquo;{signal}&rdquo;</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                      {data.customer_utterances || "한국어 번역 데이터가 없습니다."}
                    </p>
                  )}
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
              {isKoreanInput ? (
                <span className="text-xs text-slate-400 font-medium px-3 py-1.5 bg-slate-50 rounded-lg">한국어 원문</span>
              ) : (
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
              )}
            </div>
          </div>
          <div className="p-6 space-y-3 max-h-[500px] overflow-y-auto">
            {isKoreanInput ? (
              /* 한국어 입력: 화자 분리 있으면 화자 분리 표시, 없으면 원문 표시 */
              (data.speaker_segments || []).length > 0 ? (
                (data.speaker_segments || []).map((seg, i) => (
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
                <div className="py-4">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                    {data.original_text}
                  </p>
                </div>
              )
            ) : (
              /* 일본어 입력: 기존 로직 (일본어/한국어 탭 전환) */
              lang === "ja" && (data.speaker_segments || []).length > 0 ? (
                (data.speaker_segments || []).map((seg, i) => (
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
                <div className="py-4">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                    {lang === "ko"
                      ? (data.translated_text || data.original_text)
                      : data.original_text}
                  </p>
                </div>
              )
            )}
          </div>
          <div className="p-4 border-t border-slate-100">
            {/* [R1-R3 비활성화] 리포트 현황 그리드 숨김, 기존 단일 링크 복원 */}
            <div className="text-right">
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
      </div>
    </>
  );
}
