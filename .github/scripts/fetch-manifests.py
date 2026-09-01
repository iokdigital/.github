#!/usr/bin/env python3
"""Fetch dependency manifests from all iokdigital repos via the GitHub Contents API.

Decodes the base64-encoded 'content' field of the API response and writes
each file to /tmp/manifests/<repo-flattened>/<basename>.
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

PATHS_BY_REPO = {
    'iokdigital/alteryx2airflow':  ['go.mod', 'go.sum', 'worker/go.mod', 'worker/go.sum', 'worker/requirements.txt'],
    'iokdigital/alteryx2talend':   ['go.mod', 'go.sum', 'worker/go.mod', 'worker/go.sum', 'worker/requirements.txt'],
    'iokdigital/flowport-webapp':  ['frontend/package.json', 'frontend/package-lock.json', 'backend/pyproject.toml', 'backend/requirements.txt', 'backend/requirements-lock.txt'],
    'iokdigital/flowport2jira':    ['requirements.txt', 'requirements-lock.txt', 'requirements-dev.txt'],
    'iokdigital/go-mermaid':       ['go.mod', 'go.sum'],
    'iokdigital/iok.digital':      ['package.json', 'package-lock.json', 'lambda/package.json', 'lambda/package-lock.json'],
    'iokdigital/talend2airflow':   ['go.mod', 'go.sum', 'worker/go.mod', 'worker/go.sum', 'worker/requirements.txt'],
}


def fetch(repo, branch, path):
    """Fetch a single file from the Contents API. Returns (bytes, status)."""
    url = 'https://api.github.com/repos/' + repo + '/contents/' + path + '?ref=' + branch
    req = urllib.request.Request(url, headers={
        'Authorization': 'token ' + GH_TOKEN,
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                return None, r.status
            data = json.loads(r.read())
            if data.get('encoding') == 'base64':
                return base64.b64decode(data['content']), 200
            return data.get('content', '').encode(), 200
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, -1


for repo, branch in REPOS:
    safe = repo.replace('/', '-')
    os.makedirs(safe, exist_ok=True)
    print('\n=== ' + repo + ' @ ' + branch + ' ===')
    for path in PATHS_BY_REPO.get(repo, []):
        content_bytes, status = fetch(repo, branch, path)
        if content_bytes is not None:
            dest = os.path.join(safe, os.path.basename(path))
            with open(dest, 'wb') as f:
                f.write(content_bytes)
            print('  OK (' + str(status) + '): ' + path + ' (' + str(len(content_bytes)) + ' bytes)')
        else:
            print('  MISSING (' + str(status) + '): ' + path)
