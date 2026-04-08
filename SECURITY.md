# Security Policy

## Supported Versions

Security fixes are applied to the latest release only. We encourage all users to keep their installation up to date.

## Reporting a Vulnerability

If you discover a security vulnerability in Claude Ticket Pilot, please **do not** open a public GitHub issue. Public disclosure before a fix is available puts other users at risk.

Instead, please report vulnerabilities privately:

1. **Email** — Send details to the maintainers via the email address listed on the GitHub repository's security contact page, if available.
2. **GitHub Private Vulnerability Reporting** — Use the "Report a vulnerability" button on the repository's Security tab (requires a GitHub account).

### What to include

When reporting, please provide:

- A description of the vulnerability and its potential impact.
- Step-by-step instructions to reproduce it.
- Any proof-of-concept code or screenshots that help illustrate the issue.
- The version of Claude Ticket Pilot you are using.

### What to expect

- We will acknowledge receipt of your report within **3 business days**.
- We will provide an estimated timeline for a fix within **7 business days**.
- We will notify you when a fix has been released.
- We will credit you in the release notes unless you prefer to remain anonymous.

## Scope

The following are in scope for vulnerability reports:

- Credential or secret exposure (e.g. API keys written to disk or logs in cleartext).
- Arbitrary code execution triggered by malicious ticket content.
- Authentication or authorization bypasses in tracker integrations.
- Insecure handling of environment variables or configuration files.

The following are generally out of scope:

- Vulnerabilities in third-party dependencies (please report those upstream).
- Issues that require physical access to the machine running the skill.
- Theoretical vulnerabilities without a demonstrated impact.

## Security Best Practices for Users

- Store API keys and credentials only in the `.env` file, which is excluded from version control by `.gitignore`.
- Do not share your `.env` file or commit it to any repository.
- Rotate API keys immediately if you suspect they have been compromised.
- Review the permissions requested by any Claude Code skill before installation.
