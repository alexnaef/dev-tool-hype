"""
Main orchestration script.
Flow: discover -> deduplicate -> enrich -> score -> write JSON
"""
import json
from datetime import datetime

from .config import DATA_DIR, SNAPSHOTS_DIR, FRONTEND_DATA_FILE, load_tools
from .fetch_github import discover_trending_repos, enrich_repos
from .fetch_pypi import fetch_pypi_for_repos
from .fetch_hn import fetch_all_hn_metrics
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

    # --- Step 1: Discover repos ---
    print("\nDiscovering trending GitHub repos...")
    discovered = discover_trending_repos(min_stars=100, max_results=60)
    print(f"Discovered {len(discovered)} trending repos")

    # --- Step 2: Merge seed tools from tools.yaml ---
    repos: dict[str, dict] = {}

    # Add discovered repos
    for r in discovered:
        repos[r["full_name"].lower()] = r

    # Add seed tools (always tracked)
    seed_tools = load_tools()
    for tool in seed_tools:
        gh = tool.get("github")
        if not gh:
            continue
        key = gh.lower()
        if key not in repos:
            repos[key] = {"full_name": gh, "name": tool["name"]}
        # Carry over seed metadata
        repos[key]["display_name"] = tool["name"]
        repos[key]["category"] = tool.get("category", "")
        if "pypi" in tool:
            repos[key]["pypi"] = tool["pypi"]

    print(f"\nTotal unique repos after merge: {len(repos)}")

    # --- Step 3: Enrich with full GitHub stats ---
    print("\nEnriching repos with GitHub stats...")
    repos = enrich_repos(repos)

    # --- Step 4: Fetch HN metrics ---
    print("\nFetching Hacker News mentions...")
    hn_data = fetch_all_hn_metrics(days=7)

    # Merge HN data into repos
    for full_name_lower, hn_info in hn_data.items():
        if full_name_lower in repos:
            repos[full_name_lower]["hn_mentions"] = hn_info["mention_count"]
            repos[full_name_lower]["hn_points"] = hn_info["total_points"]
            repos[full_name_lower]["hn_top_posts"] = hn_info.get("posts", [])[:3]

    # --- Step 5: Fetch PyPI downloads ---
    print("\nFetching PyPI downloads...")
    pypi_data = fetch_pypi_for_repos(repos)
    for full_name, pypi_info in pypi_data.items():
        repos[full_name].update(pypi_info)

    # --- Step 6: Score ---
    previous = load_previous_snapshot()
    previous_github = previous.get("raw", {}).get("github") if previous else None
    previous_rankings = previous.get("rankings") if previous else None

    print("\nCalculating scores...")
    tools_list = list(repos.values())
    rankings = calculate_scores(tools_list, previous_github_data=previous_github)
    movers = identify_movers(rankings, previous_rankings)

    # --- Step 7: Write output ---
    output = {
        "updated_at": datetime.utcnow().isoformat(),
        "rankings": rankings,
        "movers": movers,
        "raw": {
            "github": {k: {kk: vv for kk, vv in v.items() if kk != "hn_top_posts"} for k, v in repos.items()},
        },
    }

    # Snapshot
    snapshot_file = SNAPSHOTS_DIR / f"{datetime.utcnow().date()}.json"
    with open(snapshot_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved snapshot: {snapshot_file}")

    # Current
    current_file = DATA_DIR / "current.json"
    with open(current_file, "w") as f:
        json.dump(output, f, indent=2)

    # Frontend JSON
    with open(FRONTEND_DATA_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote frontend data: {FRONTEND_DATA_FILE}")

    print("\nDone!")
    print(f"Top 5: {[r['name'] for r in rankings[:5]]}")


if __name__ == "__main__":
    main()
