"""
Fetch GitHub metrics: discover trending repos + enrich with stats
"""
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .config import GITHUB_TOKEN, REQUEST_DELAY

# With a token we get 5000 req/hr — no need for 1s delays between calls.
# Without a token, 60 req/hr so we must be conservative.
_API_DELAY = 0.1 if GITHUB_TOKEN else REQUEST_DELAY
_MAX_WORKERS = 10 if GITHUB_TOKEN else 2

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


def discover_trending_repos(max_results: int = 100) -> list[dict]:
    """
    Discover emerging repos: recently created (< 6 months), sorted by stars.
    Two queries: one for < 6 months, one for < 3 months (surfaces very new repos).
    """
    cutoff_6m = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")
    cutoff_3m = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
    queries = [
        f"created:>{cutoff_6m}",
        f"created:>{cutoff_3m}",
    ]

    seen = set()
    results = []

    for q in queries:
        url = f"{GITHUB_API}/search/repositories"
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": 100}
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
                    "created_at": item.get("created_at"),
                    "pushed_at": item.get("pushed_at"),
                    "topics": item.get("topics", []),
                })
        except requests.RequestException as e:
            print(f"Error in GitHub search '{q[:40]}...': {e}")

        time.sleep(_API_DELAY)

    results.sort(key=lambda x: x["stars"], reverse=True)
    return results[:max_results]


def _enrich_single(full_name: str, existing: dict) -> tuple[str, dict]:
    """Enrich a single repo (for use in thread pool)."""
    owner, repo = full_name.split("/", 1)
    if "watchers" not in existing:
        stats = fetch_repo_stats(owner, repo)
        if stats:
            existing.update(stats)
        time.sleep(_API_DELAY)

    if "commits_30d" not in existing:
        existing["commits_30d"] = fetch_commit_activity(owner, repo, 30)
        time.sleep(_API_DELAY)

    return full_name, existing


def enrich_repos(repos: dict[str, dict]) -> dict[str, dict]:
    """
    For each repo keyed by full_name (owner/repo), fetch full stats
    and commit activity if not already present. Uses thread pool for concurrency.
    """
    needs_enrichment = {k: v for k, v in repos.items() if "watchers" not in v or "commits_30d" not in v}
    already_done = {k: v for k, v in repos.items() if k not in needs_enrichment}

    print(f"Enriching {len(needs_enrichment)} repos ({len(already_done)} already cached)...")
    enriched = dict(already_done)

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_enrich_single, k, v): k for k, v in needs_enrichment.items()}
        for i, future in enumerate(as_completed(futures), 1):
            full_name, data = future.result()
            enriched[full_name] = data
            if i % 20 == 0:
                print(f"  Enriched {i}/{len(needs_enrichment)}")

    return enriched


KNOWN_CORPORATES = {
    "microsoft", "google", "meta", "nvidia", "amazon", "aws", "apple",
    "facebook", "openai", "anthropic", "huggingface", "databricks",
    "salesforce", "ibm", "oracle", "adobe", "intel", "alibaba", "tencent",
    "baidu", "bytedance", "tesla", "uber", "airbnb", "netflix", "spotify",
    "stripe", "cloudflare", "vercel", "supabase",
}


def scrape_github_trending() -> list[dict]:
    """Scrape GitHub Trending page for weekly and monthly repos."""
    urls = [
        "https://github.com/trending?since=weekly&spoken_language_code=en",
        "https://github.com/trending?since=monthly&spoken_language_code=en",
    ]
    seen = set()
    results = []

    for url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for article in soup.select("article.Box-row"):
                # Repo name from the h2 > a link
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                full_name = h2.get("href", "").strip("/")
                if not full_name or full_name in seen:
                    continue
                seen.add(full_name)

                desc_p = article.select_one("p")
                description = desc_p.get_text(strip=True) if desc_p else ""

                # Stars count from the link containing a star SVG
                stars = 0
                star_links = article.select("a.Link--muted")
                for link in star_links:
                    svg = link.select_one("svg.octicon-star")
                    if svg:
                        text = link.get_text(strip=True).replace(",", "")
                        try:
                            stars = int(text)
                        except ValueError:
                            pass
                        break

                # Stars this period from the span
                stars_period = 0
                period_span = article.select_one("span.d-inline-block.float-sm-right")
                if period_span:
                    text = period_span.get_text(strip=True).replace(",", "")
                    m = re.match(r"([\d]+)", text)
                    if m:
                        stars_period = int(m.group(1))

                parts = full_name.split("/", 1)
                results.append({
                    "full_name": full_name,
                    "name": parts[1] if len(parts) == 2 else full_name,
                    "stars": stars,
                    "stars_period": stars_period,
                    "description": description,
                    "source": "trending_page",
                })

        except requests.RequestException as e:
            print(f"Error scraping GitHub trending: {e}")

        time.sleep(REQUEST_DELAY)

    return results


def is_corporate_org(owner: str) -> bool:
    """Check if a GitHub owner is a known corporate organization."""
    if owner.lower() in KNOWN_CORPORATES:
        return True
    url = f"{GITHUB_API}/orgs/{owner}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=10)
        _check_rate_limit(resp)
        if resp.status_code == 404:
            return False  # Not an org (personal account)
        resp.raise_for_status()
        data = resp.json()
        return data.get("public_repos", 0) > 30
    except requests.RequestException:
        return False


def check_corporate_bulk(repos: dict[str, dict]) -> None:
    """Check corporate status for all repos, deduplicating by owner, using thread pool."""
    owners = list({k.split("/")[0] for k in repos})
    print(f"Checking {len(owners)} unique owners for corporate status...")

    owner_results: dict[str, bool] = {}

    def _check(owner: str) -> tuple[str, bool]:
        time.sleep(_API_DELAY)
        return owner, is_corporate_org(owner)

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for owner, result in pool.map(lambda o: _check(o), owners):
            owner_results[owner] = result

    for full_name, data in repos.items():
        owner = full_name.split("/")[0]
        data["corporate"] = owner_results.get(owner, False)


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
