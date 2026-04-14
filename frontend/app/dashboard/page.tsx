"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type Account, type AuditSummary, type AdPagePair } from "@/lib/api";
import { WastedSpendBanner } from "@/components/WastedSpendBanner";
import { AuditCard } from "@/components/AuditCard";
import { ConnectAccount } from "@/components/ConnectAccount";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const POLL_INTERVAL_MS = 5000;

export default function DashboardPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [audit, setAudit] = useState<AuditSummary | null>(null);
  const [pairs, setPairs] = useState<AdPagePair[]>([]);
  const [pairsTotal, setPairsTotal] = useState(0);
  const [pairsOffset, setPairsOffset] = useState(0);
  const [sort, setSort] = useState<"waste" | "score">("waste");
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);

  // Load user + accounts on mount
  useEffect(() => {
    Promise.all([api.getMe(), api.listAccounts()])
      .then(([me, accs]) => {
        setUser(me);
        setAccounts(accs);
        if (accs.length > 0) setSelectedAccount(accs[0]);
      })
      .catch(() => {
        // Not authenticated — redirect to home
        window.location.href = "/";
      })
      .finally(() => setLoading(false));
  }, []);

  // Load latest audit when account changes
  useEffect(() => {
    if (!selectedAccount) return;
    setAudit(null);
    setPairs([]);
    setPairsOffset(0);

    api.getLatestAudit(selectedAccount.id)
      .then(setAudit)
      .catch(() => setAudit(null)); // No audit yet — that's fine
  }, [selectedAccount]);

  // Poll while audit is running
  useEffect(() => {
    if (!audit || (audit.status !== "pending" && audit.status !== "running")) return;
    const id = setInterval(() => {
      api.getAudit(audit.id)
        .then(setAudit)
        .catch(console.error);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [audit?.id, audit?.status]);

  // Load pairs when audit completes
  useEffect(() => {
    if (audit?.status !== "completed") return;
    api.getAuditPairs(audit.id, sort, 0, 25)
      .then((data) => {
        setPairs(data.pairs);
        setPairsTotal(data.total);
        setPairsOffset(0);
      })
      .catch(console.error);
  }, [audit?.status, audit?.id, sort]);

  const triggerAudit = useCallback(async () => {
    if (!selectedAccount) return;
    setAuditLoading(true);
    setError(null);
    try {
      const res = await api.triggerAudit(selectedAccount.id);
      setAudit({ id: res.audit_id, status: "pending", total_ads: 0, avg_coherence_score: null, total_wasted_spend_monthly: null, ads_below_average_lp_experience: 0, error_message: null, created_at: new Date().toISOString(), completed_at: null });
      setPairs([]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAuditLoading(false);
    }
  }, [selectedAccount]);

  const loadMorePairs = async () => {
    if (!audit) return;
    const nextOffset = pairsOffset + 25;
    const data = await api.getAuditPairs(audit.id, sort, nextOffset, 25);
    setPairs((prev) => [...prev, ...data.pairs]);
    setPairsOffset(nextOffset);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <span className="font-bold text-gray-900">AdCoherence</span>
        <div className="flex items-center gap-4">
          {accounts.length > 1 && (
            <select
              value={selectedAccount?.id ?? ""}
              onChange={(e) => {
                const acc = accounts.find((a) => a.id === e.target.value);
                if (acc) setSelectedAccount(acc);
              }}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5"
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.account_name}</option>
              ))}
            </select>
          )}
          {selectedAccount && (
            <span className="text-sm text-gray-500">
              {selectedAccount.account_name}
            </span>
          )}
          <span className="text-sm text-gray-400">{user?.email}</span>
          <button
            onClick={() => api.logout().then(() => (window.location.href = "/"))}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* No account connected */}
        {accounts.length === 0 && (
          <ConnectAccount backendUrl={BACKEND_URL} />
        )}

        {/* Has account, no audit yet */}
        {accounts.length > 0 && !audit && (
          <div className="text-center mt-16">
            <h1 className="text-2xl font-bold text-gray-900 mb-3">Ready to audit your ads?</h1>
            <p className="text-gray-500 mb-8 max-w-md mx-auto">
              We'll pull every active ad from <strong>{selectedAccount?.account_name}</strong>,
              scrape each landing page, and score how well they match.
            </p>
            <button
              onClick={triggerAudit}
              disabled={auditLoading}
              className="bg-blue-600 text-white px-8 py-3 rounded-xl font-semibold text-sm hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {auditLoading ? "Starting audit…" : "Run Free Audit"}
            </button>
            {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
          </div>
        )}

        {/* Audit in progress */}
        {audit && (audit.status === "pending" || audit.status === "running") && (
          <div className="text-center mt-16">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Audit in progress…</h2>
            <p className="text-gray-500 text-sm max-w-sm mx-auto">
              Pulling your ads, scraping landing pages, and scoring with AI.
              This takes 1–3 minutes depending on account size.
            </p>
            <StatusSteps status={audit.status} />
          </div>
        )}

        {/* Audit failed */}
        {audit?.status === "failed" && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center mt-8">
            <div className="text-red-700 font-semibold mb-1">Audit failed</div>
            <p className="text-sm text-red-600">{audit.error_message || "Unknown error. Please try again."}</p>
            <button onClick={triggerAudit} className="mt-4 text-sm text-blue-600 hover:underline">
              Try again
            </button>
          </div>
        )}

        {/* Completed audit */}
        {audit?.status === "completed" && (
          <>
            {/* Summary banner */}
            <WastedSpendBanner audit={audit} />

            {/* Run new audit CTA */}
            <div className="flex items-center justify-between mt-6 mb-4">
              <div className="text-lg font-semibold text-gray-900">
                Ad-to-Page Pairs
                <span className="text-sm font-normal text-gray-400 ml-2">({pairsTotal} total)</span>
              </div>
              <div className="flex items-center gap-3">
                {/* Sort toggle */}
                <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
                  <button
                    onClick={() => setSort("waste")}
                    className={`px-3 py-1.5 ${sort === "waste" ? "bg-gray-900 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                  >
                    Worst waste first
                  </button>
                  <button
                    onClick={() => setSort("score")}
                    className={`px-3 py-1.5 ${sort === "score" ? "bg-gray-900 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                  >
                    Lowest score first
                  </button>
                </div>
                <button
                  onClick={triggerAudit}
                  disabled={auditLoading}
                  className="text-sm text-blue-600 border border-blue-200 px-3 py-1.5 rounded-lg hover:bg-blue-50 disabled:opacity-50"
                >
                  Re-run audit
                </button>
              </div>
            </div>

            {/* Ad-page pair cards */}
            <div className="space-y-4">
              {pairs.map((pair) => (
                <AuditCard key={pair.id} pair={pair} />
              ))}
            </div>

            {/* Load more */}
            {pairs.length < pairsTotal && (
              <div className="text-center mt-6">
                <button
                  onClick={loadMorePairs}
                  className="text-sm text-blue-600 border border-blue-200 px-6 py-2 rounded-lg hover:bg-blue-50"
                >
                  Load more ({pairsTotal - pairs.length} remaining)
                </button>
              </div>
            )}

            {/* Cooldown notice */}
            {error && (
              <p className="text-sm text-orange-600 mt-3 text-center">{error}</p>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function StatusSteps({ status }: { status: string }) {
  const steps = [
    { label: "Pulling ad data from Google Ads API", done: true },
    { label: "Scraping landing pages", done: status === "running" },
    { label: "Scoring with AI", done: false },
    { label: "Calculating wasted spend", done: false },
  ];

  return (
    <div className="mt-8 inline-block text-left space-y-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          {step.done ? (
            <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <div className="w-4 h-4 rounded-full border-2 border-gray-300" />
          )}
          <span className={step.done ? "text-gray-700" : "text-gray-400"}>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
