# iokdigital/.github

Org-wide CI/CD configuration for the `iokdigital` GitHub organisation.

## What lives here

This repository centralises shared GitHub Actions workflows and configuration so the rest of the org (7 active repos) doesn't need to maintain its own copies.

### Workflows

| Workflow | Schedule | Purpose |
|---|---|---|
| `org-security-scan.yml` | Sundays 9 AM UTC | Cross-repo security scan that fetches dependency manifests and runs OSV-Scanner / pip-audit / npm audit. Posts aggregate results to a single weekly GitHub issue. |

## Known limitation: private repo scanning

The workflow's default `GITHUB_TOKEN` (a per-run installation token) can read **public** repos cross-org in this setup — including `iokdigital/go-mermaid` (the only public repo).

For the **6 private repos** (`alteryx2airflow`, `alteryx2talend`, `flowport-webapp`, `flowport2jira`, `iok.digital`, `talend2airflow`), the workflow needs a Personal Access Token with `repo` scope.

### To enable private-repo scanning

1. Create a PAT at https://github.com/settings/tokens/new with these scopes:
   - `repo` (full control of private repositories)
   - `read:org` (read org membership)
2. Add it as a secret in this repo:
   - `gh secret set CROSS_REPO_READ_TOKEN --repo iokdigital/.github`
3. The workflow automatically uses it (`${{ secrets.CROSS_REPO_READ_TOKEN || secrets.GITHUB_TOKEN }}`)

Without this token, the workflow still runs successfully on Sundays and posts a weekly issue — it just reports "SKIPPED: 404" for the 6 private repos and reports actual findings for the 1 public repo (go-mermaid).

## Migration safety net

The per-repo `security.yml` cron jobs (in alteryx2airflow, alteryx2talend, flowport2jira, talend2airflow, flowport-webapp) are kept active as a safety net. Once this central workflow has been running reliably with the PAT for ~4 weeks, those per-repo crons can be removed in a follow-up PR.

Refs: docs/DEPENDABOT_ALERT_RISK_REPORT_2026-08-24.md
