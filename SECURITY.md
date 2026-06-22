# Security Policy

## What Not to Commit

Never commit the following to this repository:

- **User data files** — do not check in real `users.json`, `users.csv`, or audit reports containing actual M365 account information
- **API keys, tokens, credentials** — this tool reads files; provide data via `--input` flags, not hardcoded secrets
- **Personal information** — usernames, email addresses, phone numbers, or real organizational data used in testing
- **Configuration with secrets** — .env files, connection strings, or service principal credentials
- **Sample reports with real data** — reports generated from production systems
- **Private organizational data** — internal naming conventions, role hierarchies, or compliance policies specific to your organization

Use sample/fake data for examples and tests only.

## Security Considerations

### Input Validation

- The tool accepts user-provided data files (JSON or CSV) from the filesystem
- Malformed input is caught and reported; parsing errors do not cause crashes
- List and boolean fields are coerced to expected types
- File reading respects filesystem permissions; use OS-level access controls to protect user data files

### Output

- Reports are written to stdout or specified file paths with user-controlled permissions
- JSON and CSV output include finding details, severity, and target identifiers (UPNs)
- Text reports are human-readable and suitable for console or file output
- No credentials, API keys, or sensitive configuration appears in output

### Recommended Usage

- **Restrict file access** — keep input user data and output reports on secure, access-controlled machines
- **Use in controlled environments** — run audits on isolated systems or within trusted CI/CD pipelines
- **Operate on copies** — export user data from M365 to a secure location, then run audits offline
- **Review findings** — treat findings as signals for investigation; verify all HIGH/CRITICAL issues before acting
- **Store reports securely** — comply with your organization's data retention and confidentiality policies

## Reporting Security Issues

If you discover a security vulnerability in this tool:

1. **Do not open a public issue** — security issues should not be disclosed publicly before a fix is available
2. **Email the maintainer** — send a detailed report to the email address listed in the repository metadata
3. **Include reproduction steps** — provide a minimal example that triggers the issue
4. **Allow time for response** — maintainers will investigate and work toward a fix

## Data Handling

This tool:

- **Does not send data externally** — all processing is local to the machine where it runs
- **Does not cache sensitive data** — findings and reports exist only in stdout, files you create, or memory during the run
- **Does not modify input files** — audits are read-only operations
- **Does not require network access** — works entirely offline once installed

## License

This tool is open-source under the MIT License. Use it in accordance with your organizational security and compliance policies.
