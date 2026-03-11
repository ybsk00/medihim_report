"use client";

import { useState, useRef } from "react";

// NEXT_PUBLIC_API_URL에 /api가 포함되어 있으므로 제거
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "https://ippo-backend-3h7djqxgyq-du.a.run.app/api").replace(/\/api$/, "");
const API_KEY = "***REMOVED***";
const WEBHOOK_SECRET = "***REMOVED***";

// HMAC-SHA256 서명 생성 (Web Crypto API)
async function createSignature(body: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const hex = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `sha256=${hex}`;
}

type LogEntry = { time: string; type: "info" | "success" | "error" | "poll"; message: string };

export default function WebhookTestPage() {
  const [customerName, setCustomerName] = useState("テスト花子");
  const [sttText, setSttText] = useState(
    "相談者: こんにちは。今日は鼻の再手術について相談したいです。\n" +
    "前回の手術から1年経ちましたが、鼻先が少し曲がっているように感じます。\n" +
    "もう少し自然な感じにしたいです。鼻先を少し下げて、全体的に柔らかいラインにしたいです。\n" +
    "費用はどのくらいかかりますか？7月に手術を受けたいのですが可能ですか？\n" +
    "スタッフ: はい、鼻先の修正ですね。耳の軟骨を使って自然に整える方法があります。\n" +
    "費用は大体200万ウォンから300万ウォン程度です。7月でしたら予約可能です。"
  );
  const [consultationRound, setConsultationRound] = useState(1);
  const [hospitalName, setHospitalName] = useState("テスト病院");

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [consultationId, setConsultationId] = useState("");
  const [embedUrls, setEmbedUrls] = useState<{ patientJa?: string; patientKo?: string; doctorKo?: string }>({});
  const [sending, setSending] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLog = (type: LogEntry["type"], message: string) => {
    const time = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setLogs((prev) => [...prev, { time, type, message }]);
  };

  const handleSend = async () => {
    setSending(true);
    setLogs([]);
    setConsultationId("");
    setEmbedUrls({});

    const payload = {
      customer_name: customerName,
      stt_text: sttText,
      consultation_round: consultationRound,
      hospital_name: hospitalName,
      concern_area: "鼻の再手術",
    };

    const body = JSON.stringify(payload);
    addLog("info", "① STT 데이터 전송 중...");

    try {
      const signature = await createSignature(body);
      addLog("info", `서명 생성: ${signature.substring(0, 30)}...`);

      const res = await fetch(`${API_BASE}/api/webhook/consultation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
          "X-Signature": signature,
        },
        body,
      });

      const data = await res.json();

      if (!res.ok) {
        addLog("error", `전송 실패 (${res.status}): ${JSON.stringify(data)}`);
        setSending(false);
        return;
      }

      addLog("success", `전송 성공: ${JSON.stringify(data)}`);

      // consultation_id 추출
      const cid = data.consultation_id;
      if (cid) {
        setConsultationId(cid);
        addLog("info", `consultation_id: ${cid}`);
        addLog("info", "② 상태 폴링 시작 (30초 간격)...");
        startPolling(cid);
      } else {
        addLog("error", "응답에 consultation_id가 없습니다. 수동으로 상태 확인이 필요합니다.");
      }
    } catch (err) {
      addLog("error", `네트워크 오류: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    } finally {
      setSending(false);
    }
  };

  const startPolling = (cid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPolling(true);
    let count = 0;

    const poll = async () => {
      count++;
      try {
        const res = await fetch(`${API_BASE}/api/webhook/status/${cid}`, {
          headers: { "X-API-Key": API_KEY },
        });
        const data = await res.json();
        const status = data.status || "unknown";

        if (status === "report_ready" || status === "report_approved" || status === "report_sent") {
          addLog("success", `③ 리포트 완료! (폴링 ${count}회, status: ${status})`);

          const urls: typeof embedUrls = {};
          if (data.patient_report?.embed_url) {
            urls.patientJa = data.patient_report.embed_url.ja;
            urls.patientKo = data.patient_report.embed_url.ko;
          }
          if (data.doctor_report?.embed_url) {
            urls.doctorKo = data.doctor_report.embed_url.ko;
          }
          setEmbedUrls(urls);
          addLog("success", `embed URLs: ${JSON.stringify(urls, null, 2)}`);

          if (pollRef.current) clearInterval(pollRef.current);
          setPolling(false);
        } else if (status === "report_failed") {
          addLog("error", `리포트 생성 실패: ${data.error_message || "알 수 없음"}`);
          if (pollRef.current) clearInterval(pollRef.current);
          setPolling(false);
        } else {
          addLog("poll", `폴링 ${count}회: status=${status}`);
        }
      } catch (err) {
        addLog("error", `폴링 오류: ${err instanceof Error ? err.message : "알 수 없음"}`);
      }
    };

    poll(); // 즉시 1회
    pollRef.current = setInterval(poll, 30000); // 30초 간격
  };

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPolling(false);
    addLog("info", "폴링 중지");
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-8 sticky top-0 z-10">
        <h2 className="text-xl font-bold text-slate-800">Webhook 연동 테스트</h2>
        <span className="ml-3 text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full font-medium">테스트 전용</span>
      </header>

      <div className="p-8 max-w-[1400px] mx-auto w-full grid grid-cols-2 gap-6">
        {/* 좌측: 입력 */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-700">STT 데이터 입력</h3>

            <div>
              <label className="block text-xs text-slate-500 mb-1">고객명</label>
              <input
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">병원명</label>
                <input
                  value={hospitalName}
                  onChange={(e) => setHospitalName(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">상담 회차</label>
                <select
                  value={consultationRound}
                  onChange={(e) => setConsultationRound(Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value={1}>1차</option>
                  <option value={2}>2차</option>
                  <option value={3}>3차</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 mb-1">STT 텍스트</label>
              <textarea
                value={sttText}
                onChange={(e) => setSttText(e.target.value)}
                rows={8}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <button
              onClick={handleSend}
              disabled={sending || !customerName || !sttText}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {sending ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <span className="material-symbols-outlined text-lg">send</span>
              )}
              STT 전송 + 리포트 생성 시작
            </button>

            {polling && (
              <button
                onClick={stopPolling}
                className="w-full bg-slate-200 text-slate-700 py-2 rounded-lg text-sm font-medium hover:bg-slate-300 transition-colors"
              >
                폴링 중지
              </button>
            )}
          </div>

          {/* 로그 */}
          <div className="bg-slate-900 rounded-xl border border-slate-700 shadow-sm p-4 max-h-[400px] overflow-y-auto">
            <h3 className="text-xs font-bold text-slate-400 mb-3">실행 로그</h3>
            {logs.length === 0 ? (
              <p className="text-xs text-slate-500">STT를 전송하면 로그가 표시됩니다.</p>
            ) : (
              <div className="space-y-1 font-mono text-xs">
                {logs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-slate-500 shrink-0">{log.time}</span>
                    <span
                      className={
                        log.type === "success" ? "text-emerald-400" :
                        log.type === "error" ? "text-red-400" :
                        log.type === "poll" ? "text-yellow-400" :
                        "text-slate-300"
                      }
                    >
                      {log.message}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 우측: iframe 미리보기 */}
        <div className="space-y-4">
          {embedUrls.patientJa && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <h3 className="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-coral rounded-full"></span>
                환자용 리포트 (일본어)
              </h3>
              <p className="text-xs text-slate-400 mb-3 break-all">{embedUrls.patientJa}</p>
              <div className="border border-slate-200 rounded-lg overflow-hidden" style={{ height: "600px" }}>
                <iframe
                  src={embedUrls.patientJa}
                  style={{ width: "100%", height: "100%", border: "none" }}
                />
              </div>
            </div>
          )}

          {embedUrls.doctorKo && (
            <div className="bg-white rounded-xl border border-purple-200 shadow-sm p-4">
              <h3 className="text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                의사용 리포트 (한국어)
              </h3>
              <p className="text-xs text-slate-400 mb-3 break-all">{embedUrls.doctorKo}</p>
              <div className="border border-purple-200 rounded-lg overflow-hidden" style={{ height: "600px" }}>
                <iframe
                  src={embedUrls.doctorKo}
                  style={{ width: "100%", height: "100%", border: "none" }}
                />
              </div>
            </div>
          )}

          {!embedUrls.patientJa && !embedUrls.doctorKo && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-16 text-center">
              <span className="material-symbols-outlined text-5xl text-slate-300 mb-2 block">preview</span>
              <p className="text-slate-400 text-sm">STT를 전송하면 생성된 리포트가 여기에 표시됩니다.</p>
              <p className="text-slate-300 text-xs mt-1">약 3~5분 소요</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
