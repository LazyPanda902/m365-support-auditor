# Configuration and Setup

## Installation

### From Source

Clone the repository and install in development mode:

```bash
git clone <repository-url>
cd m365-support-auditor
pip install -e .
```

### From PyPI

```bash
pip install m365-support-auditor
```

### Requirements

- Python 3.9 or later
- No external runtime dependencies (standard library only)
- Supports Windows, macOS, and Linux

## Preparing User Data

### Exporting from Azure AD / Entra ID

Use Azure AD PowerShell module to export users:

```powershell
# Install module (if not already installed)
Install-Module -Name AzureAD -Force

# Connect to Azure AD
Connect-AzureAD

# Export users to JSON
Get-AzureADUser -All $true | Select-Object `
  UserPrincipalName,
  AccountEnabled,
  @{Label="mfaEnabled"; Expression={$null}},
  @{Label="role"; Expression={$null}},
  @{Label="assignedLicenses"; Expression={(Get-AzureADUserLicenseDetail -ObjectId $_.ObjectId).SkuPartNumber -join ";"}},
  @{Label="passwordNeverExpires"; Expression={$null}},
  LastSignInDateTime,
  @{Label="groupMemberships"; Expression={(Get-AzureADUserMembership -ObjectId $_.ObjectId).DisplayName -join ";"}} | `
  ConvertTo-Json | Out-File -FilePath users.json -Encoding UTF8
```

Or using Microsoft Graph:

```powershell
# Connect to Microsoft Graph
Connect-MgGraph -Scopes "User.Read.All", "AuditLog.Read.All"

# Export basic user properties
Get-MgUser -All | Select-Object UserPrincipalName, AccountEnabled, LastSignInDateTime | `
  ConvertTo-Json | Out-File -FilePath users.json -Encoding UTF8
```

### Sample Data Format

JSON format (direct array):

```json
[
  {
    "userPrincipalName": "alice@contoso.com",
    "accountEnabled": true,
    "mfaEnabled": true,
    "role": "User",
    "assignedLicenses": ["Microsoft365E3"],
    "passwordNeverExpires": false,
    "lastSignInDateTime": "2026-06-20T14:30:00",
    "groupMemberships": ["Engineering", "Staff"]
  },
  {
    "userPrincipalName": "admin@contoso.com",
    "accountEnabled": true,
    "mfaEnabled": false,
    "role": "GlobalAdmin",
    "assignedLicenses": ["Microsoft365E5"],
    "passwordNeverExpires": true,
    "lastSignInDateTime": "2026-06-21T09:15:00",
    "groupMemberships": ["AdminGroup"]
  }
]
```

JSON format (wrapped):

```json
{
  "users": [
    {
      "userPrincipalName": "alice@contoso.com",
      ...
    }
  ]
}
```

CSV format:

```csv
userPrincipalName,accountEnabled,mfaEnabled,role,assignedLicenses,passwordNeverExpires,lastSignInDateTime,groupMemberships
alice@contoso.com,true,true,User,Microsoft365E3,false,2026-06-20T14:30:00,Engineering;Staff
admin@contoso.com,true,false,GlobalAdmin,Microsoft365E5,true,2026-06-21T09:15:00,AdminGroup
```

### Field Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `userPrincipalName` | string | Yes | User's primary email (UPN) |
| `accountEnabled` | bool \| string | No | `true`, `false`, `"true"`, `"1"`, `"yes"`, or `"enabled"` |
| `mfaEnabled` | bool \| string | No | `true` or `false` |
| `role` | string | No | Admin role (GlobalAdmin, SecurityAdmin, ExchangeAdmin, etc.) |
| `assignedLicenses` | array \| string | No | License SKUs; in CSV use semicolon separator |
| `passwordNeverExpires` | bool \| string | No | `true` if password never expires |
| `lastSignInDateTime` | string | No | ISO 8601 format: `2026-06-20T14:30:00` or `2026-06-20` |
| `groupMemberships` | array \| string | No | Group display names; in CSV use semicolon separator |

## Running Audits

### Basic Usage

```bash
# Audit JSON file, display results to console
m365-auditor audit users.json

# Audit CSV file, save as JSON report
m365-auditor audit users.csv --format=json --output=report.json

# Audit and filter by severity
m365-auditor audit users.json --min-severity=HIGH

# Fail on HIGH or CRITICAL
m365-auditor audit users.json --fail-on=HIGH
echo $?  # Exit code will be 1 if issues found
```

### Filtering Results

```bash
# Show only CRITICAL findings
m365-auditor audit users.json --min-severity=CRITICAL

# Show INFO and above (all levels)
m365-auditor audit users.json --min-severity=INFO
```

### Output Handling

```bash
# Print to console (default)
m365-auditor audit users.json

# Save to file
m365-auditor audit users.json --output=report.txt

# Save as JSON
m365-auditor audit users.json --format=json --output=report.json

# Save as CSV
m365-auditor audit users.json --format=csv --output=report.csv

# Pipe to file
m365-auditor audit users.json > report.txt

# Pipe to other tools
m365-auditor audit users.json --format=json | jq '.findings'
```

## Integration with Scripts

### Bash / PowerShell Wrapper

Save user data, run audit, and archive report:

**Bash:**

```bash
#!/bin/bash

AUDIT_DATE=$(date +%Y-%m-%d)
REPORT_DIR="/var/audits"

# Export users (requires Azure AD/Graph auth)
export_users_from_azure_ad > users.json

# Run audit
m365-auditor audit users.json \
  --format=json \
  --output="${REPORT_DIR}/audit_${AUDIT_DATE}.json"

# Check for violations
if m365-auditor audit users.json --fail-on=MEDIUM; then
  echo "Audit passed"
else
  echo "Compliance violations detected"
  m365-auditor summary "${REPORT_DIR}/audit_${AUDIT_DATE}.json"
  exit 1
fi
```

**PowerShell:**

```powershell
$auditDate = Get-Date -Format "yyyy-MM-dd"
$reportDir = "C:\Audits"

# Export users
Get-AzureADUser -All $true | Select-Object UserPrincipalName, AccountEnabled | `
  ConvertTo-Json | Out-File "users.json"

# Run audit
m365-auditor audit users.json --format=json --output="$reportDir\audit_$auditDate.json"

# Check result
if ($LASTEXITCODE -ne 0) {
  Write-Error "Audit failed"
  exit 1
}
```

### Scheduled Tasks / Cron

**Windows Task Scheduler:**

Create a task that runs daily:

```
Program: PowerShell.exe
Arguments: -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\audit.ps1
Schedule: Daily at 02:00 AM
```

**Linux Cron:**

```cron
# Run daily audit at 2 AM
0 2 * * * /home/admin/audit.sh
```

## Troubleshooting

### File Not Found

```
error: file not found: users.json
```

**Solution:** Verify the file path and ensure the file exists:

```bash
ls -l users.json
pwd  # Check current directory
```

### Unsupported File Type

```
error: unsupported file type '.txt'. Use .json or .csv.
```

**Solution:** Use `.json` or `.csv` files only. Convert if needed:

```bash
# TXT to CSV
cat users.txt | tr '|' ',' > users.csv
```

### Invalid JSON

```
error: failed to load users.json: Expecting value: line 1 column 1
```

**Solution:** Validate JSON:

```bash
# Validate JSON
jq . users.json

# Fix with online tool or Python
python3 -m json.tool users.json
```

### Missing Required Fields

If `userPrincipalName` is missing, the tool treats it as `<unknown>` in results.

**Solution:** Ensure your export includes at least:

```json
[
  {
    "userPrincipalName": "user@example.com"
  }
]
```

## Performance Notes

- The tool processes users sequentially, executing all rules per user
- Performance is proportional to the number of users and rules
- Typical execution: 1,000 users in ~200ms
- Output rendering (especially text format) is fast; JSON/CSV formatting is slightly slower
