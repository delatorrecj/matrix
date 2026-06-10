import { AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";

export type ConfidenceLevel = "High" | "Medium" | "Low";

interface ConfidenceChipProps {
  level: ConfidenceLevel;
  reason?: string;
  className?: string;
}

export function ConfidenceChip({ level, reason, className = "" }: ConfidenceChipProps) {
  const isHigh = level === "High";
  const isMedium = level === "Medium";
  
  const baseClasses = "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm text-[10px] uppercase tracking-wider font-semibold border";
  
  let styles = "";
  let Icon = HelpCircle;

  if (isHigh) {
    styles = "bg-success/10 text-success border-success/20";
    Icon = CheckCircle2;
  } else if (isMedium) {
    styles = "bg-warning/10 text-warning border-warning/30 border-dashed";
    Icon = AlertCircle;
  } else {
    styles = "bg-error/10 text-error border-error/30 border-dashed opacity-80";
    Icon = AlertCircle;
  }

  return (
    <div className={`${baseClasses} ${styles} ${className}`} title={reason}>
      <Icon className="w-3 h-3" />
      {level}
    </div>
  );
}
