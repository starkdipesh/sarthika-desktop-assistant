# Security Policy

## Responsible Disclosure

The maintainers of Sarthika Code take privacy and local system security seriously. While Sarthika Code is an open-source project without a commercial 24/7 security operations center, we are dedicated to addressing verified security vulnerabilities promptly.

If you believe you have discovered a security vulnerability in Sarthika Code, please report it responsibly rather than opening a public issue.

---

## Reporting a Vulnerability

Please report security issues privately via GitHub Security Advisories:
* Navigate to the project's repository on GitHub.
* Click the **Security** tab.
* Select **Advisories** and click **Report a vulnerability**.

Alternatively, if private advisories are unavailable, contact the maintainers directly through the repository owner's GitHub profile.

### What to Include in Your Report
To help us reproduce and resolve the issue quickly, please provide:
1. **Description**: Clear description of the vulnerability.
2. **Impact**: Potential consequences if exploited (e.g. data disclosure, local file access, denial of service).
3. **Steps to Reproduce**: Minimal, reproducible proof-of-concept steps or scripts.
4. **Environment**: Operating system, Python version, PySide6 version, and model/server configuration.
5. **Mitigation**: Any suggested patch or remediation, if available.

We will acknowledge receipt within 48 hours and work with you on an coordinated advisory and patch.

---

## Security Invariants of Sarthika Code

Sarthika Code is designed around the following local security invariants:

1. **No Outbound Network Traffic**: The core application should never send prompts, context files, code snippets, or user data over the internet. Any bug resulting in unintended external network egress is treated as a high-severity flaw.
2. **No Command or Shell Execution**: Sarthika Code must never execute arbitrary shell commands or run generated code.
3. **No Silent Project Modification**: The application operates in a strictly read-only mode regarding user project files. It does not overwrite or patch source files on disk.
4. **Context Screening**: The application actively screens attached files to prevent accidental inclusion of `.env` files, SSH keys, certificates, credentials, and binary executables.
