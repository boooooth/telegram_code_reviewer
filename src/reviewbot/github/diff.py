import base64
import re

import httpx

from reviewbot.config import settings

PR_URL_RE = re.compile(
    r"github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/pull/(?P<number>\d+)"
)


def _auth_headers() -> dict[str, str]:
    headers = {}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def parse_pr_url(text: str) -> tuple[str, str, int] | None:
    match = PR_URL_RE.search(text)
    if not match:
        return None
    return match["owner"], match["repo"], int(match["number"])


def fetch_pr_diff(owner: str, repo: str, number: int) -> str:
    headers = {"Accept": "application/vnd.github.v3.diff", **_auth_headers()}
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    response = httpx.get(url, headers=headers, timeout=30.0)
    response.raise_for_status()
    return response.text


def fetch_pr_files(owner: str, repo: str, number: int) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
    response = httpx.get(url, headers=_auth_headers(), timeout=30.0)
    response.raise_for_status()
    return response.json()


def fetch_file_content(contents_url: str) -> str | None:
    response = httpx.get(contents_url, headers=_auth_headers(), timeout=30.0)
    response.raise_for_status()
    data = response.json()
    if data.get("encoding") != "base64" or "content" not in data:
        return None
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def fetch_pr_context(owner: str, repo: str, number: int) -> tuple[str, dict[str, str]]:
    """Fetch the PR diff, plus full content for as many changed files as fit
    within the configured caps (max file count, max size per file, max
    combined size). Files beyond the caps are simply absent from the returned
    dict; the diff still covers every changed file regardless."""
    diff = fetch_pr_diff(owner, repo, number)

    if len(diff.encode("utf-8")) > settings.max_pr_diff_bytes:
        return diff, {}

    files = fetch_pr_files(owner, repo, number)

    full_files: dict[str, str] = {}
    total_bytes = 0
    for file in files:
        if len(full_files) >= settings.max_pr_files:
            break
        if file.get("status") == "removed":
            continue
        contents_url = file.get("contents_url")
        if not contents_url:
            continue

        content = fetch_file_content(contents_url)
        if content is None:
            continue

        size = len(content.encode("utf-8"))
        if size > settings.max_pr_file_bytes:
            continue
        if total_bytes + size > settings.max_pr_total_context_bytes:
            break

        full_files[file["filename"]] = content
        total_bytes += size

    return diff, full_files
