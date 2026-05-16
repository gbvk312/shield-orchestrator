# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within ShieldOrchestrator, please report it responsibly.

**Do NOT open a public GitHub issue.**

Instead, please send an email to the maintainer with:

1. A description of the vulnerability.
2. Steps to reproduce the issue.
3. Any potential impact assessment.

You should receive a response within 48 hours acknowledging your report. We will work with you to understand and address the issue before any public disclosure.

## Security Best Practices

When using ShieldOrchestrator:

- **Never commit API keys** — always use `.env` files (excluded via `.gitignore`).
- **Keep dependencies updated** — run `uv sync` regularly.
- **Review agent outputs** — AI-generated fixes should always be reviewed by a human before merging.
- **Use the principle of least privilege** — grant agents only the permissions they need.
