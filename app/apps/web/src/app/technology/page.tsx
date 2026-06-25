import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { Reveal, RevealGroup, RevealItem } from "@/components/Reveal";
import {
  BIAS_MITIGATIONS,
  DATA_TIERS,
  GLASS_BOX,
  TECH_STACK,
} from "@/lib/marketing-content";

export const metadata: Metadata = {
  title: "Technology · MATRIX",
  description:
    "MATRIX technical architecture: unified SUMO kernel, five impact modules, 90-second pipeline, tech stack, data tiers, glass-box provenance, and validation status.",
};

export default function TechnologyPage() {
  const [leadGlass, ...supportGlass] = GLASS_BOX;
  const LeadGlassIcon = leadGlass.icon;

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <SiteHeader />

      {/* Hero */}
      <section className="border-b border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight sm:text-5xl">
              One kernel. Five modules. Full provenance.
            </h1>
            <p className="mt-6 max-w-[65ch] text-lg leading-relaxed text-text-muted">
              A single SUMO and LLM-persona simulation produces one unified
              trajectory dataset. Five impact modules score that same reality
              in parallel, streamed to a Next.js and Deck.gl cockpit in under 90
              seconds (target).
            </p>
          </Reveal>
        </div>
      </section>

      {/* Architecture */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Architecture</h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              A natural-language query or map drop flows through the Azure
              OpenAI orchestrator into the unified simulation kernel. All five
              impact modules consume the same trajectory dataset, which is why
              Behavioral cannot contradict Ecological on the same run.
            </p>
          </Reveal>
          <Reveal delay={0.08} className="mt-10">
            <ArchitectureDiagram />
          </Reveal>
        </div>
      </section>

      {/* Why unified kernel */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Why one unified kernel?
            </h2>
          </Reveal>
          <div className="mt-10 space-y-10">
            <Reveal>
              <article className="max-w-3xl">
                <h3 className="text-lg font-semibold text-primary">
                  Separate simulators contradict
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
                  If Behavioral and Ecological ran independent physics, you
                  could get trips up alongside emissions flat because they
                  modeled different realities. A unified trajectory dataset
                  eliminates that class of inconsistency.
                </p>
              </article>
            </Reveal>
            <Reveal delay={0.06}>
              <article className="max-w-3xl border-t border-border/60 pt-10">
                <h3 className="text-lg font-semibold text-primary">
                  Why SUMO, not social simulators?
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
                  OASIS and MiroFish simulate social-media dynamics, not
                  physical agents in cities. Eclipse SUMO (DLR) is the
                  open-source urban mobility standard with native intermodal
                  support, the correct engine for pre-construction transport
                  impact.
                </p>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      {/* 90s pipeline */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              90-second pipeline
            </h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Real-time interactive visualization is the product&apos;s defining
              capability. The architecture targets a hard latency budget:
              pre-warmed persona pool, delta simulations against a nightly
              baseline, parallel module execution, and progressive UI streaming.
            </p>
          </Reveal>
          <Reveal delay={0.08} className="mt-10">
            <PipelineTimeline />
          </Reveal>
        </div>
      </section>

      {/* Tech stack (definition list, not card grid) */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Tech stack</h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Deliberate technology choices, each made for a documented reason.
            </p>
          </Reveal>

          <dl className="mt-12 divide-y divide-border/70">
            {TECH_STACK.map((group, i) => (
              <Reveal key={group.category} delay={i * 0.05}>
                <div className="grid gap-3 py-6 sm:grid-cols-[10rem_1fr] sm:gap-8">
                  <dt className="font-semibold">{group.category}</dt>
                  <dd>
                    <ul className="space-y-2">
                      {group.items.map((item) => (
                        <li
                          key={item}
                          className="text-sm leading-relaxed text-text-muted sm:text-base"
                        >
                          {item}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
              </Reveal>
            ))}
          </dl>
        </div>
      </section>

      {/* Data sources (horizontal tier strip) */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Data sources</h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Every input dataset carries a confidence tier (High, Medium, or
              Low) propagated through to impact module outputs. The confidence
              layer in the UI surfaces where the simulation is sure versus
              estimating.
            </p>
          </Reveal>

          <RevealGroup className="mt-12 space-y-0" stagger={0.06}>
            {DATA_TIERS.map((tier, i) => (
              <RevealItem key={tier.tier}>
                <div
                  className={
                    i < DATA_TIERS.length - 1
                      ? "border-b border-border/60 py-6"
                      : "py-6"
                  }
                >
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="text-sm font-semibold text-primary">
                      {tier.tier}
                    </span>
                    <span className="font-medium">{tier.label}</span>
                  </div>
                  <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted">
                    {tier.examples}
                  </p>
                </div>
              </RevealItem>
            ))}
          </RevealGroup>

          <p className="mt-6 text-sm text-text-muted">
            Full catalog in{" "}
            <span className="font-mono text-xs">
              MATRIX_Iloilo_Data_Sources.md
            </span>
            . Licensing: OSM ODbL, PSA open data, ESA Copernicus, RA 10173
            compliance.
          </p>
        </div>
      </section>

      {/* Glass box + bias */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Glass-box and bias auditor
            </h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              No number ships without{" "}
              <code className="rounded bg-surface-elevated px-1.5 py-0.5 font-mono text-xs">
                equation_id
              </code>
              ,{" "}
              <code className="rounded bg-surface-elevated px-1.5 py-0.5 font-mono text-xs">
                input_dataset_ids
              </code>
              , and a computed confidence. The LLM narrates and cites. It never
              originates a number.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-4 lg:grid-cols-2">
            <Reveal>
              <div className="rounded-xl border border-primary/25 bg-primary/5 p-6">
                <LeadGlassIcon
                  className="h-4 w-4 text-primary"
                  aria-hidden="true"
                />
                <h3 className="mt-3 font-semibold">{leadGlass.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  {leadGlass.body}
                </p>
              </div>
            </Reveal>
            <div className="space-y-4">
              {supportGlass.map((item, i) => {
                const Icon = item.icon;
                return (
                  <Reveal key={item.title} delay={0.06 + i * 0.05}>
                    <div className="rounded-xl border border-border bg-surface p-5">
                      <div className="flex items-center gap-2">
                        <Icon
                          className="h-4 w-4 text-primary"
                          aria-hidden="true"
                        />
                        <h3 className="font-semibold">{item.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-text-muted">
                        {item.body}
                      </p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>

          <Reveal className="mt-14">
            <h3 className="text-lg font-semibold">Bias mitigations</h3>
            <ul className="mt-6 divide-y divide-border/70">
              {BIAS_MITIGATIONS.map((m) => (
                <li key={m.title} className="py-5 first:pt-0 last:pb-0">
                  <p className="font-medium">{m.title}</p>
                  <p className="mt-1 max-w-[65ch] text-sm text-text-muted">
                    {m.body}
                  </p>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </section>

      {/* Validation */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Validation</h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Validation machinery is shipped and tested. Headline ground-truth
              results are withheld until mode-share and demand calibration is
              complete. Uncalibrated demand cannot produce an honest RMSE yet.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-8 sm:grid-cols-2">
            <Reveal>
              <article>
                <p className="text-sm font-semibold text-primary">VAL-01</p>
                <h3 className="mt-2 text-lg font-semibold">
                  Calderon 2014 BRT RMSE
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Back-test against the Calderon et al. (2014) BRT corridor
                  model for Iloilo City. Computed into{" "}
                  <code className="font-mono text-xs">
                    validation_report.json
                  </code>
                  . Calibration pending on corridor-to-edge mapping.
                </p>
              </article>
            </Reveal>
            <Reveal delay={0.06}>
              <article className="sm:border-l sm:border-border/60 sm:pl-8">
                <p className="text-sm font-semibold text-primary">VAL-02</p>
                <h3 className="mt-2 text-lg font-semibold">2024 flood IoU</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-muted">
                  Flood intersection-over-union against 2024 Iloilo flood events.
                  Fixture labeled{" "}
                  <strong className="text-warning">PROVISIONAL</strong> until a
                  real fixture replaces the placeholder.
                </p>
              </article>
            </Reveal>
          </div>

          <Reveal>
            <div className="mt-12 flex flex-wrap gap-4">
              <Link
                href="/app"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary-hover motion-safe:hover:-translate-y-0.5 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Try the simulator
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/about"
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-5 py-3 text-sm font-semibold text-text transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                About MATRIX
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
