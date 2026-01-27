"use client";

import { useState } from "react";

export function AboutPopover() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-8 h-8 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors text-sm font-medium"
        aria-label="About this page"
      >
        ?
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-10 z-50 w-80 rounded-lg border border-border bg-background shadow-lg p-4 text-sm space-y-3">
            <h3 className="font-semibold text-foreground">How it works</h3>

            <div className="space-y-2 text-muted-foreground leading-relaxed">
              <p>
                <span className="text-foreground font-medium">Which repos?</span>{" "}
                We track emerging open-source projects created in the last 6 months,
                discovered from GitHub&apos;s top repos by stars, the GitHub Trending
                page, Hacker News discussions, and Reddit posts.
              </p>

              <p>
                <span className="text-foreground font-medium">Scoring (0-100):</span>{" "}
                A single hotness score from multiple signals, using log-scale
                normalization so no single outlier dominates.
              </p>

              <ul className="list-none space-y-1 pl-1">
                <li><span className="font-mono text-xs text-foreground">30%</span> GitHub stars</li>
                <li><span className="font-mono text-xs text-foreground">20%</span> Commit activity (30d)</li>
                <li><span className="font-mono text-xs text-foreground">15%</span> Hacker News points</li>
                <li><span className="font-mono text-xs text-foreground">10%</span> HN mention count</li>
                <li><span className="font-mono text-xs text-foreground">10%</span> Reddit points</li>
                <li><span className="font-mono text-xs text-foreground">10%</span> Trending stars/week</li>
                <li><span className="font-mono text-xs text-foreground">&nbsp;5%</span> Reddit mention count</li>
              </ul>

              <p>
                <span className="text-foreground font-medium">Penalties:</span>{" "}
                Repos under 1,000 stars are penalized proportionally.
                Corporate-backed repos get a 30% reduction.
              </p>

              <p>
                Top 50 repos by final score are shown. Data refreshes daily.
              </p>

              <a
                href="/about"
                className="inline-block text-foreground font-medium hover:underline"
              >
                Learn more &rarr;
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
