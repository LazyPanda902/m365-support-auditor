"""Core audit engine for M365 user accounts, licenses, and security policies."""

from __future__ import annotations

import csv
import dataclasses
import datetime
import enum
import io
import json
import pathlib
from typing import Any


class Severity(enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def __lt__(self, other: "Severity") -> bool:
        order = [s.value for s in Severity]
        return order.index(self.value) < order.index(other.value)


_SEVERITY_RANK: dict[str, int] = {s.value: i for i, s in enumerate(Severity)}


@dataclasses.dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    target: str
    message: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "target": self.target,
            "message": self.message,
            "detail": self.detail,
        }


@dataclasses.dataclass
class AuditReport:
    generated_at: datetime.datetime
    findings: list[Finding] = dataclasses.field(default_factory=list)

    # --- aggregation helpers ---

    def by_severity(self, severity: Severity) -> list[Finding]:
        return [f for f in self.findings if f.severity == severity]

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts

    # --- serialisation ---

    def to_json(self, indent: int = 2) -> str:
        payload = {
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary(),
            "findings": [f.as_dict() for f in self.findings],
        }
        return json.dumps(payload, indent=indent)

    def to_csv(self) -> str:
        buf = io.StringIO()
        fieldnames = ["rule_id", "severity", "target", "message", "detail"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for f in self.findings:
            writer.writerow(f.as_dict())
        return buf.getvalue()

    def to_text(self) -> str:
        lines: list[str] = [
            f"M365 Support Audit Report — {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 64,
        ]
        summary = self.summary()
        lines.append("Summary:")
        for sev in Severity:
            count = summary[sev.value]
            if count:
                lines.append(f"  {sev.value:<8} {count}")
        lines.append("")

        sorted_findings = sorted(
            self.findings,
            key=lambda f: _SEVERITY_RANK[f.severity.value],
            reverse=True,
        )
        for f in sorted_findings:
            lines.append(f"[{f.severity.value}] {f.rule_id} — {f.target}")
            lines.append(f"  {f.message}")
            if f.detail:
                lines.append(f"  Detail: {f.detail}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_LICENSE_TYPES = frozenset({
    "Microsoft365BusinessBasic",
    "Microsoft365BusinessStandard",
    "Microsoft365BusinessPremium",
    "Microsoft365E3",
    "Microsoft365E5",
    "ExchangeOnlinePlan1",
    "ExchangeOnlinePlan2",
})

_PASSWORD_NEVER_EXPIRES_RISK_ROLES = frozenset({
    "GlobalAdmin",
    "SecurityAdmin",
    "ComplianceAdmin",
    "PrivilegedRoleAdmin",
    "ExchangeAdmin",
    "SharePointAdmin",
})


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "enabled"}


def _days_since(date_str: str) -> int | None:
    """Return days elapsed since *date_str* (ISO 8601). Returns None on parse failure."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.datetime.strptime(date_str, fmt)
            delta = datetime.datetime.utcnow() - parsed
            return delta.days
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

class _Rules:
    """Stateless rule functions — each returns a list of Findings."""

    @staticmethod
    def mfa_not_enabled(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        if not _parse_bool(user.get("mfaEnabled", False)):
            role = user.get("role", "")
            sev = Severity.CRITICAL if role in _PASSWORD_NEVER_EXPIRES_RISK_ROLES else Severity.HIGH
            findings.append(Finding(
                rule_id="SEC-001",
                severity=sev,
                target=upn,
                message="MFA is not enabled for this account.",
                detail=f"Role: {role or 'None'}",
            ))
        return findings

    @staticmethod
    def account_disabled_with_license(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        enabled = _parse_bool(user.get("accountEnabled", True))
        licenses: list[str] = user.get("assignedLicenses", [])
        if not enabled and licenses:
            findings.append(Finding(
                rule_id="LIC-001",
                severity=Severity.MEDIUM,
                target=upn,
                message="Disabled account still holds active license assignments.",
                detail=f"Licenses: {', '.join(licenses)}",
            ))
        return findings

    @staticmethod
    def unrecognised_license(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        for lic in user.get("assignedLicenses", []):
            if lic not in _VALID_LICENSE_TYPES:
                findings.append(Finding(
                    rule_id="LIC-002",
                    severity=Severity.LOW,
                    target=upn,
                    message=f"Unrecognised license SKU: {lic!r}.",
                    detail="Verify SKU is intentional and not a typo.",
                ))
        return findings

    @staticmethod
    def password_never_expires_privileged(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        role = user.get("role", "")
        if role in _PASSWORD_NEVER_EXPIRES_RISK_ROLES and _parse_bool(
            user.get("passwordNeverExpires", False)
        ):
            findings.append(Finding(
                rule_id="SEC-002",
                severity=Severity.HIGH,
                target=upn,
                message="Privileged account has non-expiring password.",
                detail=f"Role: {role}. Consider enforcing password rotation.",
            ))
        return findings

    @staticmethod
    def stale_account(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        last_sign_in = user.get("lastSignInDateTime", "")
        if not last_sign_in:
            return findings
        days = _days_since(last_sign_in)
        if days is None:
            return findings
        if days >= 180:
            findings.append(Finding(
                rule_id="ACC-001",
                severity=Severity.MEDIUM,
                target=upn,
                message=f"Account has not signed in for {days} days.",
                detail="Consider disabling or reviewing this account.",
            ))
        elif days >= 90:
            findings.append(Finding(
                rule_id="ACC-001",
                severity=Severity.LOW,
                target=upn,
                message=f"Account has not signed in for {days} days.",
                detail="Monitor for continued inactivity.",
            ))
        return findings

    @staticmethod
    def no_assigned_group(user: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>")
        groups: list[str] = user.get("groupMemberships", [])
        enabled = _parse_bool(user.get("accountEnabled", True))
        if enabled and not groups:
            findings.append(Finding(
                rule_id="ACC-002",
                severity=Severity.INFO,
                target=upn,
                message="Active account belongs to no security or distribution groups.",
                detail="Verify this is intentional (e.g. external guest or service account).",
            ))
        return findings

    @staticmethod
    def privileged_no_dedicated_account(user: dict[str, Any]) -> list[Finding]:
        """Flag privileged users whose UPN does not follow an admin-naming convention."""
        findings: list[Finding] = []
        upn = user.get("userPrincipalName", "<unknown>").lower()
        role = user.get("role", "")
        if role in _PASSWORD_NEVER_EXPIRES_RISK_ROLES:
            has_admin_prefix = any(upn.startswith(p) for p in ("adm.", "admin.", "svc.", "priv."))
            if not has_admin_prefix:
                findings.append(Finding(
                    rule_id="SEC-003",
                    severity=Severity.MEDIUM,
                    target=user.get("userPrincipalName", "<unknown>"),
                    message="Privileged account UPN lacks admin-naming prefix.",
                    detail=(
                        f"Role {role!r} should use a dedicated admin account "
                        "(e.g. adm.user@domain) separate from day-to-day UPN."
                    ),
                ))
        return findings


_ALL_RULES = [
    _Rules.mfa_not_enabled,
    _Rules.account_disabled_with_license,
    _Rules.unrecognised_license,
    _Rules.password_never_expires_privileged,
    _Rules.stale_account,
    _Rules.no_assigned_group,
    _Rules.privileged_no_dedicated_account,
]


# ---------------------------------------------------------------------------
# AuditEngine
# ---------------------------------------------------------------------------

class AuditEngine:
    """
    Runs configured rules against a list of M365 user records.

    Each user record is a dict with the following optional keys:
        userPrincipalName   str
        accountEnabled      bool | str
        mfaEnabled          bool | str
        role                str
        assignedLicenses    list[str]
        passwordNeverExpires bool | str
        lastSignInDateTime  str  (ISO 8601)
        groupMemberships    list[str]
    """

    def __init__(self, rules: list | None = None) -> None:
        self._rules = rules if rules is not None else _ALL_RULES

    # --- input loaders ---

    def load_json(self, source: str | pathlib.Path | io.TextIOBase) -> list[dict[str, Any]]:
        if isinstance(source, (str, pathlib.Path)):
            text = pathlib.Path(source).read_text(encoding="utf-8")
        else:
            text = source.read()
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "users" in data:
            return data["users"]
        raise ValueError("JSON must be a list of user objects or {\"users\": [...]}")

    def load_csv(self, source: str | pathlib.Path | io.TextIOBase) -> list[dict[str, Any]]:
        if isinstance(source, (str, pathlib.Path)):
            text = pathlib.Path(source).read_text(encoding="utf-8")
        else:
            text = source.read()
        reader = csv.DictReader(io.StringIO(text))
        records: list[dict[str, Any]] = []
        for row in reader:
            record: dict[str, Any] = dict(row)
            # coerce list fields encoded as semicolon-separated strings
            for list_field in ("assignedLicenses", "groupMemberships"):
                raw = record.get(list_field, "")
                record[list_field] = [v.strip() for v in raw.split(";") if v.strip()] if raw else []
            records.append(record)
        return records

    # --- audit runner ---

    def run(self, users: list[dict[str, Any]]) -> AuditReport:
        report = AuditReport(generated_at=datetime.datetime.utcnow())
        for user in users:
            for rule in self._rules:
                report.findings.extend(rule(user))
        return report
