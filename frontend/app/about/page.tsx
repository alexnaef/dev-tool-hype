import Link from "next/link";

export default function AboutPage() {
  return (
    <main className="min-h-screen py-16 px-4">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          &larr; Back to rankings
        </Link>

        <h1 className="text-3xl font-bold text-foreground mt-6 mb-8">
          About Hype Barometer
        </h1>

        <div className="space-y-8 text-sm leading-relaxed text-muted-foreground">
          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              What is this?
            </h2>
            <p>
              Hype Barometer tracks the hottest emerging open-source projects.
              It surfaces repos that are gaining real traction right now &mdash;
              not the established giants, but the new tools people are actually
              excited about. Data refreshes daily.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Which repos are included?
            </h2>
            <p className="mb-2">
              Only projects created in the last 6 months are eligible. We discover
              repos from four sources:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <span className="text-foreground font-medium">GitHub Search</span> &mdash;
                top 100 recently-created repos sorted by stars, plus a second pass
                for repos under 3 months old.
              </li>
              <li>
                <span className="text-foreground font-medium">GitHub Trending</span> &mdash;
                weekly and monthly trending pages, which also provide a
                &quot;stars this period&quot; velocity signal.
              </li>
              <li>
                <span className="text-foreground font-medium">Hacker News</span> &mdash;
                we scan AI-related posts and comments for GitHub links, and
                search HN by project name and known aliases to catch discussions
                that don&apos;t link directly to the repo.
              </li>
              <li>
                <span className="text-foreground font-medium">Reddit</span> &mdash;
                we scan hot posts across r/LocalLLaMA, r/MachineLearning,
                r/selfhosted, r/ChatGPTCoding, and r/artificial for GitHub links.
              </li>
            </ul>
            <p className="mt-2">
              Any repo discovered on HN or Reddit that wasn&apos;t already in our
              pipeline is added automatically (cross-source discovery), then
              enriched and filtered like everything else.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              How is the score calculated?
            </h2>
            <p className="mb-2">
              Each repo gets a single 0&ndash;100 hotness score built from
              multiple signals. All values are log-scale normalized so that one
              extreme outlier doesn&apos;t crush everyone else.
            </p>
            <div className="rounded-lg border border-border p-4 bg-secondary/20">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-foreground">
                    <th className="pb-2 font-medium">Signal</th>
                    <th className="pb-2 font-medium text-right">Weight</th>
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  <tr><td className="py-1">GitHub stars (total)</td><td className="py-1 text-right">30%</td></tr>
                  <tr><td className="py-1">Commit activity (last 30 days)</td><td className="py-1 text-right">20%</td></tr>
                  <tr><td className="py-1">Hacker News points</td><td className="py-1 text-right">15%</td></tr>
                  <tr><td className="py-1">HN mention count</td><td className="py-1 text-right">10%</td></tr>
                  <tr><td className="py-1">Reddit points</td><td className="py-1 text-right">10%</td></tr>
                  <tr><td className="py-1">Trending stars/week</td><td className="py-1 text-right">10%</td></tr>
                  <tr><td className="py-1">Reddit mention count</td><td className="py-1 text-right">5%</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Penalties
            </h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <span className="text-foreground font-medium">Low star penalty</span> &mdash;
                repos with fewer than 1,000 stars have their score multiplied by
                <span className="font-mono text-xs"> stars / 1000</span>. A 500-star repo
                keeps 50% of its score; a 100-star repo keeps 10%.
              </li>
              <li>
                <span className="text-foreground font-medium">Corporate penalty</span> &mdash;
                repos from known corporate organizations (major tech companies with
                30+ public repos) receive a 30% score reduction. This surfaces
                indie and community-driven projects over well-funded corporate releases.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Why not include downloads?
            </h2>
            <p>
              Package install counts (PyPI, Homebrew, npm) are too unreliable as a
              scoring signal. Brew formula names often don&apos;t match repo names,
              npm isn&apos;t tracked, and many tools distribute binaries directly.
              Download data is still shown in the tooltip when available &mdash;
              it just doesn&apos;t affect the score.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Open source
            </h2>
            <p>
              The entire pipeline and frontend are open source. The scoring
              algorithm, data sources, and weights are all visible in the
              codebase &mdash; nothing is a black box.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
