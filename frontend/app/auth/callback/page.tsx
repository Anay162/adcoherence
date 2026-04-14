"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

interface Account {
  customer_id: string;
  formatted_id: string;
  account_name: string;
}

export default function AuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selecting, setSelecting] = useState(false);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  useEffect(() => {
    if (!token) {
      setError("Missing auth token. Please try signing in again.");
      setLoading(false);
      return;
    }

    fetch(`${backendUrl}/auth/google/accounts?token=${encodeURIComponent(token)}`, {
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load accounts (${r.status})`);
        return r.json();
      })
      .then((data) => {
        setAccounts(data.accounts || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [token, backendUrl]);

  async function selectAccount(account: Account) {
    if (!token) return;
    setSelecting(true);
    try {
      const res = await fetch(`${backendUrl}/auth/google/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          selection_token: token,
          customer_id: account.customer_id,
          account_name: account.account_name,
        }),
      });
      if (!res.ok) throw new Error("Failed to connect account");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
      setSelecting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your Google Ads accounts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-xl p-8 shadow-sm border border-red-200 max-w-md text-center">
          <div className="text-red-600 font-semibold mb-2">Connection Error</div>
          <p className="text-gray-600 text-sm mb-4">{error}</p>
          <a href="/" className="text-blue-600 text-sm hover:underline">
            Try again
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-200 max-w-md w-full">
        <h1 className="text-xl font-bold text-gray-900 mb-2">Select your Google Ads account</h1>
        <p className="text-gray-500 text-sm mb-6">
          Choose which account you want to audit. You can connect more accounts later.
        </p>

        {accounts.length === 0 ? (
          <div className="text-gray-500 text-sm text-center py-8">
            No Google Ads accounts found. Make sure your Google account has access to at least one Ads account.
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => (
              <button
                key={account.customer_id}
                onClick={() => selectAccount(account)}
                disabled={selecting}
                className="w-full text-left border border-gray-200 rounded-lg p-4 hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50"
              >
                <div className="font-medium text-gray-900">{account.account_name}</div>
                <div className="text-sm text-gray-400">ID: {account.formatted_id}</div>
              </button>
            ))}
          </div>
        )}

        {selecting && (
          <div className="mt-4 text-center text-sm text-gray-500">
            Connecting account...
          </div>
        )}
      </div>
    </div>
  );
}
