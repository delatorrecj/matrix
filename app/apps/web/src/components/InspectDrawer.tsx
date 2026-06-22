"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConfidenceChip, ConfidenceLevel } from "@/components/ConfidenceChip";
import { X } from "lucide-react";

interface InspectDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  metricId: string | null;
  data: ProvenanceData | null;
  children?: React.ReactNode;
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
          value ? "text-xs font-mono text-foreground wrap-break-word" : "text-xs italic text-text-muted"
        }
      >
        {value || "not provided"}
      </dd>
    </div>
  );
}

export default function InspectDrawer({ isOpen, onClose, data, children }: InspectDrawerProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [isExpanded, setIsExpanded] = useState(false);

  // A fresh inspection starts with all dataset rows collapsed.
  useEffect(() => {
    setExpandedId(null);
    setIsExpanded(false);
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
    <div
      ref={dialogRef}
      role="region"
      aria-labelledby="inspect-drawer-title"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      className="absolute right-6 top-24 w-[360px] md:w-[400px] z-30 flex flex-col bg-surface shadow-2xl border border-border rounded-xl outline-none overflow-hidden transition-[max-height] duration-300 ease-in-out"
      style={{
        maxHeight: isExpanded ? 'calc(100vh - 12rem)' : 'var(--panel-peek-height, 270px)'
      }}
      data-testid="inspect-drawer"
    >
      {/* Header */}
      <div className="p-6 border-b border-border flex items-start justify-between bg-surface-elevated shrink-0">
        <div className="flex-1 pr-4">
          <div className="mb-2">
            <span className="text-[10px] uppercase font-bold text-text-muted px-2 py-0.5 bg-surface border border-border rounded font-mono inline-block">
              {data?.equationId || "..."}
            </span>
          </div>
          <h3 id="inspect-drawer-title" className="text-xl font-bold text-foreground leading-tight">
            {data?.metric || "Loading..."}
          </h3>
          <div className="flex flex-col mt-4">
            <span className="text-4xl font-mono font-bold tracking-tight">{data?.value}</span>
            <span className="text-xs font-mono text-text-muted mt-1">range: {data?.range}</span>
          </div>
        </div>
          <button
            onClick={onClose}
            aria-label="Close inspector"
            className="p-2.5 bg-surface border border-border shadow-sm hover:bg-surface-elevated rounded-full text-text-muted hover:text-foreground transition-all shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!isExpanded && (
          <button
            onClick={() => setIsExpanded(true)}
            className="w-full py-2 bg-surface hover:bg-surface-elevated text-xs font-semibold text-primary transition-colors flex items-center justify-center gap-2 mt-auto"
          >
            Show details
          </button>
        )}

        <div className={`flex-1 overflow-y-auto p-6 flex flex-col gap-8 transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0 invisible'}`}>
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
            <div className="p-4 bg-surface-elevated border border-border rounded-lg font-mono text-sm overflow-x-auto">
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
                const isItemExpanded = expandedId === input.id;
                const metaId = `dataset-meta-${domSafe(input.id)}`;
                return (
                  <div
                    key={input.id}
                    className="border border-border rounded-lg bg-surface-elevated overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => setExpandedId(isItemExpanded ? null : input.id)}
                      aria-expanded={isItemExpanded}
                      aria-controls={metaId}
                      className="w-full p-3 flex justify-between items-center text-left group hover:bg-surface transition-colors"
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
                        {isItemExpanded ? "▲" : "▼"}
                      </span>
                    </button>
                    {isItemExpanded && (
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

          {children && (
            <div className="pt-2 border-t border-border/50">
              {children}
            </div>
          )}
        </div>

        {isExpanded && (
          <button
            onClick={() => setIsExpanded(false)}
            className="w-full py-3 bg-surface hover:bg-surface-elevated text-xs font-semibold text-text-muted border-t border-border transition-colors flex items-center justify-center gap-2"
          >
            Collapse details
          </button>
        )}
      </div>
  );
}
