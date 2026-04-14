import { clsx } from "clsx";
import type { AuditSummary } from "@/lib/api";

interface WastedSpendBannerProps {
  audit: AuditSummary;
}

function fmt(n: number) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function WastedSpendBanner({ audit }: WastedSpendBannerProps) {
  const score = audit.avg_coherence_score ?? 0;
  const waste = audit.total_wasted_spend_monthly ?? 0;

  const scoreBg =
    score < 40 ? "from-red-600 to-red-700" :
    score < 70 ? "from-yellow-500 to-orange-500" :
    "from-green-500 to-green-600";

  return (
    <div className={clsx("rounded-2xl p-6 text-white bg-gradient-to-r", scoreBg)}>
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Overall score */}
        <div>
          <div className="text-sm font-medium opacity-80 mb-1">Overall Coherence Score</div>
          <div className="text-5xl font-bold">
            {score.toFixed(0)}<span className="text-2xl opacity-70">/100</span>
          </div>
          <div className="text-sm opacity-80 mt-1">
            {score < 40 ? "Critical — significant spend waste detected" :
             score < 70 ? "Below average — room for meaningful improvement" :
             "Good — minor optimisations available"}
          </div>
        </div>

        {/* Waste estimate */}
        {waste > 0 && (
          <div className="bg-white/20 rounded-xl p-4 text-center">
            <div className="text-sm font-medium opacity-90 mb-1">Est. monthly waste</div>
            <div className="text-4xl font-bold">{fmt(waste)}</div>
            <div className="text-xs opacity-80 mt-1">from poor Quality Scores</div>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 text-center w-full mt-2">
          <Stat value={audit.total_ads} label="Ads audited" />
          <Stat value={audit.ads_below_average_lp_experience} label="Below Avg LPE" highlight />
          <Stat value={`${score.toFixed(0)}/100`} label="Avg coherence" />
        </div>
      </div>
    </div>
  );
}

function Stat({
  value,
  label,
  highlight,
}: {
  value: number | string;
  label: string;
  highlight?: boolean;
}) {
  return (
    <div className="bg-white/15 rounded-lg py-3 px-2">
      <div className={clsx("text-2xl font-bold", highlight && typeof value === "number" && value > 0 && "text-red-100")}>
        {value}
      </div>
      <div className="text-xs opacity-75 mt-0.5">{label}</div>
    </div>
  );
}
