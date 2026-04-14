const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export interface Account {
  id: string;
  google_ads_customer_id: string;
  account_name: string;
  last_used_at: string | null;
}

export interface AuditSummary {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  total_ads: number;
  avg_coherence_score: number | null;
  total_wasted_spend_monthly: number | null;
  ads_below_average_lp_experience: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Dimension {
  score: number;
  diagnosis: string;
}

export interface AdPagePair {
  id: string;
  campaign_name: string;
  ad_group_name: string;
  ad_headlines: string[];
  ad_descriptions: string[];
  final_url: string;
  keywords: Keyword[];
  page_title: string;
  page_h1: string;
  page_h2s: string[];
  cta_texts: string[];
  offer_mentions: string[];
  mobile_friendly: boolean;
  page_load_time_ms: number;
  screenshot_path: string | null;
  scrape_error: string | null;
  overall_score: number;
  headline_match: Dimension;
  offer_consistency: Dimension;
  cta_alignment: Dimension;
  keyword_relevance: Dimension;
  tone_continuity: Dimension;
  top_recommendations: string[];
  estimated_monthly_waste: number | null;
  waste_type: "cpc_savings" | "conversion_lift" | "none" | null;
  additional_conversions_monthly: number | null;
}

export interface Keyword {
  keyword_text: string;
  match_type: string;
  quality_score: number | null;
  landing_page_experience: string;
  expected_ctr: string;
  ad_relevance: string;
  avg_cpc_micros: number;
  clicks_30d: number;
  cost_micros_30d: number;
  conversions_30d: number;
}

export const api = {
  getMe: () => apiFetch<{ id: string; email: string; name: string }>("/auth/me"),

  listAccounts: () => apiFetch<Account[]>("/accounts"),

  triggerAudit: (accountId: string) =>
    apiFetch<{ audit_id: string; status: string }>("/audits", {
      method: "POST",
      body: JSON.stringify({ account_id: accountId }),
    }),

  getAudit: (auditId: string) => apiFetch<AuditSummary>(`/audits/${auditId}`),

  getLatestAudit: (accountId: string) =>
    apiFetch<AuditSummary>(`/audits/latest?account_id=${accountId}`),

  getAuditPairs: (auditId: string, sort: "waste" | "score" = "waste", offset = 0, limit = 25) =>
    apiFetch<{ total: number; offset: number; limit: number; pairs: AdPagePair[] }>(
      `/audits/${auditId}/pairs?sort=${sort}&offset=${offset}&limit=${limit}`
    ),

  logout: () =>
    apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" }),
};
