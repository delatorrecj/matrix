import Link from "next/link";
import { LogoMark } from "@/components/Logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-surface/40">
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-2.5">
            <LogoMark className="mt-0.5 h-5 w-5 shrink-0 text-text-muted" />
            <div className="text-sm text-text-muted">
              <p>
                Built by <span className="text-text">Team ATLAN</span> ·
                Polytechnic University of the Philippines
              </p>
              <p className="mt-1 text-xs">Pilot: Iloilo City</p>
            </div>
          </div>

          <nav
            aria-label="Footer"
            className="flex flex-wrap gap-x-5 gap-y-2 text-sm"
          >
            <Link
              href="/about"
              className="text-text-muted transition-colors hover:text-text"
            >
              About
            </Link>
            <Link
              href="/technology"
              className="text-text-muted transition-colors hover:text-text"
            >
              Technology
            </Link>
            <Link
              href="/app"
              className="text-text-muted transition-colors hover:text-text"
            >
              Simulator
            </Link>
            <Link
              href="/builder"
              className="text-text-muted transition-colors hover:text-text"
            >
              Scenario builder
            </Link>
          </nav>
        </div>

        <p className="mt-6 font-mono text-xs text-text-muted">
          SUMO · Azure OpenAI · Next.js + Deck.gl · Map data © OpenStreetMap
          (ODbL)
        </p>
      </div>
    </footer>
  );
}
