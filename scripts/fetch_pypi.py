"""
Fetch PyPI download statistics and Homebrew install counts.
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


def fetch_brew_installs(formula: str) -> dict | None:
    """Fetch Homebrew install counts for a formula."""
    url = f"https://formulae.brew.sh/api/formula/{formula}.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        analytics = data.get("analytics", {})
        install_30 = analytics.get("install", {}).get("30d", {})
        install_90 = analytics.get("install", {}).get("90d", {})
        # install data is {formula_name: count}
        count_30 = sum(install_30.values()) if isinstance(install_30, dict) else 0
        count_90 = sum(install_90.values()) if isinstance(install_90, dict) else 0
        if count_30 or count_90:
            return {"brew_installs_30d": count_30, "brew_installs_90d": count_90}
        return None
    except requests.RequestException:
        return None


def fetch_pypi_for_repos(repos: dict[str, dict]) -> dict[str, dict]:
    """
    Try to fetch PyPI stats and Homebrew installs for repos.
    Returns {full_name: combined_stats}.
    """
    results = {}
    for full_name, info in repos.items():
        repo_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
        combined = {}

        # PyPI
        pypi_name = info.get("pypi")
        if not pypi_name:
            pypi_name = repo_name.lower().replace(".", "-").replace("_", "-")
        stats = fetch_pypi_downloads(pypi_name)
        if stats:
            print(f"PyPI found: {pypi_name}")
            combined.update(stats)
        time.sleep(REQUEST_DELAY)

        # Homebrew
        brew_name = repo_name.lower()
        brew_stats = fetch_brew_installs(brew_name)
        if brew_stats:
            print(f"Brew found: {brew_name}")
            combined.update(brew_stats)
            time.sleep(REQUEST_DELAY)

        if combined:
            results[full_name] = combined

    return results
