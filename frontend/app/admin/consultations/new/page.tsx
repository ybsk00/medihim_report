"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { consultationAPI } from "@/lib/api";

interface CsvRow {
  customer_id: string;
  customer_name: string;
  customer_email: string;
  customer_line_id: string;
  original_text: string;
}

interface CsvError {
  row: number;
  message: string;
}

function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        fields.push(current.trim());
        current = "";
      } else {
        current += ch;
      }
    }
  }
  fields.push(current.trim());
  return fields;
}

const REQUIRED_COLUMNS = ["customer_id", "customer_name", "customer_email", "customer_line_id", "original_text"];

export default function NewConsultationPage() {
  const router = useRouter();
  const [inputMode, setInputMode] = useState<"stt" | "csv">("stt");
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fileName, setFileName] = useState("");
  const [formData, setFormData] = useState({
    customerId: "",
    customerName: "",
    customerEmail: "",
    lineId: "",
    sttText: "",
  });

  // CSV 관련 상태
  const [csvRows, setCsvRows] = useState<CsvRow[]>([]);
  const [csvErrors, setCsvErrors] = useState<CsvError[]>([]);
  const [csvFileName, setCsvFileName] = useState("");
  const csvInputRef = useRef<HTMLInputElement>(null);

  const handleSttFileChange = (file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setFormData((prev) => ({ ...prev, sttText: text }));
    };
    reader.readAsText(file);
  };

  const handleCsvParse = (text: string, name: string) => {
    setCsvFileName(name);
    const lines = text.split(/\r?\n/).filter((l) => l.trim());
    if (lines.length < 2) {
      setCsvErrors([{ row: 0, message: "CSV 파일에 헤더와 데이터가 필요합니다" }]);
      setCsvRows([]);
      return;
    }

    const headers = parseCsvLine(lines[0]).map((h) => h.toLowerCase().replace(/\ufeff/, ""));
    const missingCols = REQUIRED_COLUMNS.filter((c) => !headers.includes(c));
    if (missingCols.length > 0) {
      setCsvErrors([{ row: 0, message: `필수 컬럼 누락: ${missingCols.join(", ")}` }]);
      setCsvRows([]);
      return;
    }

    const colIndices = Object.fromEntries(REQUIRED_COLUMNS.map((c) => [c, headers.indexOf(c)]));
    const rows: CsvRow[] = [];
    const errors: CsvError[] = [];

    for (let i = 1; i < lines.length; i++) {
      const fields = parseCsvLine(lines[i]);
      const row: CsvRow = {
        customer_id: fields[colIndices.customer_id] || "",
        customer_name: fields[colIndices.customer_name] || "",
        customer_email: fields[colIndices.customer_email] || "",
        customer_line_id: fields[colIndices.customer_line_id] || "",
        original_text: fields[colIndices.original_text] || "",
      };

      const missing: string[] = [];
      if (!row.customer_id) missing.push("customer_id");
      if (!row.customer_name) missing.push("customer_name");
      if (!row.customer_email) missing.push("customer_email");
      if (!row.customer_line_id) missing.push("customer_line_id");
      if (!row.original_text) missing.push("original_text");

      if (missing.length > 0) {
        errors.push({ row: i + 1, message: `빈 필드: ${missing.join(", ")}` });
      } else {
        rows.push(row);
      }
    }

    setCsvRows(rows);
    setCsvErrors(errors);
  };

  const handleCsvFileChange = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      handleCsvParse(text, file.name);
    };
    reader.readAsText(file, "UTF-8");
  };

  // STT 모드 제출
  const handleSttSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.customerId || !formData.customerName || !formData.customerEmail || !formData.lineId || !formData.sttText) {
      alert("필수 항목을 모두 입력해주세요.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await consultationAPI.create({
        customer_id: formData.customerId,
        customer_name: formData.customerName,
        customer_email: formData.customerEmail,
        customer_line_id: formData.lineId,
        original_text: formData.sttText,
      });
      alert(`상담이 등록되었습니다. AI 파이프라인이 시작됩니다.\nID: ${result.id}`);
      router.push("/admin/consultations");
    } catch (err) {
      alert(`등록 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setSubmitting(false);
    }
  };

  // CSV 모드 제출
  const handleCsvSubmit = async () => {
    if (csvRows.length === 0) {
      alert("등록할 데이터가 없습니다.");
      return;
    }
    if (csvRows.length > 100) {
      alert("최대 100건까지 일괄 등록 가능합니다.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await consultationAPI.bulkCreate(csvRows);
      alert(`${result.created}건의 상담이 등록되었습니다. AI 파이프라인이 시작됩니다.`);
      router.push("/admin/consultations");
    } catch (err) {
      alert(`등록 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <Link
          href="/admin/consultations"
          className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mr-4"
        >
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <h2 className="text-xl font-bold text-slate-800">새 상담 등록</h2>
      </header>

      <div className="p-8 max-w-3xl mx-auto w-full">
        {/* 입력 방식 선택 탭 */}
        <div className="flex gap-2 mb-6">
          <button
            type="button"
            onClick={() => setInputMode("stt")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              inputMode === "stt"
                ? "bg-primary text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            STT 파일 업로드
          </button>
          <button
            type="button"
            onClick={() => setInputMode("csv")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              inputMode === "csv"
                ? "bg-primary text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            CSV 대량 업로드
          </button>
        </div>

        {/* ======================== STT 모드 ======================== */}
        {inputMode === "stt" && (
          <form
            onSubmit={handleSttSubmit}
            className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-6"
          >
            {/* 고객 정보 4개 필드 */}
            <div className="grid grid-cols-2 gap-4">
              {/* 플랫폼 ID */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  플랫폼 ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.customerId}
                  onChange={(e) => setFormData({ ...formData, customerId: e.target.value })}
                  placeholder="메디힘 플랫폼 ID"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>

              {/* 고객명 */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  고객명 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.customerName}
                  onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
                  placeholder="예: 田中花子"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>

              {/* 이메일 */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  이메일 <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={formData.customerEmail}
                  onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
                  placeholder="예: tanaka@email.jp"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>

              {/* LINE ID */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  LINE ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.lineId}
                  onChange={(e) => setFormData({ ...formData, lineId: e.target.value })}
                  placeholder="예: tanaka_123"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
            </div>

            {/* STT 파일 업로드 */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-3">
                STT 파일 <span className="text-red-500">*</span>
              </label>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive
                    ? "border-primary bg-primary/5"
                    : "border-slate-200 hover:border-slate-300"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                  const file = e.dataTransfer.files[0];
                  if (file) handleSttFileChange(file);
                }}
              >
                {fileName ? (
                  <div>
                    <span className="material-symbols-outlined text-4xl text-emerald-500 mb-2">
                      check_circle
                    </span>
                    <p className="text-sm text-slate-600 font-medium">{fileName}</p>
                    <p className="text-xs text-slate-400 mt-1">파일이 로드되었습니다</p>
                  </div>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-4xl text-slate-300 mb-3">
                      cloud_upload
                    </span>
                    <p className="text-sm text-slate-600 mb-1">파일을 드래그하거나 클릭하여 업로드</p>
                    <p className="text-xs text-slate-400">TXT, JSON, SRT 파일 지원</p>
                  </>
                )}
                <input
                  type="file"
                  accept=".txt,.json,.srt"
                  className="hidden"
                  id="stt-upload"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleSttFileChange(file);
                  }}
                />
                <label
                  htmlFor="stt-upload"
                  className="mt-3 inline-block bg-slate-100 text-slate-600 px-4 py-2 rounded-lg text-sm cursor-pointer hover:bg-slate-200 transition-colors"
                >
                  파일 선택
                </label>
              </div>
            </div>

            {/* 버튼 */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Link
                href="/admin/consultations"
                className="px-6 py-2.5 bg-slate-100 text-slate-600 rounded-lg text-sm font-medium hover:bg-slate-200 transition-colors"
              >
                취소
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2.5 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {submitting && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                )}
                등록하기
              </button>
            </div>
          </form>
        )}

        {/* ======================== CSV 대량 업로드 모드 ======================== */}
        {inputMode === "csv" && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-6">
            {/* CSV 포맷 안내 */}
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
              <p className="text-sm font-semibold text-blue-800 mb-2">CSV 파일 형식</p>
              <p className="text-xs text-blue-700 mb-2">
                필수 컬럼: <code className="bg-blue-100 px-1 rounded">customer_id</code>,{" "}
                <code className="bg-blue-100 px-1 rounded">customer_name</code>,{" "}
                <code className="bg-blue-100 px-1 rounded">customer_email</code>,{" "}
                <code className="bg-blue-100 px-1 rounded">customer_line_id</code>,{" "}
                <code className="bg-blue-100 px-1 rounded">original_text</code>
              </p>
              <p className="text-xs text-blue-600">
                UTF-8 인코딩, 쉼표 구분. 일본어 텍스트는 쌍따옴표로 감싸주세요. 최대 100건.
              </p>
            </div>

            {/* CSV 파일 드래그앤드롭 */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-slate-200 hover:border-slate-300"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                const file = e.dataTransfer.files[0];
                if (file && file.name.endsWith(".csv")) {
                  handleCsvFileChange(file);
                } else {
                  alert("CSV 파일만 업로드 가능합니다.");
                }
              }}
            >
              {csvFileName ? (
                <div>
                  <span className="material-symbols-outlined text-4xl text-emerald-500 mb-2">
                    check_circle
                  </span>
                  <p className="text-sm text-slate-600 font-medium">{csvFileName}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {csvRows.length}건 파싱 완료
                    {csvErrors.length > 0 && `, ${csvErrors.length}건 오류`}
                  </p>
                </div>
              ) : (
                <>
                  <span className="material-symbols-outlined text-4xl text-slate-300 mb-3">
                    upload_file
                  </span>
                  <p className="text-sm text-slate-600 mb-1">CSV 파일을 드래그하거나 클릭하여 업로드</p>
                  <p className="text-xs text-slate-400">.csv 파일만 지원</p>
                </>
              )}
              <input
                type="file"
                accept=".csv"
                className="hidden"
                ref={csvInputRef}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleCsvFileChange(file);
                }}
              />
              <label
                onClick={() => csvInputRef.current?.click()}
                className="mt-3 inline-block bg-slate-100 text-slate-600 px-4 py-2 rounded-lg text-sm cursor-pointer hover:bg-slate-200 transition-colors"
              >
                파일 선택
              </label>
            </div>

            {/* CSV 오류 표시 */}
            {csvErrors.length > 0 && (
              <div className="bg-red-50 border border-red-100 rounded-lg p-4">
                <p className="text-sm font-semibold text-red-800 mb-2">
                  오류 ({csvErrors.length}건)
                </p>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {csvErrors.map((err, i) => (
                    <p key={i} className="text-xs text-red-700">
                      행 {err.row}: {err.message}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* CSV 미리보기 테이블 */}
            {csvRows.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-slate-700 mb-3">
                  미리보기 ({csvRows.length}건)
                </p>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className="overflow-x-auto max-h-80 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">#</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">플랫폼ID</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">고객명</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">이메일</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">LINE ID</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">원문</th>
                        </tr>
                      </thead>
                      <tbody>
                        {csvRows.slice(0, 20).map((row, i) => (
                          <tr key={i} className="border-t border-slate-100">
                            <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                            <td className="px-3 py-2 text-slate-700">{row.customer_id}</td>
                            <td className="px-3 py-2 text-slate-700">{row.customer_name}</td>
                            <td className="px-3 py-2 text-slate-700">{row.customer_email}</td>
                            <td className="px-3 py-2 text-slate-700">{row.customer_line_id}</td>
                            <td className="px-3 py-2 text-slate-700 max-w-xs truncate">
                              {row.original_text.length > 50
                                ? row.original_text.slice(0, 50) + "..."
                                : row.original_text}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {csvRows.length > 20 && (
                    <p className="text-xs text-slate-400 text-center py-2 bg-slate-50 border-t border-slate-100">
                      ... 외 {csvRows.length - 20}건 더
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* 버튼 */}
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Link
                href="/admin/consultations"
                className="px-6 py-2.5 bg-slate-100 text-slate-600 rounded-lg text-sm font-medium hover:bg-slate-200 transition-colors"
              >
                취소
              </Link>
              <button
                type="button"
                onClick={handleCsvSubmit}
                disabled={submitting || csvRows.length === 0}
                className="px-6 py-2.5 bg-primary text-white rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {submitting && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                )}
                {csvRows.length}건 일괄 등록
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
