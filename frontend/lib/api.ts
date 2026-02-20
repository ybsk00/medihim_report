import { getToken, clearAuth } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearAuth();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new Error("인증이 만료되었습니다. 다시 로그인해주세요.");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `API Error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ============================================
// 타입 정의
// ============================================
export interface Consultation {
  id: string;
  customer_id: string | null;
  customer_name: string;
  customer_email: string;
  customer_line_id: string | null;
  original_text: string;
  translated_text: string | null;
  speaker_segments: { speaker: string; text: string }[] | null;
  customer_utterances: string | null;
  classification: "dermatology" | "plastic_surgery" | "unclassified" | null;
  classification_confidence: number | null;
  classification_reason: string | null;
  is_manually_classified: boolean;
  intent_extraction: {
    main_concerns?: string[];
    desired_direction?: string;
    unwanted?: string;
    mentioned_procedures?: string[];
    body_parts?: string[];
    keywords?: string[];
  } | null;
  cta_level: "hot" | "warm" | "cool" | null;
  cta_signals: string[] | null;
  input_language: "ja" | "ko" | null;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Report {
  id: string;
  consultation_id: string;
  report_data: ReportData;
  report_data_ko: ReportData | null;
  rag_context: unknown[] | null;
  review_count: number;
  review_passed: boolean;
  review_notes: string | null;
  access_token: string | null;
  access_expires_at: string | null;
  email_sent_at: string | null;
  email_opened_at: string | null;
  status: "draft" | "approved" | "rejected" | "sent";
  created_at: string;
  updated_at: string;
  consultations?: {
    customer_name: string;
    customer_email: string;
    customer_line_id?: string;
    classification?: string;
    cta_level?: string;
  };
}

// 리포트 데이터 (V3 9섹션 + V4 10섹션 호환)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface ReportData {
  title: string;
  date: string;
  section1_key_summary: { points: string[] };
  section2_cause_analysis: {
    intro: string;
    causes: string[];
    conclusion: string;
  };
  section3_recommendation: {
    primary: { label: string; items: string[] };
    secondary: { label: string; items: string[] };
    goal: string;
  };
  section4_recovery: {
    timeline: { period: string; detail: string }[];
    note?: string | null;
  };
  section5_scar_info: { points: string[] };
  section6_precautions: { points: string[] };
  section7_risks: { points: string[] };
  // V4 10섹션: 비용 + 내원일 + 이뻐 메시지
  section8_cost_estimate?: {
    items: string[];
    includes?: string | null;
    note?: string | null;
  };
  section9_visit_date?: { date: string | null; note?: string | null };
  section10_ippeo_message?: {
    paragraphs: string[];
    final_summary: string;
  };
  // V3 9섹션 하위 호환 (키 이름이 다름)
  section8_visit_date?: { date: string | null; note?: string | null };
  section9_ippeo_message?: {
    paragraphs: string[];
    final_summary: string;
  };
  // 추가 속성 허용
  [key: string]: unknown;
}

// V2 레거시 리포트 데이터 (기존 7섹션 구조 — 하위 호환용)
export interface ReportDataV2 {
  title: string;
  date: string;
  section1_summary: { text: string; points: string[] };
  section2_direction: {
    items: { text: string; detail?: string }[];
    conclusion: string;
    interpretation?: string;
    desired?: string[];
    quote?: string;
  };
  section3_concerns: {
    points: { title: string; description: string; sub?: string }[];
    interpretation: string;
    supplement?: string;
  };
  section4_medical: {
    explanations: {
      number: number;
      title: string;
      text: string;
      label?: string;
      icon?: string;
    }[];
    footnote?: string;
  };
  section5_proposal: {
    steps: { step: string; title: string; desc: string }[];
    context_note?: string;
  };
  section6_options: {
    recommended: { category_label?: string; items: string[]; title?: string; desc?: string };
    optional: { category_label?: string; items: string[]; title?: string; desc?: string };
    unnecessary: { category_label?: string; items: string[]; title?: string; desc?: string };
    comment?: string;
  };
  section7_recovery: {
    info: { period: string; detail: string }[];
    closing: string;
    gentle_note?: string;
  };
}

/** V3 리포트인지 판별 (section1_key_summary 존재 여부) */
export function isV3Report(data: ReportData | ReportDataV2): data is ReportData {
  return "section1_key_summary" in data;
}

export interface DashboardStats {
  total_consultations: number;
  registered_count: number;
  unclassified_count: number;
  report_pending_count: number;
  sent_count: number;
  view_rate: number;
  cta_hot: number;
  cta_warm: number;
  cta_cool: number;
  recent_consultations: {
    id: string;
    customer_name: string;
    classification: string | null;
    cta_level: string | null;
    status: string;
    created_at: string;
  }[];
}

export interface UnclassifiedItem {
  id: string;
  name: string;
  date: string;
  keywords: string[];
  preview: string;
  full_text: string;
}

export interface VectorItem {
  id: string;
  category: string;
  question: string;
  answer: string;
  procedure_name: string | null;
  youtube_video_id: string | null;
  youtube_title: string | null;
  youtube_url: string | null;
  created_at: string;
}

// ============================================
// 상담 API
// ============================================
export const consultationAPI = {
  list: (params?: Record<string, string>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchAPI<{ data: Consultation[]; total: number; page: number; page_size: number }>(
      `/consultations${query}`
    );
  },
  get: (id: string) => fetchAPI<Consultation>(`/consultations/${id}`),
  create: (data: {
    customer_id: string;
    customer_name: string;
    customer_email: string;
    customer_line_id: string;
    original_text: string;
  }) =>
    fetchAPI<{ id: string; status: string }>("/consultations", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  bulkCreate: (consultations: {
    customer_id: string;
    customer_name: string;
    customer_email: string;
    customer_line_id: string;
    original_text: string;
  }[]) =>
    fetchAPI<{ created: number; ids: string[] }>("/consultations/bulk", {
      method: "POST",
      body: JSON.stringify({ consultations }),
    }),
  classify: (id: string, classification: string) =>
    fetchAPI<{ id: string; status: string }>(`/consultations/${id}/classify`, {
      method: "PUT",
      body: JSON.stringify({ classification }),
    }),
  updateCTA: (id: string, ctaLevel: string) =>
    fetchAPI<{ id: string; cta_level: string }>(`/consultations/${id}/cta`, {
      method: "PUT",
      body: JSON.stringify({ cta_level: ctaLevel }),
    }),
  delete: (ids: string[]) =>
    fetchAPI<{ deleted: number; ids: string[] }>("/consultations/delete", {
      method: "POST",
      body: JSON.stringify({ consultation_ids: ids }),
    }),
  update: (id: string, data: { customer_name?: string; customer_email?: string; customer_line_id?: string; customer_id?: string }) =>
    fetchAPI<Consultation>(`/consultations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  generateReports: (ids: string[]) =>
    fetchAPI<{
      triggered: number;
      triggered_ids: string[];
      skipped: { id: string; status: string; reason: string }[];
    }>("/consultations/generate-reports", {
      method: "POST",
      body: JSON.stringify({ consultation_ids: ids }),
    }),
};

// ============================================
// 리포트 API
// ============================================
export const reportAPI = {
  list: () => fetchAPI<{ data: Report[] }>("/reports"),
  get: (id: string) => fetchAPI<Report>(`/reports/${id}`),
  approve: (id: string) =>
    fetchAPI<{ id: string; status: string; access_token: string }>(
      `/reports/${id}/approve`,
      { method: "PUT" }
    ),
  reject: (id: string) =>
    fetchAPI<{ id: string; status: string }>(`/reports/${id}/reject`, {
      method: "PUT",
    }),
  edit: (id: string, data: { report_data: ReportData }) =>
    fetchAPI<{ id: string; updated: boolean }>(`/reports/${id}/edit`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  translate: (id: string) =>
    fetchAPI<{ report_data_ko: ReportData; cached: boolean }>(
      `/reports/${id}/translate`
    ),
  sendEmail: (id: string) =>
    fetchAPI<{ id: string; status: string; email_sent_to: string; access_token: string }>(
      `/reports/${id}/send-email`,
      { method: "POST" }
    ),
  bulkApprove: (ids: string[]) =>
    fetchAPI<{ approved: number; approved_ids: string[]; skipped: { id: string; reason: string }[] }>(
      "/reports/bulk-approve",
      {
        method: "POST",
        body: JSON.stringify({ report_ids: ids }),
      }
    ),
  delete: (ids: string[]) =>
    fetchAPI<{ deleted: number; ids: string[] }>("/reports/delete", {
      method: "POST",
      body: JSON.stringify({ report_ids: ids }),
    }),
  regenerate: (id: string, direction: string) =>
    fetchAPI<{ id: string; status: string; message: string }>(
      `/reports/${id}/regenerate`,
      {
        method: "POST",
        body: JSON.stringify({ direction }),
      }
    ),
};

// ============================================
// 미분류 API
// ============================================
export const unclassifiedAPI = {
  list: () => fetchAPI<{ data: UnclassifiedItem[]; count: number }>("/unclassified"),
};

// ============================================
// 대시보드 API
// ============================================
export const dashboardAPI = {
  stats: () => fetchAPI<DashboardStats>("/dashboard/stats"),
};

// ============================================
// 관리자 API
// ============================================
export interface AdminUser {
  id: string;
  username: string;
  created_at: string;
}

export const adminAPI = {
  login: (username: string, password: string) =>
    fetchAPI<{ token: string; username: string }>("/admin/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  listUsers: () => fetchAPI<{ data: AdminUser[] }>("/admin/users"),
  createUser: (data: { username: string; password: string }) =>
    fetchAPI<AdminUser>("/admin/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteUser: (id: string) =>
    fetchAPI<{ deleted: boolean; id: string }>(`/admin/users/${id}`, {
      method: "DELETE",
    }),
};

// ============================================
// 벡터DB API
// ============================================
export const vectorAPI = {
  list: (params?: Record<string, string>) => {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchAPI<{ data: VectorItem[]; total: number; page: number; page_size: number }>(
      `/vectors${query}`
    );
  },
  delete: (id: string) =>
    fetchAPI<{ deleted: boolean; id: string }>(`/vectors/${id}`, {
      method: "DELETE",
    }),
  bulkDelete: (ids: string[]) =>
    fetchAPI<{ deleted: number; ids: string[] }>("/vectors/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
};

// ============================================
// 공개 리포트 API
// ============================================
export const publicReportAPI = {
  get: (token: string) =>
    fetchAPI<{ report_data: ReportData; customer_name: string }>(
      `/public/report/${token}`
    ),
  verify: (token: string, birthDate: string) =>
    fetchAPI<{ verified: boolean; report_id: string }>(
      `/public/report/${token}/verify`,
      {
        method: "POST",
        body: JSON.stringify({ birth_date: birthDate }),
      }
    ),
  opened: (token: string) =>
    fetchAPI<{ tracked: boolean }>(`/public/report/${token}/opened`, {
      method: "POST",
    }),
};
