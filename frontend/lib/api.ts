const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
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

export interface ReportData {
  title: string;
  date: string;
  section1_summary: { text: string; points: string[] };
  section2_direction: { desired: string[]; quote: string };
  section3_concerns: {
    points: { title: string; sub: string }[];
    supplement: string;
  };
  section4_medical: {
    explanations: { label: string; icon: string; title: string }[];
  };
  section5_proposal: {
    steps: { step: string; title: string; desc: string }[];
  };
  section6_options: {
    recommended: { title: string; desc: string };
    optional: { title: string; desc: string };
    unnecessary: { title: string; desc: string };
    comment?: string;
  };
  section7_recovery: {
    info: { period: string; detail: string }[];
    closing: string;
  };
}

export interface DashboardStats {
  total_consultations: number;
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
};

// ============================================
// 리포트 API
// ============================================
export const reportAPI = {
  list: () => fetchAPI<{ data: Report[] }>("/reports"),
  get: (id: string) => fetchAPI<Report>(`/reports/${id}`),
  approve: (id: string) =>
    fetchAPI<{ id: string; status: string; email_sent_to: string; access_token: string }>(
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
