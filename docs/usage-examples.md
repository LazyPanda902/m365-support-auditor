# Usage Examples

## Scenario 1: Quick Security Audit with Text Output

Export your M365 users from Azure AD and run a basic audit:

```bash
$ m365-auditor audit users.json

M365 Support Audit Report — 2026-06-22 14:32:00
================================================================

Summary:
  CRITICAL 2
  HIGH     5
  MEDIUM   3
  LOW      1
  INFO     4

[CRITICAL] SEC-001 — admin@contoso.com
  MFA is not enabled for this account.
  Detail: Role: GlobalAdmin

[CRITICAL] SEC-001 — sec.admin@contoso.com
  MFA is not enabled for this account.
  Detail: Role: SecurityAdmin

[HIGH] SEC-002 — svc.backup@contoso.com
  Privileged account has non-expiring password.
  Detail: Role: ExchangeAdmin. Consider enforcing password rotation.

[HIGH] SEC-003 — john.smith@contoso.com
  Privileged account UPN lacks admin-naming prefix.
  Detail: Role GlobalAdmin should use a dedicated admin account (e.g. adm.user@domain) separate from day-to-day UPN.

[MEDIUM] LIC-001 — guest.user@contoso.com
  Disabled account still holds active license assignments.
  Detail: Licenses: Microsoft365E3

[MEDIUM] ACC-001 — intern.old@contoso.com
  Account has not signed in for 210 days.
  Detail: Consider disabling or reviewing this account.

[LOW] ACC-001 — remote.worker@contoso.com
  Account has not signed in for 120 days.
  Detail: Monitor for continued inactivity.

[LOW] LIC-002 — test.user@contoso.com
  Unrecognised license SKU: 'CustomLicense-Beta'.
  Detail: Verify SKU is intentional and not a typo.

[INFO] ACC-002 — contractor@contoso.com
  Active account belongs to no security or distribution groups.
  Detail: Verify this is intentional (e.g. external guest or service account).

[INFO] ACC-002 — api.service@contoso.com
  Active account belongs to no security or distribution groups.
  Detail: Verify this is intentional (e.g. external guest or service account).

[INFO] ACC-002 — monitor@contoso.com
  Active account belongs to no security or distribution groups.
  Detail: Verify this is intentional (e.g. external guest or service account).

[INFO] ACC-002 — backup@contoso.com
  Active account belongs to no security or distribution groups.
  Detail: Verify this is intentional (e.g. external guest or service account).
```

## Scenario 2: Export to JSON for Compliance Reporting

Generate a machine-readable report for archival or further analysis:

```bash
$ m365-auditor audit users.json --format=json --output=compliance_report_2026-06-22.json

Report written to compliance_report_2026-06-22.json

$ cat compliance_report_2026-06-22.json
{
  "generated_at": "2026-06-22T14:32:00.123456",
  "summary": {
    "INFO": 4,
    "LOW": 1,
    "MEDIUM": 3,
    "HIGH": 5,
    "CRITICAL": 2
  },
  "findings": [
    {
      "rule_id": "SEC-001",
      "severity": "CRITICAL",
      "target": "admin@contoso.com",
      "message": "MFA is not enabled for this account.",
      "detail": "Role: GlobalAdmin"
    },
    {
      "rule_id": "SEC-001",
      "severity": "CRITICAL",
      "target": "sec.admin@contoso.com",
      "message": "MFA is not enabled for this account.",
      "detail": "Role: SecurityAdmin"
    },
    {
      "rule_id": "SEC-002",
      "severity": "HIGH",
      "target": "svc.backup@contoso.com",
      "message": "Privileged account has non-expiring password.",
      "detail": "Role: ExchangeAdmin. Consider enforcing password rotation."
    }
  ]
}
```

## Scenario 3: Filter by Severity for Management Review

Show only HIGH and CRITICAL issues for immediate action:

```bash
$ m365-auditor audit users.json --min-severity=HIGH

M365 Support Audit Report — 2026-06-22 14:32:00
================================================================

Summary:
  HIGH     5
  CRITICAL 2

[CRITICAL] SEC-001 — admin@contoso.com
  MFA is not enabled for this account.
  Detail: Role: GlobalAdmin

[CRITICAL] SEC-001 — sec.admin@contoso.com
  MFA is not enabled for this account.
  Detail: Role: SecurityAdmin

[HIGH] SEC-002 — svc.backup@contoso.com
  Privileged account has non-expiring password.
  Detail: Role: ExchangeAdmin. Consider enforcing password rotation.

[HIGH] SEC-003 — john.smith@contoso.com
  Privileged account UPN lacks admin-naming prefix.
  Detail: Role GlobalAdmin should use a dedicated admin account (e.g. adm.user@domain) separate from day-to-day UPN.

[HIGH] ...
```

## Scenario 4: CI/CD Pipeline Integration

Fail the build if compliance violations are found:

```bash
#!/bin/bash
# audit.sh — part of your CI/CD pipeline

set -e

echo "Exporting M365 user data..."
# (Your script to export users from Azure AD to users.json)

echo "Running compliance audit..."
m365-auditor audit users.json --format=json --output=report.json

echo "Checking for HIGH or CRITICAL findings..."
m365-auditor audit users.json --fail-on=HIGH

if [ $? -ne 0 ]; then
  echo "AUDIT FAILED: HIGH or CRITICAL security issues detected"
  m365-auditor summary report.json
  exit 1
fi

echo "Audit passed. Report: $(pwd)/report.json"
```

Usage in GitHub Actions:

```yaml
- name: Run M365 compliance audit
  run: |
    m365-auditor audit users.json --fail-on=MEDIUM
  continue-on-error: false
```

## Scenario 5: Export to CSV for Spreadsheet Analysis

Generate findings in CSV format for Excel or data analysis tools:

```bash
$ m365-auditor audit users.json --format=csv --output=findings.csv

Report written to findings.csv

$ head -20 findings.csv
rule_id,severity,target,message,detail
SEC-001,CRITICAL,admin@contoso.com,MFA is not enabled for this account.,Role: GlobalAdmin
SEC-001,CRITICAL,sec.admin@contoso.com,MFA is not enabled for this account.,Role: SecurityAdmin
SEC-002,HIGH,svc.backup@contoso.com,Privileged account has non-expiring password.,Role: ExchangeAdmin. Consider enforcing password rotation.
SEC-003,MEDIUM,john.smith@contoso.com,Privileged account UPN lacks admin-naming prefix.,Role GlobalAdmin should use a dedicated admin account (e.g. adm.user@domain) separate from day-to-day UPN.
LIC-001,MEDIUM,guest.user@contoso.com,Disabled account still holds active license assignments.,Licenses: Microsoft365E3
ACC-001,MEDIUM,intern.old@contoso.com,Account has not signed in for 210 days.,Consider disabling or reviewing this account.
```

## Scenario 6: Summary of Previous Report

View a summary without re-running the audit:

```bash
$ m365-auditor summary report.json

Report: report.json
Generated: 2026-06-22T14:32:00.123456
Total findings: 15

  CRITICAL 2
  HIGH     5
  MEDIUM   3
  LOW      1
  INFO     4
```

## Scenario 7: Audit a CSV File

If your export is in CSV format instead of JSON:

```bash
$ m365-auditor audit users.csv --format=json --output=report.json

Report written to report.json
```

Input CSV (`users.csv`):

```
userPrincipalName,accountEnabled,mfaEnabled,role,assignedLicenses,passwordNeverExpires,lastSignInDateTime,groupMemberships
user1@contoso.com,true,true,User,Microsoft365E3,,2026-06-20T10:00:00,Engineering;Staff
admin@contoso.com,true,false,GlobalAdmin,Microsoft365E5;ExchangeOnlinePlan2,true,2026-06-21T15:20:00,AdminGroup
guest@contoso.com,false,true,User,Microsoft365E3,,2025-12-01T08:30:00,
intern@contoso.com,true,true,User,Microsoft365E3,,2024-06-01T09:00:00,Interns
```

## Scenario 8: Identify Stale Accounts

Filter for INFO-level findings (stale accounts with no group memberships):

```bash
$ m365-auditor audit users.json --min-severity=INFO --max-severity=INFO 2>/dev/null | grep -A1 "ACC-001\|ACC-002"

[INFO] ACC-002 — contractor@contoso.com
  Active account belongs to no security or distribution groups.

[INFO] ACC-002 — api.service@contoso.com
  Active account belongs to no security or distribution groups.
```

(Note: `--max-severity` is not a real flag; use jq or grep on JSON output for precise filtering.)

Alternatively, export to JSON and filter programmatically:

```bash
$ m365-auditor audit users.json --format=json | jq '.findings[] | select(.rule_id == "ACC-001")'
{
  "rule_id": "ACC-001",
  "severity": "MEDIUM",
  "target": "intern.old@contoso.com",
  "message": "Account has not signed in for 210 days.",
  "detail": "Consider disabling or reviewing this account."
}
```
