"""
Main orchestration script.
Flow: discover -> trending -> seeds -> HN/Reddit (cross-source) -> enrich -> filter emerging -> corporate -> pypi -> score -> write
"""
import json
from datetime import datetime, timedelta

from .config import DATA_DIR, SNAPSHOTS_DIR, FRONTEND_DATA_FILE, load_tools
from .fetch_github import discover_trending_repos, enrich_repos, scrape_github_trending, is_corporate_org
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

    # --- Step 4: Fetch HN + cross-source discovery ---
    print("\nFetching Hacker News mentions...")
    repo_names_for_hn = list(repos.keys())
    hn_data = fetch_all_hn_metrics(days=7, repo_names=repo_names_for_hn)

    for full_name_lower, hn_info in hn_data.items():
        # Cross-source: add newly discovered repos
        if full_name_lower not in repos:
            parts = full_name_lower.split("/", 1)
            repos[full_name_lower] = {
                "full_name": full_name_lower,
                "name": parts[1] if len(parts) == 2 else full_name_lower,
            }
        repos[full_name_lower]["hn_mentions"] = hn_info["mention_count"]
        repos[full_name_lower]["hn_points"] = hn_info["total_points"]
        repos[full_name_lower]["hn_top_posts"] = hn_info.get("posts", [])[:3]

    # --- Step 5: Fetch Reddit + cross-source discovery ---
    print("\nFetching Reddit mentions...")
    reddit_data = fetch_all_reddit_metrics()

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

    # --- Step 8: Corporate check ---
    print("\nChecking for corporate repos...")
    for full_name, data in repos.items():
        owner = full_name.split("/")[0]
        data["corporate"] = is_corporate_org(owner)
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
    rankings = calculate_scores(tools_list, previous_github_data=previous_github)
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
