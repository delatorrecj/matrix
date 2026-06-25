import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  MinusCircle,
  XCircle,
} from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { Reveal, RevealGroup, RevealItem } from "@/components/Reveal";
import {
  ASEAN_CITIES,
  COMPETITORS,
  PROOF_POINTS,
  TARGET_USERS,
  TEAM,
  WHY_WINS,
} from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "About · MATRIX",
  description:
    "Why MATRIX exists: the planning visibility problem, who it serves, competitive differentiation, ASEAN scaling, and Team ATLAN.",
};

function CellValue({ value }: { value: boolean | "partial" }) {
  if (value === true) {
    return (
      <span className="inline-flex items-center gap-1 text-success">
        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">Yes</span>
        <span aria-hidden="true">Yes</span>
      </span>
    );
  }
  if (value === "partial") {
    return (
      <span className="inline-flex items-center gap-1 text-warning">
        <MinusCircle className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">Partial</span>
        <span aria-hidden="true">Partial</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-text-muted">
      <XCircle className="h-4 w-4" aria-hidden="true" />
      <span className="sr-only">No</span>
      <span aria-hidden="true">No</span>
    </span>
  );
}

export default function AboutPage() {
  const [leadUser, ...otherUsers] = TARGET_USERS;
  const LeadUserIcon = leadUser.icon;

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <SiteHeader />

      {/* Hero */}
      <section className="border-b border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight sm:text-5xl">
              Pre-construction impact intelligence for ASEAN cities
            </h1>
            <p className="mt-6 max-w-[65ch] text-lg leading-relaxed text-text-muted">
              Cities build infrastructure on instinct. MATRIX gives planners,
              developers, and civic stakeholders a simulator to ask what would
              happen if we build this, before a single peso is spent.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Problem + context image */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
            <Reveal>
              <h2 className="text-3xl font-bold tracking-tight">The problem</h2>
              <p className="mt-4 max-w-[65ch] leading-relaxed text-text-muted">
                Infrastructure failure in ASEAN suburban cities is not a
                planning skill problem. It is a planning visibility problem.
              </p>

              <div className="mt-10 space-y-8">
                <article>
                  <h3 className="text-lg font-semibold">
                    Static studies cannot anticipate emergent behavior
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
                    A traffic count from 2022 will not predict how a new mall
                    reshapes every household within three kilometers.
                    Spreadsheet models ignore which jeepney route gains demand,
                    which barangay loses footfall, and which flood corridor gets
                    blocked.
                  </p>
                </article>

                <article>
                  <h3 className="text-lg font-semibold">
                    Cross-domain impacts are evaluated in silos
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
                    Environmental, transport, economic, and social reviews sit in
                    different offices. No tool currently lets a planner simulate
                    all five impact dimensions of the same project in one run.
                  </p>
                </article>

                <article>
                  <h3 className="text-lg font-semibold">
                    Existing tools require specialist expertise
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
                    Vissim, Aimsun, CityEngine, and AnyLogic need engineers or
                    modelers. None accept a plain-language what-if from a city
                    planner with no technical background.
                  </p>
                </article>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-border">
                <Image
                  src="/about-context.png"
                  alt="Iloilo City river esplanade at golden hour with the urban skyline in soft haze"
                  fill
                  className="object-cover"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
                <div
                  aria-hidden="true"
                  className="absolute inset-0 bg-gradient-to-t from-background/30 to-transparent"
                />
              </div>
              <p className="mt-8 max-w-[65ch] text-sm leading-relaxed text-text-muted">
                The cumulative cost lands on commuters paying for first-mile
                travel planners never modeled, informal vendors displaced without
                warning, barangays that flood because runoff was calculated in
                isolation, and developers whose entrances open onto the wrong
                side of the street.
              </p>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Who it's for (lead + list) */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Who it&apos;s for</h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Three constituencies ask the same pre-construction question from
              different angles.
            </p>
          </Reveal>

          <div className="mt-12 grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <Reveal>
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 sm:p-8">
                <div className="flex items-center gap-2">
                  <LeadUserIcon
                    className="h-4 w-4 text-primary"
                    aria-hidden="true"
                  />
                  <h3 className="font-semibold">{leadUser.title}</h3>
                </div>
                <p className="mt-2 text-sm font-medium text-primary">
                  {leadUser.who}
                </p>
                <p className="mt-4 text-sm leading-relaxed text-text-muted sm:text-base">
                  {leadUser.useCase}
                </p>
              </div>
            </Reveal>

            <ul className="divide-y divide-border/70">
              {otherUsers.map((user, i) => {
                const Icon = user.icon;
                return (
                  <Reveal key={user.title} delay={0.06 + i * 0.05}>
                    <li className="py-6 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-2">
                        <Icon
                          className="h-4 w-4 text-primary"
                          aria-hidden="true"
                        />
                        <h3 className="font-semibold">{user.title}</h3>
                      </div>
                      <p className="mt-1 text-xs font-medium text-primary">
                        {user.who}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-text-muted">
                        {user.useCase}
                      </p>
                    </li>
                  </Reveal>
                );
              })}
            </ul>
          </div>
        </div>
      </section>

      {/* Value proposition */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Value proposition
            </h2>
            <blockquote className="mt-6 max-w-3xl border-l-4 border-primary pl-5 text-xl font-semibold leading-snug sm:text-2xl">
              Real-time simulators tell a city what is happening. MATRIX tells
              it what will happen if it builds.
            </blockquote>
            <p className="mt-6 max-w-[65ch] leading-relaxed text-text-muted">
              Multi-billion-peso infrastructure is decided on static studies that
              age the day they are filed. MATRIX simulates community impact
              before a single peso is spent: five dimensions, explicit
              confidence, about 90 seconds, every number traceable to its data
              and equation.
            </p>
          </Reveal>

          <ul className="mt-10 space-y-4">
            {PROOF_POINTS.map((point, i) => (
              <Reveal key={point} delay={i * 0.05}>
                <li className="flex gap-3 text-sm leading-relaxed sm:text-base">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                    aria-hidden="true"
                  />
                  {point}
                </li>
              </Reveal>
            ))}
          </ul>
        </div>
      </section>

      {/* Competitive landscape */}
      <section
        id="competitive-landscape"
        className="border-t border-border/60"
      >
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Competitive landscape
            </h2>
            <p className="mt-4 max-w-[65ch] text-sm leading-relaxed text-text-muted sm:text-base">
              Based on a feature survey of tools planners actually evaluate,
              not an exhaustive procurement audit. The gap is the combination:
              natural-language input, five impact dimensions scored against one
              simulated reality, and per-dimension confidence.
            </p>
          </Reveal>

          <div className="mt-10 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-3 pr-4 font-semibold">Tool</th>
                  <th className="pb-3 pr-4 font-semibold">Strength</th>
                  <th className="pb-3 pr-4 font-semibold">NL input</th>
                  <th className="pb-3 pr-4 font-semibold">5 dims, one run</th>
                  <th className="pb-3 pr-4 font-semibold">Per-dim confidence</th>
                  <th className="pb-3 font-semibold">Needs specialist</th>
                </tr>
              </thead>
              <tbody>
                {COMPETITORS.map((row) => (
                  <tr
                    key={row.name}
                    className={cn(
                      row.name === "MATRIX"
                        ? "bg-primary/5"
                        : "border-b border-border/40 last:border-0",
                    )}
                  >
                    <td className="py-3.5 pr-4 font-semibold">{row.name}</td>
                    <td className="py-3.5 pr-4 text-text-muted">
                      {row.strength}
                    </td>
                    <td className="py-3.5 pr-4">
                      <CellValue value={row.nlInput} />
                    </td>
                    <td className="py-3.5 pr-4">
                      <CellValue value={row.fiveDimsOneRun} />
                    </td>
                    <td className="py-3.5 pr-4">
                      <CellValue value={row.perDimConfidence} />
                    </td>
                    <td className="py-3.5">
                      <CellValue value={row.needsSpecialist} />
                      {row.name === "MATRIX" && (
                        <span className="ml-1 text-xs text-text-muted">
                          (planner-friendly)
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ASEAN scaling */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Scaling across ASEAN
            </h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Geographic scaling is API-level: new city means a new OSM bounding
              box and municipal data sources. Behavioral scaling is
              prompt-level: persona archetypes reweight from Iloilo jeepney
              commuters to Jakarta ojek riders. No hardware, no IoT sensors.
            </p>
          </Reveal>

          <div className="mt-10 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-3 pr-4 font-semibold">City</th>
                  <th className="pb-3 pr-4 font-semibold">Mobility pattern</th>
                  <th className="pb-3 font-semibold">Open data</th>
                </tr>
              </thead>
              <tbody>
                {ASEAN_CITIES.map((row, i) => (
                  <tr
                    key={row.city}
                    className={cn(
                      i < ASEAN_CITIES.length - 1 && "border-b border-border/40",
                    )}
                  >
                    <td className="py-3.5 pr-4 font-semibold">{row.city}</td>
                    <td className="py-3.5 pr-4 text-text-muted">
                      {row.pattern}
                    </td>
                    <td className="py-3.5 text-text-muted">{row.openData}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Why it matters (vertical stack, not card grid) */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">
              Why MATRIX matters
            </h2>
            <p className="mt-4 max-w-[65ch] text-text-muted">
              Aligned to AAIH 2026 judging criteria, with Iloilo&apos;s 2026
              ASEAN Clean Tourist City Award (2nd time, awarded Jan 30, 2026 in
              Cebu) as the regional anchor.
            </p>
          </Reveal>

          <ol className="mt-12 divide-y divide-border/70">
            {WHY_WINS.map((item, i) => (
              <Reveal key={item.criterion} delay={i * 0.05}>
                <li className="py-8 first:pt-0 last:pb-0">
                  <p className="text-xs font-medium text-primary">
                    {item.weight}
                  </p>
                  <h3 className="mt-1 text-lg font-semibold">
                    {item.criterion}
                  </h3>
                  <p className="mt-2 max-w-[65ch] text-sm leading-relaxed text-text-muted sm:text-base">
                    {item.claim}
                  </p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* Team */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight">Team ATLAN</h2>
            <p className="mt-4 text-text-muted">
              Polytechnic University of the Philippines, ASEAN AI Hackathon
              2026, Smart Cities track
            </p>
          </Reveal>

          <RevealGroup className="mt-10 divide-y divide-border/70" stagger={0.06}>
            {TEAM.map((member) => (
              <RevealItem key={member.name}>
                <div className="py-5">
                  <p className="font-semibold">{member.name}</p>
                  <p className="mt-1 text-sm text-text-muted">{member.roles}</p>
                </div>
              </RevealItem>
            ))}
          </RevealGroup>

          <Reveal>
            <div className="mt-12 flex flex-wrap gap-4">
              <Link
                href="/technology"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary-hover motion-safe:hover:-translate-y-0.5 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Explore the technology
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link
                href="/app"
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-5 py-3 text-sm font-semibold text-text transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Launch the simulator
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
