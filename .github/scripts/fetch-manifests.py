#!/usr/bin/env python3
"""Fetch dependency manifests from all iokdigital repos via the Git Trees API.

Uses git/trees to discover file paths+SHAs, then git/blobs on the
correct repo to fetch content. Works with the default GITHUB_TOKEN
because the tree/blobs endpoints have different cross-repo permissions
than the Contents API.

Note on private repos: a workflow's default GITHUB_TOKEN can read
public repos in the org cross-repo, but NOT private ones. For private
repo scanning, use a PAT secret (e.g. \`CROSS_REPO_READ_TOKEN\`) and
replace \$GH_TOKEN with its reference.
"""

import sys
import json
import base64
import os
import urllib.request

# Allow override via env var (for PAT use)
GH_TOKEN = os.environ.get('CROSS_REPO_READ_TOKEN') or os.environ.get('GH_TOKEN')
REPOS = [
    ('iokdigital/alteryx2airflow', 'main'),
    ('iokdigital/alteryx2talend', 'develop'),
    ('iokdigital/flowport-webapp', 'develop'),
    ('iokdigital/flowport2jira', 'develop'),
    ('iokdigital/go-mermaid', 'main'),
    ('iokdigital/iok.digital', 'main'),
    ('iokdigital/talend2airflow', 'main'),
]

MANIFEST_NAMES = {
    'go.mod', 'go.sum',
    'package.json', 'package-lock.json',
    'requirements.txt', 'requirements-lock.txt', 'requirements-dev.txt',
    'pyproject.toml',
}


def gh_get(url):
    req = urllib.request.Request(url, headers={
        'Authorization': 'token ' + GH_TOKEN,
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return -1, None


def fetch_tree(repo, branch):
    status, ref_data = gh_get('https://api.github.com/repos/' + repo + '/git/refs/heads/' + branch)
    if status != 200 or ref_data is None:
        return None, 'git/refs/heads: ' + str(status)
    sha = ref_data['object']['sha']

    status, tree_data = gh_get(
        'https://api.github.com/repos/' + repo + '/git/trees/' + sha + '?recursive=1'
    )
    if status != 200 or tree_data is None:
        return None, 'git/trees: ' + str(status)
    return tree_data.get('tree', []), None


def fetch_blob(repo, sha):
    status, data = gh_get('https://api.github.com/repos/' + repo + '/git/blobs/' + sha)
    if status != 200 or data is None:
        return None, status
    if data.get('encoding') == 'base64':
        return base64.b64decode(data['content']), 200
    return data.get('content', '').encode(), 200


for repo, branch in REPOS:
    safe = repo.replace('/', '-')
    os.makedirs(safe, exist_ok=True)
    print('\n=== ' + repo + ' @ ' + branch + ' ===')

    tree, err = fetch_tree(repo, branch)
    if tree is None:
        print('  SKIPPED: ' + str(err))
        continue

    # Filter to manifest files
    matches = []
    for entry in tree:
        if entry['type'] != 'blob':
            continue
        path = entry['path']
        if any(p in path for p in ['__pycache__', 'node_modules', '/dist/', '/build/']):
            continue
        basename = os.path.basename(path)
        if basename in MANIFEST_NAMES or path.startswith(('worker/', 'lambda/', 'frontend/', 'backend/', 'tests/')):
            matches.append((path, entry['sha']))

    for path, sha in matches:
        content_bytes, status = fetch_blob(repo, sha)
        if content_bytes is not None:
            dest = os.path.join(safe, os.path.basename(path))
            with open(dest, 'wb') as f:
                f.write(content_bytes)
            print('  OK (' + str(status) + '): ' + path + ' (' + str(len(content_bytes)) + ' bytes)')
        else:
            print('  FAIL (' + str(status) + '): ' + path)
