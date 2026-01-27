"""
Calculate hype and adoption scores for tools.

Hype Score = stars (25%) + stars_this_week (15%) + HN points (10%) + HN mentions (5%)
             + Reddit points (15%) + Reddit mentions (10%) + commits (20%)
Adoption Score = install downloads (60%) + commit activity (40%)

Repos with < 1000 stars get a harsh penalty multiplier.
Log-scale normalization avoids outlier crushing.
"""
import math
from datetime import datetime


def normalize_log(values: list[float]) -> list[float]:
    """Log-scale normalization to 0-100. Reduces outlier dominance."""
    if not values:
        return []
    logged = [math.log1p(v) for v in values]
    max_val = max(logged)
    if max_val == 0:
        return [0.0] * len(values)
    return [v / max_val * 100 for v in logged]


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
            "downloads_week": tool.get("downloads_last_week", 0) + tool.get("brew_installs_30d", 0),
            "downloads_month": tool.get("downloads_last_month", 0) + tool.get("brew_installs_90d", 0),
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

    # Log-scale normalization (reduces outlier dominance)
    norm_stars = normalize_log([r["stars"] for r in results])
    norm_stars_week = normalize_log([r["stars_this_week"] for r in results])
    norm_hn_pts = normalize_log([r["hn_points"] for r in results])
    norm_hn_cnt = normalize_log([r["hn_mentions"] for r in results])
    norm_reddit_pts = normalize_log([r["reddit_points"] for r in results])
    norm_reddit_cnt = normalize_log([r["reddit_mentions"] for r in results])
    norm_downloads = normalize_log([r["downloads_week"] for r in results])
    norm_commits = normalize_log([r["commits_30d"] for r in results])

    for i, r in enumerate(results):
        hype = (
            norm_stars[i] * 0.25
            + norm_stars_week[i] * 0.15
            + norm_hn_pts[i] * 0.10
            + norm_hn_cnt[i] * 0.05
            + norm_reddit_pts[i] * 0.15
            + norm_reddit_cnt[i] * 0.10
            + norm_commits[i] * 0.20
        )
        adoption = norm_downloads[i] * 0.6 + norm_commits[i] * 0.4

        # Heavy penalty for repos with < 1000 stars
        if r["stars"] < 1000:
            star_penalty = r["stars"] / 1000
            hype *= star_penalty
            adoption *= star_penalty

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
    return results[:50]


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
