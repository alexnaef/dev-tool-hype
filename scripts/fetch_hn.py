"""
Discover AI tools from Hacker News discussions.
Extracts GitHub URLs from posts and comments rather than fuzzy matching.
"""
import re
import requests
from concurrent.futures import ThreadPoolExecutor
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


def fetch_ai_related_comments(days: int = 7) -> list[dict]:
    """Fetch HN comments related to AI/ML/LLM topics."""
    queries = [
        "LLM",
        "AI tool",
        "GPT",
        "Claude",
        "local model",
        "RAG",
        "AI agent",
        "coding assistant",
        "Ollama",
        "open source AI",
    ]
    all_comments = []
    seen_ids = set()

    for query in queries:
        print(f"Searching HN comments: '{query}'")
        timestamp = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        url = f"{HN_ALGOLIA_API}/search"
        params = {
            "query": query,
            "tags": "comment",
            "numericFilters": f"created_at_i>{timestamp}",
            "hitsPerPage": 200,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            for hit in hits:
                cid = hit.get("objectID")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    all_comments.append(hit)
        except requests.RequestException as e:
            print(f"Error searching HN comments for '{query}': {e}")

    return all_comments


def extract_github_repos_from_comments(comments: list[dict]) -> dict:
    """
    Extract GitHub repo references from HN comment text.
    Returns {full_name: {mention_count, total_points, total_comments, posts}}.
    """
    repo_mentions: dict[str, dict] = {}

    for comment in comments:
        comment_text = comment.get("comment_text", "")
        if not comment_text:
            continue

        # Find all GitHub URLs in comment text
        urls = re.findall(r"https?://github\.com/[\w.\-]+/[\w.\-]+", comment_text)
        points = comment.get("points", 0) or 0
        story_id = comment.get("story_id")

        repos_in_comment = set()
        for url in urls:
            repo = parse_github_url(url)
            if repo:
                repos_in_comment.add(repo.lower())

        for repo in repos_in_comment:
            if repo not in repo_mentions:
                repo_mentions[repo] = {
                    "mention_count": 0,
                    "total_points": 0,
                    "total_comments": 0,
                    "posts": [],
                }
            repo_mentions[repo]["mention_count"] += 1
            repo_mentions[repo]["total_points"] += points

    return repo_mentions


def merge_hn_data(stories: dict, comments: dict) -> dict:
    """Merge story and comment HN data."""
    merged = dict(stories)
    for repo, data in comments.items():
        if repo in merged:
            merged[repo]["mention_count"] += data["mention_count"]
            merged[repo]["total_points"] += data["total_points"]
        else:
            merged[repo] = data
    return merged


def _search_hn_for_alias(alias: str, days: int) -> tuple[str, list[dict]]:
    """Search HN for a single alias string. Returns (alias, matching_posts)."""
    posts = search_hn(alias, days=days, hits_per_page=50)
    alias_lower = alias.lower()
    matched = []
    for post in posts:
        title_lower = post.get("title", "").lower()
        url_lower = post.get("url", "").lower()
        if alias_lower in title_lower or alias_lower in url_lower:
            matched.append(post)
    return alias, matched


def search_hn_by_names(repos_with_aliases: list[tuple[str, list[str]]], days: int = 30) -> dict:
    """
    Search HN for repo names and aliases (display names, topic tags).
    repos_with_aliases: list of (full_name, [alias1, alias2, ...])
    Returns {full_name_lower: {mention_count, total_points, ...}}.
    """
    # Build alias -> full_name mapping, dedup aliases
    alias_to_repo: dict[str, str] = {}
    for full_name, aliases in repos_with_aliases:
        for alias in aliases:
            a = alias.lower()
            if len(a) >= 4 and a not in alias_to_repo:
                alias_to_repo[a] = full_name.lower()

    unique_aliases = list(alias_to_repo.keys())[:80]

    repo_mentions: dict[str, dict] = {}
    seen_ids: set[str] = set()

    print(f"  Searching HN for {len(unique_aliases)} aliases across {len(repos_with_aliases)} repos...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_search_hn_for_alias, a, days) for a in unique_aliases]
        all_results = [f.result() for f in futures]

    for alias, matched_posts in all_results:
        key = alias_to_repo[alias.lower()]
        for post in matched_posts:
            post_id = post.get("objectID", "")
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            points = post.get("points", 0) or 0
            comments = post.get("num_comments", 0) or 0
            title = post.get("title", "")

            if key not in repo_mentions:
                repo_mentions[key] = {
                    "mention_count": 0,
                    "total_points": 0,
                    "total_comments": 0,
                    "posts": [],
                }
            repo_mentions[key]["mention_count"] += 1
            repo_mentions[key]["total_points"] += points
            repo_mentions[key]["total_comments"] += comments
            repo_mentions[key]["posts"].append({
                "title": title,
                "url": f"https://news.ycombinator.com/item?id={post_id}",
                "points": points,
                "comments": comments,
            })

    for repo in repo_mentions:
        repo_mentions[repo]["posts"].sort(key=lambda x: x["points"], reverse=True)
        repo_mentions[repo]["posts"] = repo_mentions[repo]["posts"][:5]

    return repo_mentions


def fetch_all_hn_metrics(
    days: int = 7,
    repos_with_aliases: list[tuple[str, list[str]]] | None = None,
) -> dict:
    """Fetch HN data and extract GitHub repo mentions from stories, comments, and name search."""
    # Run story and comment fetches in parallel
    with ThreadPoolExecutor(max_workers=2) as pool:
        posts_future = pool.submit(fetch_ai_related_posts, days)
        comments_future = pool.submit(fetch_ai_related_comments, days)
        posts = posts_future.result()
        comments = comments_future.result()

    print(f"Found {len(posts)} AI-related HN posts, {len(comments)} comments")
    story_mentions = extract_github_repos_from_posts(posts)
    comment_mentions = extract_github_repos_from_comments(comments)

    merged = merge_hn_data(story_mentions, comment_mentions)

    # Also search by repo name + aliases (display name, topics)
    if repos_with_aliases:
        name_mentions = search_hn_by_names(repos_with_aliases, days=30)
        merged = merge_hn_data(merged, name_mentions)

    print(f"Total unique repos from HN: {len(merged)}")
    return merged
