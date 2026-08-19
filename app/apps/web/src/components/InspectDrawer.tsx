"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConfidenceChip, ConfidenceLevel, toConfidenceLevel } from "@/components/ConfidenceChip";
import { PlannerFeedback } from "@/components/PlannerFeedback";
import { resolveReferenceMeta } from "@/lib/datasets";
import { X, ChevronDown, ExternalLink } from "lucide-react";

interface InspectDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  metricId: string | null;
  data: ProvenanceData | null;
  runId?: string | null;
  site?: CorridorSite | null;
  children?: React.ReactNode;
}

/** Kernel corridor resolution shown under Inspect (method + names, never GIS ids). */
export interface CorridorSite {
  method?: string | null;
  corridor?: string | null;
  fromCross?: string | null;
  toCross?: string | null;
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
  url?: string;
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

export default function InspectDrawer({ isOpen, onClose, data, runId, site, children }: InspectDrawerProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [isExpanded, setIsExpanded] = useState(false);

  // A fresh inspection starts collapsed; reset peek/expand when drawer closes too.
  useEffect(() => {
    setExpandedId(null);
    setIsExpanded(false);
  }, [data]);

  useEffect(() => {
    if (isOpen) return;
    setExpandedId(null);
    setIsExpanded(false);
  }, [isOpen]);

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
  // Surface the specific capping factor next to the confidence chip (DSD §8 /
  // methods §2 Low-Confidence Protocol). The modules record it in assumptions
  // (e.g. "confidence capped at M: …"); pull it forward instead of burying it.
  const cappingReason =
    level !== "High"
      ? data?.assumptions?.find((a) => /cap|confiden/i.test(a))
      : undefined;
  const corridorVolumeEq =
    data?.equationId === "BEH-1" || data?.equationId === "BEH-3";
  const fidelityNotice =
    corridorVolumeEq && (level === "Low" || data?.assumptions?.some((a) => /VAL-01|uncalibrated/i.test(a)))
      ? "Iloilo corridor volumes are directional, not city-calibrated. VAL-01 vs Calderon 2014 is published in Analytics → Validation (FAIL is FAIL). Magnitudes are not a passing calibration."
      : undefined;

  return (
    <div
      ref={dialogRef}
      role="region"
      aria-labelledby="inspect-drawer-title"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      className="glass-strong absolute inset-2 z-30 flex flex-col rounded-xl outline-none min-h-0"
      style={{
        maxHeight: isExpanded ? "100%" : "var(--panel-peek-height, 270px)",
      }}
      data-testid="inspect-drawer"
    >
      <button
        onClick={onClose}
        aria-label="Close inspector"
        className="absolute top-3 right-3 z-20 p-2.5 bg-surface border border-border shadow-sm hover:bg-surface-elevated rounded-full text-text-muted hover:text-foreground transition-all"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="flex-1 overflow-y-auto min-h-0 rounded-xl">
        <div className="p-6 pr-16 border-b border-border bg-surface-elevated">
          <div className="mb-2">
            <span className="text-[10px] uppercase font-bold text-text-muted px-2 py-0.5 bg-surface border border-border rounded font-mono inline-block">
              {data?.equationId || "..."}
            </span>
          </div>
          <h3 id="inspect-drawer-title" className="text-xl font-bold text-foreground leading-tight">
            {data?.metric || "Loading..."}
          </h3>
          {site?.method ? (
            <p className="mt-2 text-xs font-mono text-text-muted wrap-break-word" data-testid="inspect-corridor-site">
              {site.method}
              {site.corridor ? ` · ${site.corridor}` : ""}
              {site.fromCross && site.toCross
                ? ` from ${site.fromCross} to ${site.toCross}`
                : site.fromCross
                  ? ` from ${site.fromCross}`
                  : site.toCross
                    ? ` up to ${site.toCross}`
                    : ""}
            </p>
          ) : null}
          <div className="flex flex-col mt-4 min-w-0">
            <span className="text-4xl font-mono font-bold tracking-tight wrap-break-word">{data?.value}</span>
            <span className="text-xs font-mono text-text-muted mt-1 wrap-break-word">range: {data?.range}</span>
            {fidelityNotice && (
              <p
                className="mt-3 text-xs leading-relaxed text-foreground bg-warning/10 border border-warning/30 rounded-lg px-2.5 py-2"
                data-testid="inspect-fidelity-notice"
              >
                {fidelityNotice}
              </p>
            )}
          </div>
        </div>

        {isExpanded && (
          <div className="p-6 flex flex-col gap-8">
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
              {cappingReason && (
                <p className="text-xs text-foreground mt-2 pt-2 border-t border-border/50">
                  <span className="font-semibold">Capped by:</span> {cappingReason}
                </p>
              )}
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
                  Equation text not provided over the stream. {data?.equationId || "This equation"}{" "}
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
                      <ChevronDown
                        className={`text-text-muted shrink-0 ml-2 h-4 w-4 transition-transform ${isItemExpanded ? "rotate-180" : ""}`}
                        aria-hidden="true"
                      />
                    </button>
                    {isItemExpanded && (
                      <dl
                        id={metaId}
                        className="px-3 pb-3 pt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 border-t border-border/60"
                        data-testid={`dataset-meta-${domSafe(input.id)}`}
                      >
                        <MetaField label="Vintage" value={input.vintage} />
                        <MetaField label="Confidence" value={input.confidence} />
                        <MetaField label="License" value={input.license} />
                        <MetaField label="Tier" value={input.tier} />
                        <MetaField label="Source note" value={input.sourceNote} wide />
                        {input.url ? (
                          <div className="col-span-2">
                            <dt className="text-[10px] uppercase tracking-wider text-text-muted">Source</dt>
                            <dd>
                              <a
                                href={input.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-primary hover:underline inline-flex items-center gap-1 wrap-break-word"
                              >
                                {input.url}
                                <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
                              </a>
                            </dd>
                          </div>
                        ) : null}
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
                {data?.references?.map((ref: string, i: number) => {
                  const refMeta = resolveReferenceMeta(ref);
                  return (
                    <li key={i} className="text-sm text-text-muted">
                      {refMeta?.url ? (
                        <a
                          href={refMeta.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-primary hover:underline inline-flex items-center gap-1"
                        >
                          {refMeta.name || ref}
                          <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
                        </a>
                      ) : (
                        <span className="font-mono">{ref}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {/* Source datasets (attribution links) */}
          {(data?.inputs?.some((input) => input.url) ?? false) && (
            <section>
              <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">
                Sources
              </h4>
              <ul className="space-y-2">
                {data?.inputs
                  ?.filter((input) => input.url)
                  .map((input) => (
                    <li key={input.id}>
                      <a
                        href={input.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                      >
                        {input.name || input.id}
                        <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
                      </a>
                      {input.license && (
                        <span className="text-xs text-text-muted ml-1">({input.license})</span>
                      )}
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

          <PlannerFeedback runId={runId ?? null} equationId={data?.equationId ?? null} />
          </div>
        )}
      </div>

      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full py-2 bg-surface hover:bg-surface-elevated text-xs font-semibold text-primary transition-colors flex items-center justify-center gap-2 shrink-0"
        >
          Show details
        </button>
      )}

      {isExpanded && (
        <button
          onClick={() => setIsExpanded(false)}
          className="w-full py-3 bg-surface hover:bg-surface-elevated text-xs font-semibold text-text-muted border-t border-border transition-colors flex items-center justify-center gap-2 shrink-0"
        >
          Collapse details
        </button>
      )}
    </div>
  );
}
