import { clsx } from "clsx";

interface CoherenceScoreProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

function scoreColor(score: number): string {
  if (score < 40) return "text-red-600";
  if (score < 70) return "text-yellow-500";
  return "text-green-600";
}

function scoreBg(score: number): string {
  if (score < 40) return "bg-red-50 border-red-200";
  if (score < 70) return "bg-yellow-50 border-yellow-200";
  return "bg-green-50 border-green-200";
}

function scoreLabel(score: number): string {
  if (score < 40) return "Poor";
  if (score < 70) return "Fair";
  if (score < 85) return "Good";
  return "Excellent";
}

export function CoherenceScore({ score, size = "md" }: CoherenceScoreProps) {
  const sizeClasses = {
    sm: "w-12 h-12 text-lg",
    md: "w-16 h-16 text-2xl",
    lg: "w-24 h-24 text-4xl",
  };

  return (
    <div
      className={clsx(
        "rounded-full border-2 flex flex-col items-center justify-center font-bold",
        sizeClasses[size],
        scoreBg(score),
        scoreColor(score)
      )}
      title={`Coherence score: ${score}/100 (${scoreLabel(score)})`}
    >
      <span>{score}</span>
      {size === "lg" && (
        <span className="text-xs font-normal mt-0.5">{scoreLabel(score)}</span>
      )}
    </div>
  );
}

/** Horizontal bar variant for use in summary stats */
export function ScoreBar({ score, label }: { score: number; label: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className={clsx("font-semibold", scoreColor(score))}>{score}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all",
            score < 40 ? "bg-red-500" : score < 70 ? "bg-yellow-400" : "bg-green-500"
          )}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
