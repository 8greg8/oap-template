# Security Policy

## Supported Versions

| Version            | Supported          |
| ------------------ | ------------------ |
| latest `develop`   | :white_check_mark: |
| latest `main`      | :white_check_mark: |
| any older commit   | :x:                |

This repository has no tagged releases yet. Only the latest commits on `develop` and `main`
receive security fixes; update to them before reporting.

Once releases exist, we support the **latest minor release and the one immediately prior** with
security updates. Older versions receive no patches; upgrade to a supported release before
reporting.

## Scope

### In Scope

- Task, backlog, report and housekeeping tooling (`.agents/tasks/scripts/`)
- Gate, gitflow, commit-lint and release tooling (`scripts/`)
- Git hooks (`.husky/`)
- The project initialization script (`init_project.py`)
- Dev container configuration (`.devcontainer/`, including `postCreate.sh` and `spec-blind/`)
- Source code and tests (`src/`, `tests/`)
- Agent instruction files (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `.agents/README.md`),
  including unsafe behavior they cause, such as a rule that would lead an agent to leak secrets
  or run destructive commands
- Dependency pins (`uv.lock`, `package-lock.json`)

### Out of Scope

- Projects created from this template — report to their maintainers, unless the flaw comes from
  a file this template provides
- AI coding agents and their vendors' products — report to the vendor
- Third-party dependencies — report to the upstream maintainer; notify us so we can track
  remediation
- Social engineering or phishing attacks targeting maintainers
- Physical access attacks

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately rather than opening a public issue.

**Preferred:** Use GitHub private vulnerability reporting: open the repository's **Security**
tab and click **Report a vulnerability**. This routes directly to the maintainers through
GitHub's secure channel.

**Fallback:** Email info@koporec.eu

Please include the following details in your report:

- A clear description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested mitigations or fixes
- Your estimate of the CVSS v3.1 severity (if known)

**Preferred language:** English.

## Severity Classification

We use [CVSS v3.1](https://www.first.org/cvss/v3.1/specification-document) scores to classify severity and set resolution timelines:

| Severity | CVSS v3.1 Score | Resolution SLA        |
| -------- | --------------- | --------------------- |
| Critical | 9.0 – 10.0      | 14 business days      |
| High     | 7.0 – 8.9       | 14 business days      |
| Medium   | 4.0 – 6.9       | 30 business days      |
| Low      | 0.1 – 3.9       | 30 business days      |

## Response SLA

- **Acknowledgment:** Within 48 hours of receiving your report.
- **Initial assessment:** Within 5 business days.
- **Resolution or mitigation plan:** Within 14 business days for critical vulnerabilities, 30 business days for all others.

We will keep you informed of our progress throughout the process and credit you in any public disclosure (unless you prefer to remain anonymous).

## CVE Assignment

We will request a CVE identifier for all confirmed vulnerabilities via [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories). The advisory will be published after a fix is available or upon reaching the disclosure deadline, whichever comes first.

## Coordinated Disclosure

We follow a **90-day coordinated disclosure policy**. We will publish a security advisory within 90 days of receiving a report, regardless of whether a fix is ready. If active exploitation is confirmed, we may disclose sooner in the public interest.

We ask that you do not publicly disclose the vulnerability before we have had the opportunity to respond and remediate.

## Supply Chain

If you discover a vulnerability in one of our dependencies, please report it to the upstream maintainer first. You are welcome to notify us as well so we can monitor remediation and pin or patch the affected version in a timely manner.

## Safe Harbor

We consider security research conducted in accordance with this policy to be authorised. This repository runs no service, so test only against your own clone of it or a project you created from the template. We will not initiate legal action against researchers who:

- Report vulnerabilities through the channels described above
- Test only against their own clone or a project they created from the template
- Avoid accessing, modifying, or deleting data beyond what is necessary to demonstrate the issue
- Do not affect other people's repositories, clones or projects during testing
- Act in good faith and do not exploit vulnerabilities for personal gain

We ask that you give us a reasonable opportunity to investigate and address the issue before any public disclosure.
