"""GitHub issue -> Jira (PORT) one-way sync fallback.

Used by the central reusable workflow
(`iokdigital/.github/.github/workflows/github-jira-sync.yml`); consumer repos
call that workflow and never touch this file. Trigger: issues.opened /
issues.labeled (all issues, human + machine-filed), or manual
workflow_dispatch with an issue number for backfill.

Auth: Basic auth with ATLASSIAN_USER email + ATLASSIAN_JIRA_TOKEN API token
(both loaded into env by the infisical-secrets step).
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

GH_API = "https://api.github.com"

# Env is read inside main()/helpers via _env() so the module stays import-safe.
_ENV = {}


def _env(name, default=None):
    if name not in _ENV:
        val = os.environ.get(name, default)
        if val is None:
            raise KeyError(name)
        _ENV[name] = val
    return _ENV[name]


def gh_api(path, method="GET", payload=None):
    token = _env("GH_TOKEN")
    req = urllib.request.Request(
        GH_API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def jira_api(path, payload):
    base = _env("JIRA_BASE_URL").rstrip("/")
    user = _env("JIRA_USER")
    token = _env("JIRA_TOKEN")
    cred = base64.b64encode(f"{user}:{token}".encode()).decode()
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:2000]}


def adf_paragraph(text):
    """Plain-text paragraph node; newlines become hard breaks."""
    content = []
    for i, line in enumerate(text.split("\n")):
        if i:
            content.append({"type": "hardBreak"})
        if line:
            content.append({"type": "text", "text": line})
    return {"type": "paragraph", "content": content or [{"type": "text", "text": " "}]}


def main():
    base = _env("JIRA_BASE_URL").rstrip("/")
    project = os.environ.get("JIRA_PROJECT_KEY", "PORT")
    repo = _env("REPO_FULL")  # owner/repo
    number = _env("ISSUE_NUMBER")
    issue = gh_api(f"/repos/{repo}/issues/{number}")
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    jira_labels = ["github-sync"] + (["ci-filed"] if "ci-filed" in labels else [])

    comments = gh_api(f"/repos/{repo}/issues/{number}/comments")
    for c in comments:
        if "Created Jira" in c.get("body", "") and project + "-" in c.get("body", ""):
            print("Already synced (marker comment found); skipping.")
            return 0

    title = issue.get("title", f"GitHub issue #{number}")
    body = issue.get("body") or "(no description)"
    html_url = issue.get("html_url", "")
    header = (
        f"Source: {repo}#{number}\n"
        f"URL: {html_url}\n"
        f"Author: {(issue.get('user') or {}).get('login', 'unknown')}"
    )

    summary = f"[{repo}] {title}"[:255]
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": "Task"},
            "labels": jira_labels,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [adf_paragraph(header), adf_paragraph(body)],
            },
        }
    }
    status, data = jira_api("/rest/api/3/issue", payload)
    if status not in (200, 201):
        print(f"Jira create failed ({status}): {json.dumps(data)[:2000]}", file=sys.stderr)
        return 1

    key = data["key"]
    browse_url = f"{base}/browse/{key}"
    gh_api(
        f"/repos/{repo}/issues/{number}/comments",
        method="POST",
        payload={"body": f"Created Jira [{key}]({browse_url}) via github-jira-sync."},
    )
    print(f"Synced {repo}#{number} -> {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
