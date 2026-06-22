"""M365 Support Auditor — Windows admin automation for account, license, and security audits."""

__version__ = "0.1.0"
__all__ = ["AuditEngine", "AuditReport", "Finding", "Severity"]

from m365_auditor.auditor import AuditEngine, AuditReport, Finding, Severity
