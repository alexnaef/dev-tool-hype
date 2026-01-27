"""
Fetch GitHub metrics: discover trending repos + enrich with stats
"""
import re
import requests
import time
from datetime import datetime, timedelta
from .config import GITHUB_TOKEN, REQUEST_DELAY

GITHUB_API = "https://api.github.com"

GITHUB_URL_RE = re.compile(r"https?://github\.com/([\w.\-]+)/([\w.\-]+)")


def get_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _check_rate_limit(resp: requests.Response) -> None:
    """Sleep if we're close to hitting the rate limit."""
    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None and int(remaining) < 5:
        reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
        wait = max(reset_ts - int(datetime.utcnow().timestamp()), 1)
        print(f"Rate limit nearly exhausted, sleeping {wait}s")
        time.sleep(wait)


def fetch_repo_stats(owner: str, repo: str) -> dict | None:
    """Fetch stats for a single repo."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        _check_rate_limit(resp)
        resp.raise_for_status()
        data = resp.json()
        return {
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "watchers": data["subscribers_count"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "pushed_at": data["pushed_at"],
            "language": data["language"],
            "description": data["description"],
            "full_name": data["full_name"],
            "topics": data.get("topics", []),
        }
    except requests.RequestException as e:
        print(f"Error fetching {owner}/{repo}: {e}")
        return None


def fetch_commit_activity(owner: str, repo: str, days: int = 30) -> int:
    """Get commit count in last N days."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    try:
        resp = requests.get(
            url,
            headers=get_headers(),
            params={"since": since, "per_page": 100},
            timeout=10,
        )
        _check_rate_limit(resp)
        resp.raise_for_status()
        return len(resp.json())
    except requests.RequestException:
        return 0


def discover_trending_repos(min_stars: int = 100, max_results: int = 50) -> list[dict]:
    """
    Discover trending AI/ML repos via GitHub search API.
    Searches for repos with AI-related topics that were pushed recently.
    """
    since_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    queries = [
        f"topic:llm stars:>{min_stars} pushed:>{since_date}",
        f"topic:ai-tools stars:>{min_stars} pushed:>{since_date}",
        f"topic:generative-ai stars:>{min_stars} pushed:>{since_date}",
        f"topic:langchain OR topic:rag stars:>{min_stars} pushed:>{since_date}",
        f"topic:agent stars:>{min_stars} pushed:>{since_date} language:python",
    ]

    seen = set()
    results = []

    for q in queries:
        url = f"{GITHUB_API}/search/repositories"
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": 30}
        try:
            resp = requests.get(url, headers=get_headers(), params=params, timeout=15)
            _check_rate_limit(resp)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            for item in items:
                full_name = item["full_name"]
                if full_name in seen:
                    continue
                seen.add(full_name)
                results.append({
                    "full_name": full_name,
                    "name": item["name"],
                    "stars": item["stargazers_count"],
                    "forks": item["forks_count"],
                    "open_issues": item["open_issues_count"],
                    "description": item.get("description", ""),
                    "language": item.get("language"),
                    "pushed_at": item.get("pushed_at"),
                    "topics": item.get("topics", []),
                })
        except requests.RequestException as e:
            print(f"Error in GitHub search '{q[:40]}...': {e}")

        time.sleep(REQUEST_DELAY * 2)

    results.sort(key=lambda x: x["stars"], reverse=True)
    return results[:max_results]


def enrich_repos(repos: dict[str, dict]) -> dict[str, dict]:
    """
    For each repo keyed by full_name (owner/repo), fetch full stats
    and commit activity if not already present.
    """
    enriched = {}
    for full_name, existing in repos.items():
        owner, repo = full_name.split("/", 1)
        if "watchers" not in existing:
            print(f"Enriching {full_name}")
            stats = fetch_repo_stats(owner, repo)
            if stats:
                existing.update(stats)
            time.sleep(REQUEST_DELAY)

        if "commits_30d" not in existing:
            existing["commits_30d"] = fetch_commit_activity(owner, repo, 30)
            time.sleep(REQUEST_DELAY)

        enriched[full_name] = existing

    return enriched


def parse_github_url(url: str) -> str | None:
    """Extract owner/repo from a GitHub URL."""
    m = GITHUB_URL_RE.search(url or "")
    if m:
        owner, repo = m.group(1), m.group(2)
        # Strip trailing .git or similar
        repo = repo.removesuffix(".git")
        if owner.lower() not in ("topics", "explore", "settings", "notifications"):
            return f"{owner}/{repo}"
    return None
