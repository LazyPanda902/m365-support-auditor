# Privacy Policy

## Data Processing

`m365-support-auditor` is a local, offline tool. It:

- **Processes data only on your machine** — no information is transmitted to external servers
- **Does not collect usage data** — there is no telemetry, logging to remote systems, or tracking
- **Does not require internet access** — functionality is entirely self-contained
- **Does not store data** — files exist only where you create them; no temporary caches are retained after the tool exits

## Sample and Fake Data

For testing and documentation purposes, this project includes **fake sample user records** (in test files and examples):

- Sample user emails are fictional (`user@example.com`, `admin@contoso.com`)
- No real personal information is used in examples or test data
- Sample data is for demonstration purposes only; do not treat it as templates for real user data

All sample data in test files (`tests/test_auditor.py`) and documentation (README.md, usage examples) is entirely synthetic and does not reference real people, organizations, or systems.

## Your Data

When you use this tool with your organization's M365 user data:

- **You control storage** — you decide where input files are kept and how reports are stored
- **You control access** — use filesystem permissions and access control lists to protect user data
- **You are responsible for compliance** — ensure your use complies with data protection regulations (GDPR, HIPAA, etc.) and your organization's privacy policies
- **No third parties see your data** — unless you explicitly share reports or input files

## Recommended Practices

- **Use local copies** — export M365 data to a secure, access-controlled machine
- **Limit access** — restrict file permissions on both input data and generated reports
- **Audit trail** — log when audits are run, by whom, and what changes result
- **Data retention** — define how long audit reports are kept and when they should be deleted
- **Anonymization** — if sharing findings with non-admin staff, consider removing identifying details

## Contact

For privacy inquiries specific to your organization's data handling, consult your data protection officer or privacy team.
