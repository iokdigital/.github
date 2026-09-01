#!/usr/bin/env python3
"""Fetch dependency manifests from all iokdigital repos via the Git Trees API.

Uses git/trees to discover file paths+SHAs, then git/blobs on the
correct repo to fetch content. Works with the default GITHUB_TOKEN
because the tree/blobs endpoints have different cross-repo permissions
than the Contents API.

Filters:
- Only files in well-known manifest paths (not __pycache__, not lockfile)
- Excludes any path containing /node_modules/ or /__pycache__/
"""

import sys
import json
import base64
import os
import urllib.request

GH_TOKEN = os.environ['GH_TOKEN']
REPOS = [
    ('iokdigital/alteryx2airflow', 'main'),
    ('iokdigital/alteryx2talend', 'develop'),
    ('iokdigital/flowport-webapp', 'develop'),
    ('iokdigital/flowport2jira', 'develop'),
    ('iokdigital/go-mermaid', 'main'),
    ('iokdigital/iok.digital', 'main'),
    ('iokdigital/talend2airflow', 'main'),
]

# Pairs of (must_contain_dir, file_name) for manifests we want
MANIFEST_PATTERNS = [
    ('', 'go.mod'),
    ('', 'go.sum'),
    ('', 'package.json'),
    ('', 'package-lock.json'),
    ('', 'requirements.txt'),
    ('', 'requirements-lock.txt'),
    ('', 'requirements-dev.txt'),
    ('', 'pyproject.toml'),
    ('worker/', 'go.mod'),
    ('worker/', 'go.sum'),
    ('worker/', 'requirements.txt'),
    ('worker/', 'requirements-lock.txt'),
    ('lambda/', 'package.json'),
    ('lambda/', 'package-lock.json'),
    ('frontend/', 'package.json'),
    ('frontend/', 'package-lock.json'),
    ('backend/', 'requirements.txt'),
    ('backend/', 'requirements-lock.txt'),
    ('backend/', 'pyproject.toml'),
    ('tests/', 'requirements.txt'),
]

EXCLUDE_PATH_PATTERNS = ['__pycache__', 'node_modules', '/dist/', '/build/']


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
    except Exception:
        return -1, None


def fetch_tree(repo, branch):
    status, ref_data = gh_get('https://api.github.com/repos/' + repo + '/git/refs/heads/' + branch)
    if status != 200 or ref_data is None:
        return None
    sha = ref_data['object']['sha']

    status, tree_data = gh_get(
        'https://api.github.com/repos/' + repo + '/git/trees/' + sha + '?recursive=1'
    )
    if status != 200 or tree_data is None:
        return None

    files = []
    for entry in tree_data.get('tree', []):
        if entry['type'] != 'blob':
            continue
        path = entry['path']
        if any(p in path for p in EXCLUDE_PATH_PATTERNS):
            continue
        basename = os.path.basename(path)
        for prefix, name in MANIFEST_PATTERNS:
            if basename == name and path.startswith(prefix):
                files.append((path, entry['sha']))
                break
    return files


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

    files = fetch_tree(repo, branch)
    if files is None:
        print('  SKIPPED: could not fetch tree')
        continue

    for path, sha in files:
        content_bytes, status = fetch_blob(repo, sha)
        if content_bytes is not None:
            dest = os.path.join(safe, os.path.basename(path))
            with open(dest, 'wb') as f:
                f.write(content_bytes)
            print('  OK (' + str(status) + '): ' + path + ' (' + str(len(content_bytes)) + ' bytes)')
        else:
            print('  FAIL (' + str(status) + '): ' + path)
