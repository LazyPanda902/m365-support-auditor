# m365-support-auditor

<!-- portfolio-card -->
<p align="center">
  <img src="docs/assets/project-card.svg" alt="m365-support-auditor project card" width="100%" />
</p>
<!-- /portfolio-card -->

A Python command-line tool to audit Microsoft 365 user accounts for security, compliance, and license management issues. Designed for Windows administrators managing Azure AD / Entra ID environments.

## Purpose

`m365-support-auditor` analyzes M365 user records and detects:

- **Security violations** — MFA disabled on privileged accounts, non-expiring passwords for admins, accounts lacking admin-naming conventions
- **License issues** — disabled accounts holding active licenses, unrecognized license SKUs
- **Compliance gaps** — stale accounts (no sign-in for 90+ days), users with no group memberships, accounts without security group assignments

Findings are categorized by severity (INFO, LOW, MEDIUM, HIGH, CRITICAL) and can be exported as text, JSON, or CSV for further processing.



## Features

- Audits Microsoft 365 user records from JSON or CSV files.
- Flags MFA, privileged-account, stale-account, group-membership, and license issues.
- Categorizes findings by severity for support and admin review.
- Exports reports as text, JSON, or CSV.
- Runs locally against exported data without requiring direct tenant access.
- Includes tests and GitHub Actions CI for repeatable validation.
## Installation

Install from the package directory:

```bash
pip install -e .
```

Or install directly:

```bash
pip install m365-support-auditor
```

Requires Python 3.9+.

## Usage

### Basic Audit

Run a security audit on a JSON file of M365 users:

```bash
m365-auditor audit users.json
```

Output (text format):

```
M365 Support Audit Report — 2026-06-22 14:32:00
================================================================

Summary:
  CRITICAL 2
  HIGH     5
  MEDIUM   3
  LOW      1

[CRITICAL] SEC-001 — admin@example.com
  MFA is not enabled for this account.
  Detail: Role: GlobalAdmin

[HIGH] SEC-002 — svc.backup@example.com
  Privileged account has non-expiring password.
  Detail: Role: ExchangeAdmin. Consider enforcing password rotation.

...
```

### CSV Input

Audit user data from a CSV file:

```bash
m365-auditor audit users.csv
```

CSV format (headers required):

```
userPrincipalName,accountEnabled,mfaEnabled,role,assignedLicenses,passwordNeverExpires,lastSignInDateTime,groupMemberships
user1@contoso.com,true,true,User,Microsoft365E3,,2026-06-20T09:30:00,Engineering;Staff
admin@contoso.com,true,false,GlobalAdmin,Microsoft365E5;ExchangeOnline,true,2026-06-21T15:20:00,AdminGroup
```

Multi-valued fields (assignedLicenses, groupMemberships) use semicolon separators.

### JSON Input

Audit a JSON file of user records:

```bash
m365-auditor audit users.json
```

JSON format (array or wrapped):

```json
[
  {
    "userPrincipalName": "user1@example.com",
    "accountEnabled": true,
    "mfaEnabled": true,
    "role": "User",
    "assignedLicenses": ["Microsoft365E3"],
    "passwordNeverExpires": false,
    "lastSignInDateTime": "2026-06-20T10:00:00",
    "groupMemberships": ["Staff", "Engineering"]
  }
]
```

Or wrapped format:

```json
{
  "users": [...]
}
```

### Output Formats

Export findings in different formats using `--format`:

**Text (default):**

```bash
m365-auditor audit users.json --format=text
```

**JSON:**

```bash
m365-auditor audit users.json --format=json > report.json
```

**CSV:**

```bash
m365-auditor audit users.json --format=csv > report.csv
```

### Filtering by Severity

Show only findings at a certain severity level or higher:

```bash
m365-auditor audit users.json --min-severity=HIGH
```

Levels: INFO, LOW, MEDIUM, HIGH, CRITICAL

### Exit Code Control

Fail (exit code 1) if any finding meets a severity threshold:

```bash
m365-auditor audit users.json --fail-on=MEDIUM
```

Useful for CI/CD pipelines to block on compliance violations.

### Save to File

Write the report to a file instead of stdout:

```bash
m365-auditor audit users.json --format=json --output=report.json
```

### Summary Report

Print a summary of findings from a previously generated JSON report:

```bash
m365-auditor summary report.json
```

Output:

```
Report: report.json
Generated: 2026-06-22T14:32:00.123456
Total findings: 11

  CRITICAL 2
  HIGH     5
  MEDIUM   3
  LOW      1
```

## Rules Reference

| Rule ID | Severity | Condition |
|---------|----------|-----------|
| SEC-001 | CRITICAL (admin) / HIGH | MFA not enabled |
| SEC-002 | HIGH | Privileged account with non-expiring password |
| SEC-003 | MEDIUM | Privileged role without admin-naming prefix |
| LIC-001 | MEDIUM | Disabled account holding active licenses |
| LIC-002 | LOW | Unrecognized license SKU |
| ACC-001 | MEDIUM (180+ days) / LOW (90+ days) | Account has not signed in |
| ACC-002 | INFO | Active account belongs to no groups |

**Privileged roles flagged by rules:** GlobalAdmin, SecurityAdmin, ComplianceAdmin, PrivilegedRoleAdmin, ExchangeAdmin, SharePointAdmin

## Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest --cov=m365_auditor tests/
```

Test categories:

- **Parser tests** — command-line argument parsing
- **Helper tests** — boolean parsing, date calculations
- **Rule tests** — each audit rule for correctness and edge cases
- **Engine tests** — input loading (JSON/CSV), report generation
- **CLI tests** — end-to-end workflows, exit codes

## Example Workflows

**Generate a JSON report for compliance review:**

```bash
m365-auditor audit users.json --format=json --output=audit_2026-06-22.json
```

**Fail CI if any HIGH severity issues found:**

```bash
m365-auditor audit users.json --fail-on=HIGH
if [ $? -ne 0 ]; then echo "Compliance check failed"; exit 1; fi
```

**Export HIGH and CRITICAL findings only to CSV:**

```bash
m365-auditor audit users.json --min-severity=HIGH --format=csv --output=critical.csv
```

**Check audit summary:**

```bash
m365-auditor audit users.json --format=json --output=report.json
m365-auditor summary report.json
```
