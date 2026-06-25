import { cn } from "@/lib/utils";

/**
 * MATRIX logomark — a unified simulation kernel (the center node) radiating to
 * the five impact dimensions (the pentad of satellite nodes). This is the
 * product's core thesis ("one kernel → five modules") expressed as a mark.
 *
 * Drawn with `currentColor` so it adapts to any surface/theme; the identical
 * geometry ships (in fixed brand blue) as the favicon at app/icon.svg and the
 * static asset at public/logo.svg. Keep the three in sync if the mark changes.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="MATRIX logo"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.9">
        <line x1="16" y1="16" x2="16" y2="6.5" />
        <line x1="16" y1="16" x2="25.04" y2="13.06" />
        <line x1="16" y1="16" x2="21.58" y2="23.69" />
        <line x1="16" y1="16" x2="10.42" y2="23.69" />
        <line x1="16" y1="16" x2="6.96" y2="13.06" />
      </g>
      <g fill="currentColor">
        <circle cx="16" cy="6.5" r="2.2" />
        <circle cx="25.04" cy="13.06" r="2.2" />
        <circle cx="21.58" cy="23.69" r="2.2" />
        <circle cx="10.42" cy="23.69" r="2.2" />
        <circle cx="6.96" cy="13.06" r="2.2" />
      </g>
      <rect x="12.5" y="12.5" width="7" height="7" rx="2.1" fill="currentColor" />
    </svg>
  );
}

/**
 * Horizontal lockup: mark + MATRIX wordmark. Used in app headers and the landing
 * hero. `showWordmark={false}` renders the mark alone (e.g. tight nav contexts).
 */
export function Logo({
  className,
  markClassName,
  wordmarkClassName,
  showWordmark = true,
}: {
  className?: string;
  markClassName?: string;
  wordmarkClassName?: string;
  showWordmark?: boolean;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className={cn("h-7 w-7 text-primary", markClassName)} />
      {showWordmark && (
        <span
          className={cn(
            "text-xl font-bold uppercase tracking-[0.2em] text-foreground",
            wordmarkClassName,
          )}
        >
          MATRIX
        </span>
      )}
    </span>
  );
}

export default Logo;
