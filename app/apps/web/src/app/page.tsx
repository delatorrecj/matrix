import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, SlidersHorizontal } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { LogoMark } from "@/components/Logo";
import { Reveal, RevealGroup, RevealItem } from "@/components/Reveal";
import {
  DIMENSIONS,
  GLASS_BOX,
  PROBLEM_CARDS,
} from "@/lib/marketing-content";

export const metadata: Metadata = {
  title: "MATRIX · Pre-construction Urban Impact Simulator",
  description:
    "MATRIX simulates how a new road, transit line, school, or flood closure ripples across Iloilo City across five dimensions of urban impact, with every number traceable to its source.",
};

const ctaPrimary =
  "inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary-hover hover:shadow-primary/30 motion-safe:hover:-translate-y-0.5 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

const ctaSecondary =
  "inline-flex items-center gap-2 rounded-xl border border-border bg-surface/90 px-5 py-3 text-sm font-semibold text-text backdrop-blur-sm transition-all hover:border-primary hover:text-primary motion-safe:hover:-translate-y-0.5 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export default function Landing() {
  const [leadGlass, ...supportGlass] = GLASS_BOX;
  const LeadGlassIcon = leadGlass.icon;

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <SiteHeader />

      {/* Hero */}
      <section className="relative min-h-[100dvh] overflow-hidden">
        <Image
          src="/hero-iloilo.png"
          alt="Abstract aerial map of a river-delta city with glowing blue network lines"
          fill
          priority
          className="object-cover object-center"
          sizes="100vw"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-b from-background/88 via-background/78 to-background/95 dark:from-background/92 dark:via-background/82 dark:to-background/98"
        />

        <div className="relative mx-auto flex min-h-[100dvh] max-w-7xl flex-col justify-center px-5 pb-16 pt-24 sm:px-8">
          <Reveal>
            <h1 className="max-w-3xl text-balance text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              See the impact <span className="text-primary">before</span> you
              build it.
            </h1>
          </Reveal>

          <Reveal delay={0.08}>
            <p className="mt-6 max-w-[65ch] text-pretty text-lg leading-relaxed text-text-muted">
              Describe a proposed project in plain language, or pick a preset.
              Get scored, confidence-anchored estimates across five impact
              dimensions — every number inspectable.
            </p>
          </Reveal>

          <Reveal delay={0.14}>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link href="/app" className={ctaPrimary}>
                Launch MATRIX
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link href="/builder" className={ctaSecondary}>
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                Build a scenario
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Problem (editorial list) */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
              Infrastructure fails on visibility, not intent.
            </h2>
            <p className="mt-4 max-w-[65ch] leading-relaxed text-text-muted">
              Multi-billion-peso decisions rely on static feasibility studies
              that age the day they are filed. Three failure patterns repeat
              across ASEAN cities.
            </p>
          </Reveal>

          <ol className="mt-14 divide-y divide-border/70">
            {PROBLEM_CARDS.map((card, i) => (
              <Reveal key={card.title} delay={i * 0.06}>
                <li className="grid gap-4 py-8 sm:grid-cols-[4rem_1fr] sm:gap-8 sm:py-10">
                  <span
                    className="font-mono text-4xl font-semibold tabular-nums text-primary/40 sm:text-5xl"
                    aria-hidden="true"
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <h3 className="text-lg font-semibold leading-snug">
                      {card.title}
                    </h3>
                    <p className="mt-2 max-w-[65ch] text-sm leading-relaxed text-text-muted sm:text-base">
                      {card.body}
                    </p>
                  </div>
                </li>
              </Reveal>
            ))}
          </ol>

          <Reveal>
            <Link
              href="/about"
              className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary transition-colors hover:text-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Read the full problem and value proposition
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Reveal>
        </div>
      </section>

      {/* One kernel, five dimensions (split + bento) */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
          <div className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_1.1fr] lg:items-start">
            <Reveal>
              <LogoMark className="h-14 w-14 text-primary" />
              <h2 className="mt-6 text-3xl font-bold tracking-tight sm:text-4xl">
                One simulation. Five dimensions.
              </h2>
              <p className="mt-4 max-w-[65ch] leading-relaxed text-text-muted">
                A single SUMO agent simulation produces one shared trajectory
                dataset. All five impact modules score that same reality in
                parallel, which is why the results stay internally consistent.
              </p>
              <Link
                href="/technology"
                className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary transition-colors hover:text-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                See the architecture
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Reveal>

            <RevealGroup className="grid gap-3 sm:grid-cols-2" stagger={0.07}>
              {DIMENSIONS.map((d) => (
                <RevealItem key={d.name}>
                  <div className="glass h-full rounded-xl p-4 transition-transform motion-safe:hover:-translate-y-0.5">
                    <div className="flex items-center gap-2.5">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: d.color }}
                        aria-hidden="true"
                      />
                      <span className="font-semibold">{d.name}</span>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-text-muted">
                      {d.blurb}
                    </p>
                  </div>
                </RevealItem>
              ))}
            </RevealGroup>
          </div>
        </div>
      </section>

      {/* Glass box (1 + 2 asymmetric) */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <h2 className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
              No black boxes. Every number, accountable.
            </h2>
            <p className="mt-4 max-w-[65ch] leading-relaxed text-text-muted">
              A planning decision is only as trustworthy as the evidence behind
              it. MATRIX is built so that anyone can audit any figure it
              produces.
            </p>
          </Reveal>

          <div className="mt-12 grid gap-4 lg:grid-cols-2">
            <Reveal className="lg:row-span-2">
              <div className="flex h-full flex-col justify-between rounded-xl border border-primary/25 bg-surface p-6 sm:p-8">
                <div>
                  <LeadGlassIcon
                    className="h-5 w-5 text-primary"
                    aria-hidden="true"
                  />
                  <h3 className="mt-4 text-xl font-semibold">
                    {leadGlass.title}
                  </h3>
                  <p className="mt-3 max-w-[65ch] text-sm leading-relaxed text-text-muted sm:text-base">
                    {leadGlass.body}
                  </p>
                </div>
              </div>
            </Reveal>

            {supportGlass.map((item, i) => {
              const Icon = item.icon;
              return (
                <Reveal key={item.title} delay={0.08 + i * 0.06}>
                  <div className="rounded-xl border border-border bg-surface p-5 sm:p-6">
                    <div className="flex items-center gap-2">
                      <Icon
                        className="h-4 w-4 shrink-0 text-primary"
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
      </section>

      {/* Differentiation snapshot */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/8 to-transparent p-6 sm:p-10">
              <p className="max-w-3xl text-xl font-semibold leading-snug sm:text-2xl">
                Natural-language input, five impact dimensions in one run, and
                per-dimension confidence: a combination we have not found in the
                tools planners typically evaluate.
              </p>
              <p className="mt-4 max-w-[65ch] text-sm leading-relaxed text-text-muted sm:text-base">
                Real-time IoT simulators tell a city what is happening. MATRIX
                tells it what will happen if it builds, with no sensors and no
                black box.
              </p>
              <Link
                href="/about#competitive-landscape"
                className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary transition-colors hover:text-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                View full competitive comparison
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="border-t border-border/60 bg-surface/40">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
          <Reveal>
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-2xl font-bold tracking-tight">
                  Ready to run a what-if?
                </p>
                <p className="mt-2 max-w-md text-text-muted">
                  Open the simulator, or read more about the project and
                  technology.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/app" className={ctaPrimary}>
                  Launch MATRIX
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <Link href="/about" className={ctaSecondary}>
                  About MATRIX
                </Link>
                <Link href="/technology" className={ctaSecondary}>
                  Technology
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
