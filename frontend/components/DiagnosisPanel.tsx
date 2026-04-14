"use client";

import { useState } from "react";
import { clsx } from "clsx";
import type { AdPagePair } from "@/lib/api";
import { ScoreBar } from "./CoherenceScore";

interface DiagnosisPanelProps {
  pair: AdPagePair;
}

export function DiagnosisPanel({ pair }: DiagnosisPanelProps) {
  const [open, setOpen] = useState(false);

  const dimensions = [
    { key: "headline_match", label: "Headline Match", weight: "30%", data: pair.headline_match },
    { key: "offer_consistency", label: "Offer Consistency", weight: "25%", data: pair.offer_consistency },
    { key: "cta_alignment", label: "CTA Alignment", weight: "20%", data: pair.cta_alignment },
    { key: "keyword_relevance", label: "Keyword Relevance", weight: "15%", data: pair.keyword_relevance },
    { key: "tone_continuity", label: "Tone Continuity", weight: "10%", data: pair.tone_continuity },
  ];

  return (
    <div className="border-t border-gray-100 mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 py-3 font-medium"
      >
        <span>{open ? "Hide" : "Show"} detailed diagnosis</span>
        <svg
          className={clsx("w-4 h-4 transition-transform", open && "rotate-180")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="pb-4 space-y-5">
          {/* Score breakdown */}
          <div className="space-y-3">
            {dimensions.map(({ label, weight, data }) => (
              <div key={label}>
                <ScoreBar score={data.score} label={`${label} (${weight})`} />
                <p className="text-sm text-gray-600 mt-1.5 ml-0.5">{data.diagnosis}</p>
              </div>
            ))}
          </div>

          {/* Recommendations */}
          {pair.top_recommendations?.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
              <div className="text-sm font-semibold text-blue-900 mb-2">
                Top fixes for this ad
              </div>
              <ol className="space-y-1.5 list-decimal list-inside">
                {pair.top_recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-blue-800">
                    {rec}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Keyword Quality Score table */}
          {pair.keywords?.length > 0 && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Keyword Quality Scores</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="text-left px-2 py-1.5 border border-gray-200 font-medium text-gray-600">Keyword</th>
                      <th className="px-2 py-1.5 border border-gray-200 font-medium text-gray-600">QS</th>
                      <th className="px-2 py-1.5 border border-gray-200 font-medium text-gray-600">LPE</th>
                      <th className="px-2 py-1.5 border border-gray-200 font-medium text-gray-600">Clicks/mo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pair.keywords.slice(0, 10).map((kw, i) => (
                      <tr key={i} className={kw.landing_page_experience === "BELOW_AVERAGE" ? "bg-red-50" : ""}>
                        <td className="px-2 py-1.5 border border-gray-200">
                          [{kw.match_type?.charAt(0)}] {kw.keyword_text}
                        </td>
                        <td className="px-2 py-1.5 border border-gray-200 text-center">
                          <QSBadge qs={kw.quality_score} />
                        </td>
                        <td className="px-2 py-1.5 border border-gray-200 text-center">
                          <LPEBadge lpe={kw.landing_page_experience} />
                        </td>
                        <td className="px-2 py-1.5 border border-gray-200 text-center text-gray-600">
                          {kw.clicks_30d}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function QSBadge({ qs }: { qs: number | null }) {
  if (qs === null) return <span className="text-gray-400">—</span>;
  const color =
    qs >= 7 ? "text-green-700 bg-green-50" :
    qs >= 5 ? "text-yellow-700 bg-yellow-50" :
    "text-red-700 bg-red-50";
  return (
    <span className={clsx("px-1.5 py-0.5 rounded font-bold", color)}>{qs}</span>
  );
}

function LPEBadge({ lpe }: { lpe: string }) {
  const map: Record<string, string> = {
    ABOVE_AVERAGE: "text-green-700 bg-green-50",
    AVERAGE: "text-yellow-700 bg-yellow-50",
    BELOW_AVERAGE: "text-red-700 bg-red-50",
  };
  const label: Record<string, string> = {
    ABOVE_AVERAGE: "Above Avg",
    AVERAGE: "Average",
    BELOW_AVERAGE: "Below Avg",
  };
  return (
    <span className={clsx("px-1.5 py-0.5 rounded text-xs", map[lpe] || "text-gray-500 bg-gray-50")}>
      {label[lpe] || lpe}
    </span>
  );
}
