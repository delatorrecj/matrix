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
}

export function DimensionCard({
  id,
  name,
  icon: Icon,
  colorVar,
  score,
  rangeMin,
  rangeMax,
  confidence,
  confidenceReason,
  unit = "",
  onInspect,
  className = "",
}: DimensionCardProps) {
  const isPositive = score > 0;
  const isNegative = score < 0;

  return (
    <div 
      className={`bg-surface border border-border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group cursor-pointer ${className}`}
      onClick={() => onInspect(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onInspect(id);
        }
      }}
    >
      {/* Hue bar indicator on the left edge */}
      <div 
        className="absolute left-0 top-0 bottom-0 w-1.5" 
        style={{ backgroundColor: `var(${colorVar})` }} 
      />

      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2 text-text">
          <Icon className="w-4 h-4 text-text-muted" />
          <h3 className="font-semibold text-sm">{name}</h3>
        </div>
        <ConfidenceChip level={confidence} reason={confidenceReason} />
      </div>

      <div className="flex items-end justify-between mt-4">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="mono-tabular text-2xl font-bold tracking-tight">
              {score > 0 ? "+" : ""}{score.toLocaleString()}
            </span>
            <span className="text-text-muted text-xs mono-tabular">{unit}</span>
          </div>
          
          <div className="text-xs text-text-muted mt-1 mono-tabular">
            Range: {rangeMin.toLocaleString()} to {rangeMax.toLocaleString()}
          </div>
        </div>

        {/* Sparkline placeholder or trend indicator */}
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-secondary">
          {isPositive ? (
            <TrendingUp className="w-4 h-4 text-success" />
          ) : isNegative ? (
            <TrendingDown className="w-4 h-4 text-error" />
          ) : (
            <Minus className="w-4 h-4 text-text-muted" />
          )}
        </div>
      </div>
      
      {/* Inspect Affordance hover overlay */}
      <div className="absolute inset-0 bg-primary/0 group-hover:bg-primary/5 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100 backdrop-blur-[1px]">
        <span className="bg-surface text-primary border border-primary/20 px-3 py-1.5 rounded-full text-xs font-medium shadow-sm flex items-center gap-1.5">
          Inspect Metric
        </span>
      </div>
    </div>
  );
}
