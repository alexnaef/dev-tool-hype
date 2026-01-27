"""
Main orchestration script.
Flow: discover -> trending -> seeds -> HN/Reddit (cross-source) -> enrich -> filter emerging -> corporate -> pypi -> score -> write
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from .config import DATA_DIR, SNAPSHOTS_DIR, FRONTEND_DATA_FILE, load_tools
from .fetch_github import discover_trending_repos, enrich_repos, scrape_github_trending, check_corporate_bulk
from .fetch_pypi import fetch_pypi_for_repos
from .fetch_hn import fetch_all_hn_metrics
from .fetch_reddit import fetch_all_reddit_metrics
from .calculate_scores import calculate_scores, identify_movers


def load_previous_snapshot() -> dict | None:
    """Load the most recent previous snapshot."""
    snapshots = sorted(SNAPSHOTS_DIR.glob("*.json"), reverse=True)
    if len(snapshots) > 1:
        with open(snapshots[1]) as f:
            return json.load(f)
    return None


def main():
    print("=" * 50)
    print(f"AI Tools Radar - {datetime.utcnow().date()}")
    print("=" * 50)

    # --- Step 1: Discover emerging repos (created < 6 months, sorted by stars) ---
    print("\nDiscovering emerging GitHub repos...")
    discovered = discover_trending_repos(max_results=100)
    print(f"Discovered {len(discovered)} emerging repos")

    # --- Step 2: Scrape GitHub Trending page ---
    print("\nScraping GitHub Trending page...")
    trending_page = scrape_github_trending()
    print(f"Found {len(trending_page)} repos from Trending page")

    # --- Step 3: Build repos dict ---
    repos: dict[str, dict] = {}

    # Add discovered repos
    for r in discovered:
        repos[r["full_name"].lower()] = r

    # Merge trending page repos — carry stars_period through
    for r in trending_page:
        key = r["full_name"].lower()
        if key not in repos:
            repos[key] = r
        else:
            # Carry stars_period into existing entry
            if r.get("stars_period"):
                repos[key]["stars_period"] = r["stars_period"]

    # Add seed tools (always tracked)
    seed_tools = load_tools()
    for tool in seed_tools:
        gh = tool.get("github")
        if not gh:
            continue
        key = gh.lower()
        if key not in repos:
            repos[key] = {"full_name": gh, "name": tool["name"]}
        repos[key]["display_name"] = tool["name"]
        repos[key]["category"] = tool.get("category", "")
        if "pypi" in tool:
            repos[key]["pypi"] = tool["pypi"]

    print(f"\nTotal unique repos after initial merge: {len(repos)}")

    # --- Step 4 & 5: Fetch HN + Reddit in parallel ---
    print("\nFetching Hacker News + Reddit mentions in parallel...")

    # Build aliases for HN search: repo name, display name, topic tags
    repos_with_aliases = []
    for key, data in repos.items():
        aliases = set()
        # Repo short name (e.g. "moltbot")
        repo_name = key.split("/")[-1]
        aliases.add(repo_name)
        # Display name if different (e.g. "clawdbot")
        display = data.get("display_name", "")
        if display:
            aliases.add(display)
        name = data.get("name", "")
        if name and name.lower() != repo_name:
            aliases.add(name)
        # Topic tags that look like product names (not generic like "ai" or "python")
        for topic in data.get("topics", []):
            if len(topic) >= 4 and topic not in ("python", "javascript", "typescript", "rust",
                "golang", "machine-learning", "deep-learning", "artificial-intelligence",
                "open-source", "linux", "macos", "windows", "docker", "kubernetes"):
                aliases.add(topic)
        repos_with_aliases.append((key, list(aliases)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        hn_future = pool.submit(fetch_all_hn_metrics, days=7, repos_with_aliases=repos_with_aliases)
        reddit_future = pool.submit(fetch_all_reddit_metrics)
        hn_data = hn_future.result()
        reddit_data = reddit_future.result()

    for full_name_lower, hn_info in hn_data.items():
        if full_name_lower not in repos:
            parts = full_name_lower.split("/", 1)
            repos[full_name_lower] = {
                "full_name": full_name_lower,
                "name": parts[1] if len(parts) == 2 else full_name_lower,
            }
        repos[full_name_lower]["hn_mentions"] = hn_info["mention_count"]
        repos[full_name_lower]["hn_points"] = hn_info["total_points"]
        repos[full_name_lower]["hn_top_posts"] = hn_info.get("posts", [])[:3]

    for full_name_lower, reddit_info in reddit_data.items():
        if full_name_lower not in repos:
            parts = full_name_lower.split("/", 1)
            repos[full_name_lower] = {
                "full_name": full_name_lower,
                "name": parts[1] if len(parts) == 2 else full_name_lower,
            }
        repos[full_name_lower]["reddit_mentions"] = reddit_info["mention_count"]
        repos[full_name_lower]["reddit_points"] = reddit_info["total_points"]

    print(f"Total repos after cross-source discovery: {len(repos)}")

    # --- Step 6: Enrich all repos with GitHub stats ---
    print("\nEnriching repos with GitHub stats...")
    repos = enrich_repos(repos)

    # --- Step 6b: Deduplicate by enriched full_name (handles redirects/renames) ---
    deduped = {}
    for key, data in repos.items():
        canonical = data.get("full_name", key).lower()
        if canonical in deduped:
            # Merge: keep whichever has more data, combine HN/Reddit mentions
            existing = deduped[canonical]
            existing["hn_mentions"] = existing.get("hn_mentions", 0) + data.get("hn_mentions", 0)
            existing["hn_points"] = existing.get("hn_points", 0) + data.get("hn_points", 0)
            existing["reddit_mentions"] = existing.get("reddit_mentions", 0) + data.get("reddit_mentions", 0)
            existing["reddit_points"] = existing.get("reddit_points", 0) + data.get("reddit_points", 0)
            hn_posts = existing.get("hn_top_posts", []) + data.get("hn_top_posts", [])
            hn_posts.sort(key=lambda x: x.get("points", 0), reverse=True)
            existing["hn_top_posts"] = hn_posts[:5]
            if data.get("display_name") and not existing.get("display_name"):
                existing["display_name"] = data["display_name"]
        else:
            deduped[canonical] = data
    if len(deduped) < len(repos):
        print(f"Deduplicated repos: {len(repos)} -> {len(deduped)}")
    repos = deduped

    # --- Step 7: Filter to emerging only (created < 6 months) ---
    cutoff = datetime.utcnow() - timedelta(days=180)
    before = len(repos)
    filtered_repos = {}
    for key, data in repos.items():
        created = data.get("created_at")
        if not created:
            continue  # drop repos without created_at (failed enrichment)
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        if created_dt >= cutoff:
            filtered_repos[key] = data
    repos = filtered_repos
    print(f"Filtered to emerging repos: {before} -> {len(repos)}")

    # --- Step 8: Corporate check (bulk, deduplicated by owner) ---
    print("\nChecking for corporate repos...")
    check_corporate_bulk(repos)
    corporate_count = sum(1 for r in repos.values() if r.get("corporate"))
    print(f"Flagged {corporate_count} corporate repos")

    # --- Step 9: Fetch PyPI downloads ---
    print("\nFetching PyPI downloads...")
    pypi_data = fetch_pypi_for_repos(repos)
    for full_name, pypi_info in pypi_data.items():
        repos[full_name].update(pypi_info)

    # --- Step 10: Score ---
    previous = load_previous_snapshot()
    previous_github = previous.get("raw", {}).get("github") if previous else None
    previous_rankings = previous.get("rankings") if previous else None

    print("\nCalculating scores...")
    tools_list = list(repos.values())
    all_rankings = calculate_scores(tools_list, previous_github_data=previous_github)
    rankings = all_rankings[:50]
    print(f"Top 50 selected from {len(all_rankings)} scored repos")
    movers = identify_movers(rankings, previous_rankings)

    # --- Step 11: Write output ---
    output = {
        "updated_at": datetime.utcnow().isoformat(),
        "rankings": rankings,
        "movers": movers,
        "raw": {
            "github": {k: {kk: vv for kk, vv in v.items() if kk != "hn_top_posts"} for k, v in repos.items()},
        },
    }

    snapshot_file = SNAPSHOTS_DIR / f"{datetime.utcnow().date()}.json"
    with open(snapshot_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved snapshot: {snapshot_file}")

    current_file = DATA_DIR / "current.json"
    with open(current_file, "w") as f:
        json.dump(output, f, indent=2)

    with open(FRONTEND_DATA_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote frontend data: {FRONTEND_DATA_FILE}")

    print("\nDone!")
    print(f"Top 5: {[r['name'] for r in rankings[:5]]}")


if __name__ == "__main__":
    main()
