"""
Discover AI tools from Reddit discussions.
Extracts GitHub URLs from posts in relevant subreddits.
"""
import re
import requests
import time
from .config import REQUEST_DELAY
from .fetch_github import parse_github_url

SUBREDDITS = [
    "LocalLLaMA",
    "MachineLearning",
    "selfhosted",
    "ChatGPTCoding",
    "artificial",
]

HEADERS = {"User-Agent": "ai-tools-radar/1.0"}


def fetch_subreddit_posts(subreddit: str, limit: int = 100) -> list[dict]:
    """Fetch hot posts from a subreddit via public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]
    except requests.RequestException as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return []


def extract_github_repos_from_reddit(posts: list[dict]) -> dict:
    """
    Extract GitHub repo references from Reddit posts.
    Returns {full_name_lower: {mention_count, total_points}}.
    """
    repo_mentions: dict[str, dict] = {}

    for post in posts:
        urls_to_check = []
        post_url = post.get("url", "")
        selftext = post.get("selftext", "")
        score = post.get("score", 0) or 0

        if post_url:
            urls_to_check.append(post_url)

        # Extract GitHub URLs from selftext
        urls_to_check.extend(re.findall(r"https?://github\.com/[\w.\-]+/[\w.\-]+", selftext))

        repos_in_post = set()
        for url in urls_to_check:
            repo = parse_github_url(url)
            if repo:
                repos_in_post.add(repo.lower())

        for repo in repos_in_post:
            if repo not in repo_mentions:
                repo_mentions[repo] = {
                    "mention_count": 0,
                    "total_points": 0,
                }
            repo_mentions[repo]["mention_count"] += 1
            repo_mentions[repo]["total_points"] += score

    return repo_mentions


def fetch_all_reddit_metrics() -> dict:
    """Fetch Reddit data and extract GitHub repo mentions."""
    all_posts = []
    for sub in SUBREDDITS:
        print(f"Fetching r/{sub}...")
        posts = fetch_subreddit_posts(sub)
        all_posts.extend(posts)
        time.sleep(REQUEST_DELAY * 2)

    print(f"Found {len(all_posts)} Reddit posts across {len(SUBREDDITS)} subreddits")
    return extract_github_repos_from_reddit(all_posts)
