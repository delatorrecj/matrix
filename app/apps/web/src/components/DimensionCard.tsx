import { LucideIcon, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { ConfidenceChip, ConfidenceLevel } from "./ConfidenceChip";

interface DimensionCardProps {
  id: string;
  name: string;
  icon: LucideIcon;
  colorVar: string;
  score: number;
  rangeMin: number;
  rangeMax: number;
  confidence: ConfidenceLevel;
  confidenceReason?: string;
  unit?: string;
  onInspect: (id: string) => void;
  className?: string;
  style?: React.CSSProperties;
}

function getPlainEnglishSummary(id: string, name: string, score: number, unit: string): string {
  const lower = (id + " " + name).toLowerCase();
  if (lower.includes("behavioral") || lower.includes("beh")) {
    return score < 0
      ? `Commuters experience ~${Math.abs(score)}% faster travel and lower traffic delay.`
      : `Traffic delay changes by ${score}% along surrounding routes.`;
  }
  if (lower.includes("social") || lower.includes("soc")) {
    return score > 0
      ? `Public transit access and community equity improve by +${score}%.`
      : `Transit accessibility shifts by ${score}% for surrounding communities.`;
  }
  if (lower.includes("economic") || lower.includes("eco-1")) {
    const formatted = Math.abs(score) >= 1e6 ? `₱${(Math.abs(score)/1e6).toFixed(1)}M` : `₱${Math.abs(score).toLocaleString()}`;
    return score > 0
      ? `Estimated net commerce & business boost of ${formatted}.`
      : `Estimated net economic cost impact of ${formatted}.`;
  }
  if (lower.includes("ecological") || lower.includes("eco-2")) {
    return score < 0
      ? `Cleans air quality, cutting greenhouse emissions by ${Math.abs(score).toLocaleString()}${unit}.`
      : `Urban air emissions change by +${score.toLocaleString()}${unit}.`;
  }
  if (lower.includes("societal") || lower.includes("scl")) {
    return `Composite citizen wellbeing & urban health score of ${score} / 10.`;
  }
  return `Net impact: ${score > 0 ? "+" : ""}${score.toLocaleString()}${unit}`;
}

export function DimensionCard({
  id,
  name,
  icon: Icon,

  score,
  rangeMin,
  rangeMax,
  confidence,
  confidenceReason,
  unit = "",
  onInspect,
  className = "",
  style,
}: DimensionCardProps) {
  const isPositive = score > 0;
  const isNegative = score < 0;

  return (
    <div
      className={`glass rounded-xl p-5 transition-all hover:border-primary/50 active:scale-[0.99] relative overflow-hidden group cursor-pointer ${className}`}
      style={style}
      onClick={() => onInspect(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onInspect(id);
        }
      }}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2 text-text">
          <Icon className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm">{name}</h3>
        </div>
        <ConfidenceChip level={confidence} reason={confidenceReason} />
      </div>

      <div className="flex items-end justify-between mt-4">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="mono-tabular text-2xl font-bold tracking-tight text-foreground">
              {score > 0 ? "+" : ""}{score.toLocaleString()}
            </span>
            <span className="text-text-muted text-xs mono-tabular">{unit}</span>
          </div>
          
          <div className="text-xs text-text-muted mt-1 mono-tabular">
            Expected Range: {rangeMin.toLocaleString()} to {rangeMax.toLocaleString()}
          </div>
        </div>

        {/* Sparkline placeholder or trend indicator */}
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-surface">
          {isPositive ? (
            <TrendingUp className="w-4 h-4 text-success" />
          ) : isNegative ? (
            <TrendingDown className="w-4 h-4 text-error" />
          ) : (
            <Minus className="w-4 h-4 text-text-muted" />
          )}
        </div>
      </div>

      <p className="text-xs text-foreground/80 mt-3 pt-2.5 border-t border-border/50 leading-relaxed font-sans">
        {getPlainEnglishSummary(id, name, score, unit)}
      </p>
      
      
      {/* Inspect Affordance hover overlay */}
      <div className="absolute inset-0 bg-primary/0 group-hover:bg-primary/5 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
        <span className="bg-surface-elevated text-primary border border-primary/20 px-3 py-1.5 rounded-full text-xs font-medium shadow-md flex items-center gap-1.5">
          Inspect Metric
        </span>
      </div>
    </div>
  );
}
