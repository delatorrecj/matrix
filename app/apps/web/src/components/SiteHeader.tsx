"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/Logo";
import { HeaderControls } from "@/components/HeaderControls";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/about", label: "About" },
  { href: "/technology", label: "Technology" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3.5 sm:px-8">
        <Link href="/" className="shrink-0">
          <Logo />
        </Link>

        <nav
          aria-label="Marketing"
          className="hidden items-center gap-1 md:flex"
        >
          {NAV_LINKS.map(({ href, label }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-text-muted hover:text-text",
                )}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <HeaderControls />
          <Link
            href="/app"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-md shadow-primary/20 transition-all hover:bg-primary-hover active:scale-[0.98] sm:px-4"
          >
            <span className="hidden sm:inline">Launch simulator</span>
            <span className="sm:hidden">Launch</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>

      {/* Mobile nav */}
      <nav
        aria-label="Marketing mobile"
        className="flex gap-1 overflow-x-auto border-t border-border/40 px-5 py-2 md:hidden"
      >
        {NAV_LINKS.map(({ href, label }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-text-muted hover:text-text",
              )}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
