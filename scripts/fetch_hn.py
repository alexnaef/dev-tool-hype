"""
Discover AI tools from Hacker News discussions.
Extracts GitHub URLs directly from posts rather than fuzzy matching.
"""
import re
import requests
from datetime import datetime, timedelta
from .config import REQUEST_DELAY
from .fetch_github import parse_github_url

HN_ALGOLIA_API = "https://hn.algolia.com/api/v1"


def search_hn(query: str, days: int = 7, hits_per_page: int = 200) -> list[dict]:
    """Search HN for posts matching query."""
    timestamp = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    url = f"{HN_ALGOLIA_API}/search"
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{timestamp}",
        "hitsPerPage": hits_per_page,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except requests.RequestException as e:
        print(f"Error searching HN for '{query}': {e}")
        return []


def fetch_ai_related_posts(days: int = 7) -> list[dict]:
    """Fetch HN posts related to AI/ML/LLM topics."""
    queries = [
        "LLM",
        "AI tool",
        "GPT",
        "Claude",
        "local model",
        "RAG",
        "vector database",
        "AI agent",
        "coding assistant",
        "Ollama",
        "LangChain",
        "open source AI",
        "machine learning",
    ]
    all_posts = []
    seen_ids = set()

    for query in queries:
        print(f"Searching HN: '{query}'")
        posts = search_hn(query, days=days)
        for post in posts:
            post_id = post.get("objectID")
            if post_id and post_id not in seen_ids:
                seen_ids.add(post_id)
                all_posts.append(post)

    return all_posts


def extract_github_repos_from_posts(posts: list[dict]) -> dict:
    """
    Extract GitHub repo references from HN posts.
    Returns {full_name: {mention_count, total_points, total_comments, posts}}.
    """
    repo_mentions: dict[str, dict] = {}

    for post in posts:
        title = post.get("title", "")
        post_url = post.get("url", "")
        story_url = post.get("story_url", "")
        points = post.get("points", 0) or 0
        comments = post.get("num_comments", 0) or 0
        post_id = post.get("objectID")

        # Try to extract a GitHub repo from the post URL or story URL
        repo = parse_github_url(post_url) or parse_github_url(story_url)
        if not repo:
            continue

        repo = repo.lower()
        if repo not in repo_mentions:
            repo_mentions[repo] = {
                "mention_count": 0,
                "total_points": 0,
                "total_comments": 0,
                "posts": [],
            }

        repo_mentions[repo]["mention_count"] += 1
        repo_mentions[repo]["total_points"] += points
        repo_mentions[repo]["total_comments"] += comments
        repo_mentions[repo]["posts"].append({
            "title": title,
            "url": f"https://news.ycombinator.com/item?id={post_id}",
            "points": points,
            "comments": comments,
        })

    # Sort posts by points and keep top 5
    for repo in repo_mentions:
        repo_mentions[repo]["posts"].sort(key=lambda x: x["points"], reverse=True)
        repo_mentions[repo]["posts"] = repo_mentions[repo]["posts"][:5]

    return repo_mentions


def fetch_all_hn_metrics(days: int = 7) -> dict:
    """Fetch HN data and extract GitHub repo mentions."""
    posts = fetch_ai_related_posts(days=days)
    print(f"Found {len(posts)} AI-related HN posts")
    return extract_github_repos_from_posts(posts)
