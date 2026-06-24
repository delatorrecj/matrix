/**
 * Bilingual synthesis splitting (CR-010, WS-5 T5.2).
 *
 * The kernel emits the BLUF brief as the full English version, a `=== HILIGAYNON ===`
 * marker line, then the full Hiligaynon version (delimited, never inline-interleaved —
 * methods §4). This module splits on that marker so the UI renders ONE language at a
 * time, driven by the LanguageProvider toggle. Glass box: splitting is presentation
 * only; every `[EQN-ID]` citation survives in whichever half is shown.
 */

import type { Language } from "@/components/LanguageProvider";

/** Must match `HILIGAYNON_MARKER` in packages/kernel/matrix_kernel/synthesis.py. */
export const HILIGAYNON_MARKER = "=== HILIGAYNON ===";

/**
 * The BLUF section headers the synthesis prompt emits (CR-010), in order. The headers
 * stay in English in both language halves (see the kernel prompt). Consumers use this to
 * bold the headers and to extract sections for the brief.
 */
export const BLUF_HEADERS = [
  "HEADLINE",
  "WHAT WE SIMULATED",
  "KEY FINDINGS",
  "RECOMMENDATION",
  "KEY RISK",
] as const;

export type BlufHeader = (typeof BLUF_HEADERS)[number];

/**
 * Parse a single-language brief into its labelled sections. Tolerant of a missing
 * section (returns "" for it) and of headers that appear with or without a trailing
 * newline. Returns the sections in canonical order plus any preamble before the first
 * header (rare; kept so nothing is silently dropped).
 */
export function parseBlufSections(brief: string): Record<BlufHeader, string> {
  const out = Object.fromEntries(BLUF_HEADERS.map((h) => [h, ""])) as Record<BlufHeader, string>;
  if (!brief) return out;
  // Build an alternation that anchors each header at a line start.
  const headerAlt = BLUF_HEADERS.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const re = new RegExp(`^[ \\t]*(${headerAlt})[ \\t]*$`, "im");
  // Walk the text header-by-header.
  let current: BlufHeader | null = null;
  const lines = brief.split(/\r?\n/);
  for (const line of lines) {
    const m = re.exec(line);
    if (m) {
      current = m[1].toUpperCase() as BlufHeader;
      continue;
    }
    if (current) {
      out[current] = (out[current] ? out[current] + "\n" : "") + line;
    }
  }
  for (const h of BLUF_HEADERS) out[h] = out[h].trim();
  return out;
}

// Tolerant matcher: allow leading/trailing spaces and a flexible run of '=' so a minor
// LLM formatting wobble (e.g. "==== HILIGAYNON ====") still splits cleanly.
const MARKER_RE = /^[ \t]*={2,}\s*HILIGAYNON\s*={2,}[ \t]*$/im;

export interface BilingualBrief {
  english: string;
  /** The Hiligaynon half, or "" when the narrative carried no marker (graceful fallback). */
  hiligaynon: string;
  /** True when a Hiligaynon section was actually present. */
  hasHiligaynon: boolean;
}

/** Split a (possibly bilingual) narrative into its English and Hiligaynon halves. */
export function splitBilingual(narrative: string | undefined): BilingualBrief {
  const text = narrative ?? "";
  const match = MARKER_RE.exec(text);
  if (!match) {
    return { english: text.trim(), hiligaynon: "", hasHiligaynon: false };
  }
  const english = text.slice(0, match.index).trim();
  const hiligaynon = text.slice(match.index + match[0].length).trim();
  return { english, hiligaynon, hasHiligaynon: hiligaynon.length > 0 };
}

/**
 * The half to display for the chosen language. Falls back to English when the
 * requested Hiligaynon half is absent (older runs, or the marker never emitted) — we
 * never show an empty narrative or invent a translation.
 */
export function narrativeForLanguage(
  narrative: string | undefined,
  language: Language,
): string {
  const { english, hiligaynon, hasHiligaynon } = splitBilingual(narrative);
  if (language === "hil" && hasHiligaynon) return hiligaynon;
  return english;
}
