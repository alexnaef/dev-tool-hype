import { HypeBarometer } from "@/components/hype-barometer";
import { AboutPopover } from "@/components/about-popover";
import { promises as fs } from "fs";
import path from "path";

interface ToolData {
  name: string;
  github_url: string;
  combined_score: number;
  stars: number;
  hn_mentions: number;
  downloads_month: number;
  pushed_at: string;
  description?: string;
}

interface DataFile {
  updated_at: string;
  rankings: ToolData[];
}

async function getData(): Promise<DataFile> {
  try {
    const filePath = path.join(process.cwd(), "public", "data.json");
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return { updated_at: "", rankings: [] };
  }
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export default async function Home() {
  const data = await getData();
  const tools = data.rankings.map((t) => ({
    name: t.name,
    score: Math.round(t.combined_score),
    url: t.github_url,
    stats: {
      githubStars: formatNumber(t.stars),
      hnMentions: t.hn_mentions,
      pypiDownloads: t.downloads_month > 0 ? `${formatNumber(t.downloads_month)}/mo` : "N/A",
      lastUpdated: t.pushed_at ? new Date(t.pushed_at).toLocaleDateString() : "N/A",
    },
  }));

  return (
    <main className="min-h-screen py-16 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-10 flex items-start gap-4">
          <AboutPopover />
          <h1 className="text-4xl font-bold text-foreground text-center flex-1">
            Hype Barometer
          </h1>
          <div className="w-8" /> {/* balance the about button */}
        </div>

        {tools.length === 0 ? (
          <p className="text-center text-muted-foreground">
            No data yet. Run the data pipeline to populate.
          </p>
        ) : (
          <div className="space-y-0">
            {tools.map((tool) => (
              <HypeBarometer
                key={tool.name}
                name={tool.name}
                score={tool.score}
                url={tool.url}
                stats={tool.stats}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
