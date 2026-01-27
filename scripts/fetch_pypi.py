"""
Fetch PyPI download statistics and Homebrew install counts.
"""
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _fetch_single_repo_installs(full_name: str, info: dict) -> tuple[str, dict]:
    """Fetch PyPI + Brew for one repo (for thread pool)."""
    repo_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
    combined = {}

    pypi_name = info.get("pypi")
    if not pypi_name:
        pypi_name = repo_name.lower().replace(".", "-").replace("_", "-")
    stats = fetch_pypi_downloads(pypi_name)
    if stats:
        combined.update(stats)

    brew_name = repo_name.lower()
    brew_stats = fetch_brew_installs(brew_name)
    if brew_stats:
        combined.update(brew_stats)

    return full_name, combined


def fetch_pypi_for_repos(repos: dict[str, dict]) -> dict[str, dict]:
    """
    Try to fetch PyPI stats and Homebrew installs for repos concurrently.
    Returns {full_name: combined_stats}.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_single_repo_installs, k, v): k for k, v in repos.items()}
        for i, future in enumerate(as_completed(futures), 1):
            full_name, combined = future.result()
            if combined:
                pypi_found = "downloads_last_week" in combined
                brew_found = "brew_installs_30d" in combined
                if pypi_found or brew_found:
                    parts = []
                    if pypi_found:
                        parts.append("PyPI")
                    if brew_found:
                        parts.append("Brew")
                    print(f"  {'+'.join(parts)} found: {full_name.split('/')[-1]}")
                results[full_name] = combined
            if i % 20 == 0:
                print(f"  Checked installs {i}/{len(repos)}")

    return results
