"""
Calculate hype and adoption scores for tools.

Hype Score = stars_this_week (35%) + HN points (15%) + HN mentions (10%) + Reddit points (25%) + Reddit mentions (15%)
Adoption Score = PyPI downloads (60%) + commit activity (40%)
"""
from datetime import datetime


def normalize_values(values: list[float]) -> list[float]:
    """Min-max normalization to 0-100 scale."""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [50.0] * len(values)
    return [(v - min_val) / (max_val - min_val) * 100 for v in values]


def calculate_scores(
    tools: list[dict],
    previous_github_data: dict | None = None,
) -> list[dict]:
    """
    Calculate hype and adoption scores for discovered tools.
    Each tool dict should already have github/pypi/hn/reddit fields merged in.
    """
    results = []
    prev = previous_github_data or {}
    now = datetime.utcnow()

    for tool in tools:
        full_name = tool.get("full_name", "")
        stars_current = tool.get("stars", 0)

        # Compute star velocity (stars per day based on repo age)
        created = tool.get("created_at")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                age_days = max((now - created_dt).days, 1)
            except (ValueError, TypeError):
                age_days = 365
        else:
            age_days = 365
        stars_per_day = round(stars_current / age_days, 2)

        # Keep stars_delta_7d for backward compat in output
        prev_stars = prev.get(full_name, {}).get("stars", stars_current)
        stars_delta = stars_current - prev_stars

        result = {
            "name": tool.get("display_name", tool.get("name", full_name.split("/")[-1])),
            "full_name": full_name,
            "category": tool.get("category", ""),
            "description": tool.get("description", ""),
            "github_url": f"https://github.com/{full_name}",
            "stars": stars_current,
            "stars_delta_7d": stars_delta,
            "stars_per_day": stars_per_day,
            "forks": tool.get("forks", 0),
            "commits_30d": tool.get("commits_30d", 0),
            "open_issues": tool.get("open_issues", 0),
            "language": tool.get("language", ""),
            "downloads_week": tool.get("downloads_last_week", 0),
            "downloads_month": tool.get("downloads_last_month", 0),
            "hn_mentions": tool.get("hn_mentions", 0),
            "hn_points": tool.get("hn_points", 0),
            "hn_top_posts": tool.get("hn_top_posts", []),
            "reddit_mentions": tool.get("reddit_mentions", 0),
            "reddit_points": tool.get("reddit_points", 0),
            "stars_this_week": tool.get("stars_period", 0),
            "corporate": tool.get("corporate", False),
        }
        results.append(result)

    if not results:
        return results

    # Normalize components
    stars_week_list = [r["stars_this_week"] for r in results]
    hn_points_list = [r["hn_points"] for r in results]
    hn_mentions_list = [r["hn_mentions"] for r in results]
    reddit_points_list = [r["reddit_points"] for r in results]
    reddit_mentions_list = [r["reddit_mentions"] for r in results]
    downloads_list = [r["downloads_week"] for r in results]
    commits_list = [r["commits_30d"] for r in results]

    norm_stars_week = normalize_values(stars_week_list)
    norm_hn_pts = normalize_values(hn_points_list)
    norm_hn_cnt = normalize_values(hn_mentions_list)
    norm_reddit_pts = normalize_values(reddit_points_list)
    norm_reddit_cnt = normalize_values(reddit_mentions_list)
    norm_downloads = normalize_values(downloads_list)
    norm_commits = normalize_values(commits_list)

    for i, r in enumerate(results):
        hype = (
            norm_stars_week[i] * 0.35
            + norm_hn_pts[i] * 0.15
            + norm_hn_cnt[i] * 0.10
            + norm_reddit_pts[i] * 0.25
            + norm_reddit_cnt[i] * 0.15
        )
        adoption = norm_downloads[i] * 0.6 + norm_commits[i] * 0.4

        # Corporate penalty
        if r["corporate"]:
            hype *= 0.7

        r["hype_score"] = round(hype, 1)
        r["adoption_score"] = round(adoption, 1)
        r["combined_score"] = round((hype + adoption) / 2, 1)

        if r["stars_this_week"] > 100:
            r["trend"] = "rising"
        elif r["stars_delta_7d"] < -10:
            r["trend"] = "falling"
        else:
            r["trend"] = "stable"

    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results


def identify_movers(current: list[dict], previous: list[dict] | None) -> dict:
    """Identify biggest movers up and down."""
    if not previous:
        return {"rising": [], "falling": []}

    prev_scores = {r["full_name"]: r.get("combined_score", 0) for r in previous}
    changes = []
    for r in current:
        prev = prev_scores.get(r["full_name"], r["combined_score"])
        change = r["combined_score"] - prev
        changes.append({
            "name": r["name"],
            "change": round(change, 1),
            "current_score": r["combined_score"],
        })

    changes.sort(key=lambda x: x["change"], reverse=True)
    return {
        "rising": [c for c in changes[:5] if c["change"] > 0],
        "falling": [c for c in changes[-5:] if c["change"] < 0][::-1],
    }
