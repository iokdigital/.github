#!/usr/bin/env python3
"""Summarize npm audit JSON to a single line."""
import json, sys

try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    if isinstance(d, dict) and 'metadata' in d:
        total = d.get('metadata', {}).get('vulnerabilities', {}).get('total', '?')
        print(f"  Total vulnerabilities: {total}")
    else:
        print(f"  (vulnerabilities: {len(d) if isinstance(d, list) else 'unknown'})")
except Exception as e:
    print(f"  (parse error: {e})")
