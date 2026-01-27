"""
Fetch PyPI download statistics
"""
import requests
import time
from .config import REQUEST_DELAY

PYPISTATS_API = "https://pypistats.org/api"


def fetch_pypi_downloads(package: str) -> dict | None:
    """Fetch recent download stats for a package."""
    url = f"{PYPISTATS_API}/packages/{package}/recent"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "downloads_last_day": data["data"]["last_day"],
            "downloads_last_week": data["data"]["last_week"],
            "downloads_last_month": data["data"]["last_month"],
        }
    except requests.RequestException as e:
        print(f"Error fetching PyPI stats for {package}: {e}")
        return None


def fetch_pypi_for_repos(repos: dict[str, dict]) -> dict[str, dict]:
    """
    Try to fetch PyPI stats for repos that have a pypi field,
    or guess the package name from the repo name.
    Returns {full_name: pypi_stats}.
    """
    results = {}
    for full_name, info in repos.items():
        pypi_name = info.get("pypi")
        if not pypi_name:
            # Try the repo name as a guess
            repo_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
            pypi_name = repo_name.lower().replace(".", "-").replace("_", "-")

        stats = fetch_pypi_downloads(pypi_name)
        if stats:
            print(f"PyPI found: {pypi_name}")
            results[full_name] = stats
        time.sleep(REQUEST_DELAY)

    return results
