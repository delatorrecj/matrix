"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConfidenceChip, ConfidenceLevel } from "@/components/ConfidenceChip";

interface InspectDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  metricId: string | null;
  data: ProvenanceData | null;
}

/**
 * One input dataset behind a number. Only `id` is guaranteed over the wire —
 * every other field is OPTIONAL metadata. The drawer renders an honest
 * "not provided" fallback for anything absent (glass box, PRD-F14): metadata
 * is never invented client-side.
 */
export interface InputDataset {
  id: string;
  name?: string;
  confidence?: string;
  vintage?: string;
  license?: string;
  tier?: string;
  sourceNote?: string;
}

export interface ProvenanceData {
  metric: string;
  value: string;
  range: string;
  confidence: string; // "H" | "M" | "L" (kernel-computed, methods §2)
  confidenceBasis: string;
  equationId: string;
  /** Full equation text when available; absent over today's stream. */
  equationText?: string;
  inputs: InputDataset[];
  assumptions: string[];
  references: string[];
}

/** Map the wire's H/M/L letter onto the ConfidenceChip vocabulary. */
function toConfidenceLevel(confidence: string | undefined): ConfidenceLevel {
  if (confidence === "H" || confidence === "High") return "High";
  if (confidence === "M" || confidence === "Medium") return "Medium";
  return "Low";
}

const CONFIDENCE_BOX_STYLES: Record<ConfidenceLevel, string> = {
  High: "border-success/20 bg-success/5",
  Medium: "border-warning/20 bg-warning/5",
  Low: "border-error/20 bg-error/5",
};

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

/** Stable, attribute-safe id fragment for aria-controls wiring. */
function domSafe(id: string): string {
  return id.replace(/[^a-zA-Z0-9_-]/g, "_");
}

function MetaField({
  label,
  value,
  wide = false,
}: {
  label: string;
  value?: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "col-span-2" : undefined}>
      <dt className="text-[10px] uppercase tracking-wider text-text-muted">{label}</dt>
      <dd
        className={
          value ? "text-xs font-mono text-foreground break-words" : "text-xs italic text-text-muted"
        }
      >
        {value || "not provided"}
      </dd>
    </div>
  );
}

export default function InspectDrawer({ isOpen, onClose, data }: InspectDrawerProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // A fresh inspection starts with all dataset rows collapsed.
  useEffect(() => {
    setExpandedId(null);
  }, [data]);

  // Focus management: move focus into the dialog on open, restore it on close.
  useEffect(() => {
    if (!isOpen) return;
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => {
      previouslyFocused.current?.focus?.();
    };
  }, [isOpen]);

  // ESC closes from anywhere while the dialog is open.
  useEffect(() => {
    if (!isOpen) return;
    const onDocKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onDocKeyDown);
    return () => document.removeEventListener("keydown", onDocKeyDown);
  }, [isOpen, onClose]);

  // Hand-rolled focus trap: Tab / Shift+Tab cycle within the dialog.
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab") return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusables = Array.from(
      dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    );
    if (focusables.length === 0) {
      e.preventDefault();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement;
    if (e.shiftKey) {
      if (active === first || active === dialog) {
        e.preventDefault();
        last.focus();
      }
    } else if (active === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  if (!isOpen) return null;

  const level = toConfidenceLevel(data?.confidence);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/20 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
        data-testid="inspect-backdrop"
      />

      {/* Drawer */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="inspect-drawer-title"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="fixed right-0 top-0 h-full w-full max-w-[420px] bg-surface shadow-lg z-50 flex flex-col border-l border-border transform transition-transform duration-200 ease-out outline-none"
        data-testid="inspect-drawer"
      >
        {/* Header */}
        <div className="p-6 border-b border-border flex items-start justify-between bg-secondary/30">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs px-2 py-0.5 bg-background border border-border rounded font-mono">
                {data?.equationId || "..."}
              </span>
              <h3 id="inspect-drawer-title" className="text-lg font-bold text-foreground">
                {data?.metric || "Loading..."}
              </h3>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-bold tracking-tight">{data?.value}</span>
              <span className="text-sm font-mono text-text-muted">range: {data?.range}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close inspector"
            className="p-2 hover:bg-background rounded-md text-text-muted transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
          {/* Confidence */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
              Confidence
            </h4>
            <div className={`p-4 border rounded-lg ${CONFIDENCE_BOX_STYLES[level]}`}>
              <div className="flex items-center gap-2 mb-2">
                <ConfidenceChip level={level} />
                <span className="text-sm font-medium text-foreground">
                  {level} confidence (computed)
                </span>
              </div>
              <p className="text-sm text-text-muted">{data?.confidenceBasis}</p>
            </div>
          </section>

          {/* Equation */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
              Equation
            </h4>
            <div className="p-4 bg-background border border-border rounded-lg font-mono text-sm overflow-x-auto">
              {data?.equationText || (
                <span className="text-text-muted italic font-sans">
                  Equation text not provided over the stream — {data?.equationId || "this equation"}{" "}
                  is registered in the methods ledger (methods-matrix §3).
                </span>
              )}
            </div>
          </section>

          {/* Inputs */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
              Input Datasets
            </h4>
            <div className="flex flex-col gap-2">
              {(data?.inputs?.length ?? 0) === 0 && (
                <p className="text-sm italic text-text-muted">No input datasets reported.</p>
              )}
              {data?.inputs?.map((input: InputDataset) => {
                const isExpanded = expandedId === input.id;
                const metaId = `dataset-meta-${domSafe(input.id)}`;
                return (
                  <div
                    key={input.id}
                    className="border border-border rounded-lg bg-background overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : input.id)}
                      aria-expanded={isExpanded}
                      aria-controls={metaId}
                      className="w-full p-3 flex justify-between items-center text-left group hover:bg-secondary/40 transition-colors"
                      data-testid={`dataset-row-${domSafe(input.id)}`}
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-primary group-hover:underline">
                          {input.id}
                        </div>
                        {input.name && input.name !== input.id && (
                          <div className="text-xs text-text-muted truncate">{input.name}</div>
                        )}
                      </div>
                      <span className="text-text-muted text-xs shrink-0 ml-2" aria-hidden="true">
                        {isExpanded ? "▲" : "▼"}
                      </span>
                    </button>
                    {isExpanded && (
                      <dl
                        id={metaId}
                        className="px-3 pb-3 pt-2 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border/60"
                        data-testid={`dataset-meta-${domSafe(input.id)}`}
                      >
                        <MetaField label="Vintage" value={input.vintage} />
                        <MetaField label="Confidence" value={input.confidence} />
                        <MetaField label="License" value={input.license} />
                        <MetaField label="Tier" value={input.tier} />
                        <MetaField label="Source note" value={input.sourceNote} wide />
                      </dl>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Assumptions */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
              Assumptions
            </h4>
            {(data?.assumptions?.length ?? 0) === 0 ? (
              <p className="text-sm italic text-text-muted">No assumptions reported.</p>
            ) : (
              <ul className="list-disc pl-5 space-y-2">
                {data?.assumptions?.map((ass: string, i: number) => (
                  <li key={i} className="text-sm text-text-muted">
                    {ass}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* References */}
          {(data?.references?.length ?? 0) > 0 && (
            <section>
              <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
                References
              </h4>
              <ul className="list-disc pl-5 space-y-2">
                {data?.references?.map((ref: string, i: number) => (
                  <li key={i} className="text-sm text-text-muted font-mono">
                    {ref}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
