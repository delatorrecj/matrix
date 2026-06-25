import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ScanSearch, Scale, SlidersHorizontal } from "lucide-react";
import { Logo, LogoMark } from "@/components/Logo";
import { HeaderControls } from "@/components/HeaderControls";

export const metadata: Metadata = {
  title: "MATRIX · Pre-construction Urban Impact Simulator",
  description:
    "MATRIX simulates how a new road, transit line, school, or flood closure ripples across Iloilo City — across five dimensions of urban impact, with every number traceable to its source.",
};

// The five impact dimensions, with the hues used throughout the simulator.
const DIMENSIONS: { name: string; color: string; blurb: string }[] = [
  { name: "Behavioral", color: "#2563EB", blurb: "How people re-route and shift travel when the network changes." },
  { name: "Social", color: "#DB2777", blurb: "Who is affected or displaced — and how the burden is shared." },
  { name: "Economic", color: "#CA8A04", blurb: "Construction cost, land value, and livelihoods along the corridor." },
  { name: "Ecological", color: "#16A34A", blurb: "Emissions and flood exposure under the simulated change." },
  { name: "Societal", color: "#9333EA", blurb: "Access to services and long-run wellbeing across barangays." },
];

const GLASS_BOX: { icon: React.ElementType; title: string; body: string }[] = [
  {
    icon: ScanSearch,
    title: "Every number is traceable",
    body: "Each result carries the equation that produced it, the datasets it drew from, and a computed confidence level. Open the Inspect drawer on any figure to see its full provenance.",
  },
  {
    icon: Scale,
    title: "Honest by construction",
    body: "Outputs are confidence-anchored ranges, not false-precision point estimates. The AI narrates and cites the results — it never originates a number. A bias auditor keeps a public audit log.",
  },
  {
    icon: SlidersHorizontal,
    title: "One reality, five lenses",
    body: "A single agent-based simulation feeds all five impact modules, so the dimensions can never contradict each other. You score one simulated reality, not five disconnected guesses.",
  },
];

export default function Landing() {
  return (
    <main className="min-h-dvh bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5 sm:px-8">
          <Logo />
          <div className="flex items-center gap-3">
            <HeaderControls />
            <Link
              href="/app"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/20 transition-all hover:bg-primary-hover active:scale-[0.98]"
            >
              Launch simulator
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_50%_-10%,rgba(29,78,216,0.18),transparent)]"
        />
        <div className="mx-auto max-w-6xl px-5 pb-20 pt-20 sm:px-8 sm:pt-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
            ASEAN AI Hackathon 2026 · Smart Cities · Iloilo City pilot
          </span>

          <h1 className="mt-6 max-w-3xl text-balance text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
            See the impact <span className="text-primary">before</span> you build it.
          </h1>

          <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-text-muted">
            MATRIX is a multi-agent digital twin that simulates how a new road, transit
            line, school, or flood closure ripples across a city — scored across five
            dimensions of urban impact, with every number traceable to its source.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/app"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary-hover active:scale-[0.98]"
            >
              Launch the simulator
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              href="/builder"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-5 py-3 text-sm font-semibold text-text transition-colors hover:border-primary hover:text-primary"
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Build a scenario
            </Link>
          </div>
        </div>
      </section>

      {/* One kernel → five dimensions */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_1.4fr] lg:items-center">
            <div>
              <div className="flex items-center gap-4">
                <LogoMark className="h-16 w-16 text-primary" />
                <div className="text-sm font-mono uppercase tracking-widest text-text-muted">
                  one kernel
                  <br />→ five dimensions
                </div>
              </div>
              <h2 className="mt-7 text-3xl font-bold tracking-tight">
                One simulation. Five dimensions.
              </h2>
              <p className="mt-4 text-text-muted leading-relaxed">
                A single SUMO agent simulation produces one shared trajectory dataset.
                All five impact modules score <em>that same reality</em> in parallel —
                which is exactly why the results stay internally consistent.
              </p>
            </div>

            <ul className="grid gap-3 sm:grid-cols-2">
              {DIMENSIONS.map((d) => (
                <li
                  key={d.name}
                  className="glass rounded-xl p-4 transition-transform motion-safe:hover:-translate-y-0.5"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: d.color }}
                      aria-hidden="true"
                    />
                    <span className="font-semibold">{d.name}</span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-text-muted">{d.blurb}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Glass box */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <h2 className="max-w-2xl text-3xl font-bold tracking-tight">
            No black boxes. Every number, accountable.
          </h2>
          <p className="mt-4 max-w-2xl text-text-muted leading-relaxed">
            A planning decision is only as trustworthy as the evidence behind it. MATRIX
            is built so that anyone can audit any figure it produces.
          </p>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {GLASS_BOX.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.title} className="rounded-xl border border-border bg-surface p-5">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 font-semibold">{c.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-text-muted">{c.body}</p>
                </div>
              );
            })}
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-4 rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 to-transparent p-6">
            <p className="text-lg font-semibold">Ready to run a what-if?</p>
            <Link
              href="/app"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary-hover active:scale-[0.98]"
            >
              Launch the simulator
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-10 text-sm text-text-muted sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div className="flex items-center gap-2.5">
            <LogoMark className="h-5 w-5 text-text-muted" />
            <span>
              Built by <span className="text-text">Team ATLAN</span> · Polytechnic
              University of the Philippines
            </span>
          </div>
          <p className="font-mono text-xs">
            SUMO · Azure OpenAI · Next.js + Deck.gl · Map data © OpenStreetMap (ODbL)
          </p>
        </div>
      </footer>
    </main>
  );
}
