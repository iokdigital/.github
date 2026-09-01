#!/usr/bin/env python3
"""Summarize OSV-Scanner JSON output."""
import json, sys

try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    if isinstance(d, list):
        for r in d:
            vulns = r.get('vulnerabilities', [])
            print(f"  {r.get('source',{}).get('path','?')}: {len(vulns)} vulns")
    elif isinstance(d, dict) and 'results' in d:
        for r in d['results']:
            vulns = r.get('vulnerabilities', [])
            print(f"  {r.get('source',{}).get('path','?')}: {len(vulns)} vulns")
    else:
        print(f"  (unexpected structure: {type(d).__name__})")
except Exception as e:
    print(f"  (parse error: {e})")
