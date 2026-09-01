# iokdigital/.github

Org-wide CI/CD configuration for the `iokdigital` GitHub organisation.

## What lives here

This repository centralises shared GitHub Actions workflows and configuration so that the rest of the org (7 active repos) doesn't need to maintain its own copies.

### Workflows

| Workflow | Schedule | Replaces | Saves |
|---|---|---|---|
| `org-security-scan.yml` | Sundays 9 AM UTC | 5 per-repo `security.yml` jobs in alteryx2airflow, alteryx2talend, flowport2jira, talend2airflow, flowport-webapp | ~5 weekly runs → 1 weekly run (~80% reduction in scheduled security CI minutes) |

## Why we did this

Before centralisation, each repo with scheduled security scans ran independently on its own cron. Two problems:

1. **Burst behaviour** — multiple repos could trigger at the same time, saturating GitHub Actions runners.
2. **PR review burden** — strands of security alerts scattered across 5 repos required 5 separate PR reviews per week.

The staggered-cron workaround (already applied) fixed (1). This centralisation also fixes (2) by aggregating findings into a single weekly GitHub issue in this repo.

## Migration plan

The per-repo `security.yml` cron jobs in:
- `iokdigital/alteryx2airflow`
- `iokdigital/alteryx2talend`
- `iokdigital/flowport2jira`
- `iokdigital/talend2airflow`

…are kept for now as a safety net (push-triggered scans still work). Once this central workflow has run successfully for 4 weeks straight, those cron lines can be removed.

`flowport-webapp`'s `security-scanning.yml` was changed from daily to weekly as a separate optimisation.
