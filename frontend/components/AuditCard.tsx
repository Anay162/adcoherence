import { clsx } from "clsx";
import type { AdPagePair } from "@/lib/api";
import { CoherenceScore } from "./CoherenceScore";
import { DiagnosisPanel } from "./DiagnosisPanel";

interface AuditCardProps {
  pair: AdPagePair;
}

export function AuditCard({ pair }: AuditCardProps) {
  const worstLpe = pair.keywords?.reduce<string>((worst, kw) => {
    const order = ["BELOW_AVERAGE", "AVERAGE", "ABOVE_AVERAGE", "UNKNOWN"];
    return order.indexOf(kw.landing_page_experience) < order.indexOf(worst)
      ? kw.landing_page_experience
      : worst;
  }, "UNKNOWN");

  const topKw = pair.keywords?.find((k) => k.quality_score !== null) ?? pair.keywords?.[0];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Header row */}
      <div className="flex items-start gap-4">
        <CoherenceScore score={pair.overall_score} size="md" />

        <div className="flex-1 min-w-0">
          {/* Breadcrumb */}
          <div className="text-xs text-gray-400 mb-1 truncate">
            {pair.campaign_name}
            <span className="mx-1">›</span>
            {pair.ad_group_name}
          </div>

          {/* Ad vs page side-by-side */}
          <div className="grid grid-cols-2 gap-4">
            {/* Ad copy */}
            <div>
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Ad Headlines
              </div>
              <ul className="space-y-0.5">
                {pair.ad_headlines?.slice(0, 3).map((h, i) => (
                  <li key={i} className="text-sm text-gray-800 truncate">{h}</li>
                ))}
              </ul>
            </div>

            {/* Landing page */}
            <div>
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Landing Page
              </div>
              <div className="text-sm text-gray-800 line-clamp-2">
                {pair.page_h1 || pair.page_title || "No H1 found"}
              </div>
              <a
                href={pair.final_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline truncate block mt-0.5"
              >
                {pair.final_url}
              </a>
            </div>
          </div>
        </div>

        {/* Right side: badges + waste */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          {pair.estimated_monthly_waste != null && pair.estimated_monthly_waste > 0.5 && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-center">
              <div className="text-xs text-red-600 font-medium">Est. waste</div>
              <div className="text-lg font-bold text-red-700">
                ${pair.estimated_monthly_waste.toLocaleString("en-US", { maximumFractionDigits: 0 })}<span className="text-xs font-normal">/mo</span>
              </div>
            </div>
          )}
          {pair.waste_type === "conversion_lift" && (pair.additional_conversions_monthly ?? 0) > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 text-center">
              <div className="text-xs text-orange-600 font-medium">Possible</div>
              <div className="text-base font-bold text-orange-700">
                +{pair.additional_conversions_monthly?.toFixed(1)} conv/mo
              </div>
            </div>
          )}

          {/* QS + LPE badges */}
          <div className="flex gap-1.5 flex-wrap justify-end">
            {topKw?.quality_score != null && (
              <QSChip qs={topKw.quality_score} />
            )}
            {worstLpe !== "UNKNOWN" && <LPEChip lpe={worstLpe} />}
            {!pair.mobile_friendly && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                Not mobile-friendly
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Scrape error warning */}
      {pair.scrape_error && (
        <div className="mt-3 text-xs text-orange-700 bg-orange-50 border border-orange-200 rounded-md px-3 py-2">
          Page could not be scraped: {pair.scrape_error}
        </div>
      )}

      <DiagnosisPanel pair={pair} />
    </div>
  );
}

function QSChip({ qs }: { qs: number }) {
  const color =
    qs >= 7 ? "bg-green-50 text-green-700 border-green-200" :
    qs >= 5 ? "bg-yellow-50 text-yellow-700 border-yellow-200" :
    "bg-red-50 text-red-700 border-red-200";
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium", color)}>
      QS {qs}
    </span>
  );
}

function LPEChip({ lpe }: { lpe: string }) {
  const map: Record<string, string> = {
    ABOVE_AVERAGE: "bg-green-50 text-green-700 border-green-200",
    AVERAGE: "bg-yellow-50 text-yellow-700 border-yellow-200",
    BELOW_AVERAGE: "bg-red-50 text-red-700 border-red-200",
  };
  const labels: Record<string, string> = {
    ABOVE_AVERAGE: "LPE: Above Avg",
    AVERAGE: "LPE: Average",
    BELOW_AVERAGE: "LPE: Below Avg",
  };
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium", map[lpe] || "bg-gray-50 text-gray-500 border-gray-200")}>
      {labels[lpe] ?? lpe}
    </span>
  );
}
