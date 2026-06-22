"""Tests for m365_auditor — auditor engine and CLI."""

from __future__ import annotations

import io
import json
import pathlib
import sys

import pytest

from m365_auditor.auditor import (
    AuditEngine,
    AuditReport,
    Finding,
    Severity,
    _Rules,
    _days_since,
    _parse_bool,
)
from m365_auditor.cli import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(**kwargs):
    base = {
        "userPrincipalName": "user@example.com",
        "accountEnabled": True,
        "mfaEnabled": True,
        "role": "",
        "assignedLicenses": [],
        "passwordNeverExpires": False,
        "lastSignInDateTime": "",
        "groupMemberships": ["Staff"],
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

def test_build_parser_constructs():
    parser = build_parser()
    assert parser is not None
    assert parser.prog == "m365-auditor"


def test_build_parser_audit_defaults():
    parser = build_parser()
    args = parser.parse_args(["audit", "data.json"])
    assert args.command == "audit"
    assert args.output_format == "text"
    assert args.min_severity == "INFO"
    assert args.fail_on is None
    assert args.output is None


def test_build_parser_audit_format_choices():
    parser = build_parser()
    for fmt in ("text", "json", "csv"):
        args = parser.parse_args(["audit", "data.json", f"--format={fmt}"])
        assert args.output_format == fmt


def test_build_parser_audit_min_severity_choices():
    parser = build_parser()
    for sev in ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
        args = parser.parse_args(["audit", "data.json", f"--min-severity={sev}"])
        assert args.min_severity == sev


def test_build_parser_audit_fail_on():
    parser = build_parser()
    args = parser.parse_args(["audit", "data.json", "--fail-on=HIGH"])
    assert args.fail_on == "HIGH"


def test_build_parser_audit_output():
    parser = build_parser()
    args = parser.parse_args(["audit", "data.json", "--output=report.json"])
    assert args.output == pathlib.Path("report.json")


def test_build_parser_summary_subcommand():
    parser = build_parser()
    args = parser.parse_args(["summary", "report.json"])
    assert args.command == "summary"
    assert args.report == pathlib.Path("report.json")


def test_build_parser_no_subcommand_exits():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([])
    assert exc_info.value.code == 2


def test_build_parser_bad_format_exits():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["audit", "data.json", "--format=xml"])
    assert exc_info.value.code == 2


def test_build_parser_bad_min_severity_exits():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["audit", "data.json", "--min-severity=NONE"])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# _parse_bool
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (True, True),
    (False, False),
    ("true", True),
    ("True", True),
    ("1", True),
    ("yes", True),
    ("enabled", True),
    ("false", False),
    ("0", False),
    ("no", False),
    ("disabled", False),
])
def test_parse_bool(value, expected):
    assert _parse_bool(value) is expected


# ---------------------------------------------------------------------------
# _days_since
# ---------------------------------------------------------------------------

def test_days_since_valid_datetime():
    days = _days_since("2000-01-01T00:00:00")
    assert days is not None
    assert days > 8000


def test_days_since_valid_date():
    days = _days_since("2000-01-01")
    assert days is not None
    assert days > 8000


def test_days_since_invalid():
    assert _days_since("not-a-date") is None


def test_days_since_empty():
    assert _days_since("") is None


# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------

def test_severity_ordering():
    assert Severity.INFO < Severity.LOW
    assert Severity.LOW < Severity.MEDIUM
    assert Severity.MEDIUM < Severity.HIGH
    assert Severity.HIGH < Severity.CRITICAL


# ---------------------------------------------------------------------------
# Finding.as_dict
# ---------------------------------------------------------------------------

def test_finding_as_dict():
    f = Finding(
        rule_id="SEC-001",
        severity=Severity.HIGH,
        target="user@example.com",
        message="MFA not enabled.",
        detail="Role: GlobalAdmin",
    )
    d = f.as_dict()
    assert d["rule_id"] == "SEC-001"
    assert d["severity"] == "HIGH"
    assert d["target"] == "user@example.com"
    assert d["message"] == "MFA not enabled."
    assert d["detail"] == "Role: GlobalAdmin"


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def test_rule_mfa_not_enabled_high_for_standard_user():
    user = _user(mfaEnabled=False, role="User")
    findings = _Rules.mfa_not_enabled(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-001"
    assert findings[0].severity == Severity.HIGH


def test_rule_mfa_not_enabled_critical_for_admin():
    user = _user(mfaEnabled=False, role="GlobalAdmin")
    findings = _Rules.mfa_not_enabled(user)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL


def test_rule_mfa_enabled_no_finding():
    user = _user(mfaEnabled=True)
    assert _Rules.mfa_not_enabled(user) == []


def test_rule_account_disabled_with_license():
    user = _user(accountEnabled=False, assignedLicenses=["Microsoft365E3"])
    findings = _Rules.account_disabled_with_license(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "LIC-001"
    assert findings[0].severity == Severity.MEDIUM


def test_rule_account_disabled_no_license_no_finding():
    user = _user(accountEnabled=False, assignedLicenses=[])
    assert _Rules.account_disabled_with_license(user) == []


def test_rule_unrecognised_license():
    user = _user(assignedLicenses=["UnknownSKU-XYZ"])
    findings = _Rules.unrecognised_license(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "LIC-002"
    assert findings[0].severity == Severity.LOW


def test_rule_recognised_license_no_finding():
    user = _user(assignedLicenses=["Microsoft365E5"])
    assert _Rules.unrecognised_license(user) == []


def test_rule_password_never_expires_privileged():
    user = _user(role="GlobalAdmin", passwordNeverExpires=True)
    findings = _Rules.password_never_expires_privileged(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-002"
    assert findings[0].severity == Severity.HIGH


def test_rule_password_never_expires_non_privileged_no_finding():
    user = _user(role="User", passwordNeverExpires=True)
    assert _Rules.password_never_expires_privileged(user) == []


def test_rule_stale_account_180_plus_days():
    user = _user(lastSignInDateTime="2020-01-01T00:00:00")
    findings = _Rules.stale_account(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "ACC-001"
    assert findings[0].severity == Severity.MEDIUM


def test_rule_stale_account_no_sign_in_no_finding():
    user = _user(lastSignInDateTime="")
    assert _Rules.stale_account(user) == []


def test_rule_no_assigned_group_active_user():
    user = _user(accountEnabled=True, groupMemberships=[])
    findings = _Rules.no_assigned_group(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "ACC-002"
    assert findings[0].severity == Severity.INFO


def test_rule_no_assigned_group_disabled_user_no_finding():
    user = _user(accountEnabled=False, groupMemberships=[])
    assert _Rules.no_assigned_group(user) == []


def test_rule_privileged_no_dedicated_account():
    user = _user(userPrincipalName="john.doe@example.com", role="GlobalAdmin")
    findings = _Rules.privileged_no_dedicated_account(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "SEC-003"


def test_rule_privileged_with_admin_prefix_no_finding():
    user = _user(userPrincipalName="adm.john@example.com", role="GlobalAdmin")
    assert _Rules.privileged_no_dedicated_account(user) == []


# ---------------------------------------------------------------------------
# AuditEngine.load_json
# ---------------------------------------------------------------------------

def test_load_json_list():
    engine = AuditEngine()
    data = [{"userPrincipalName": "a@b.com"}]
    result = engine.load_json(io.StringIO(json.dumps(data)))
    assert result == data


def test_load_json_wrapped():
    engine = AuditEngine()
    data = {"users": [{"userPrincipalName": "a@b.com"}]}
    result = engine.load_json(io.StringIO(json.dumps(data)))
    assert result == data["users"]


def test_load_json_invalid_raises():
    engine = AuditEngine()
    with pytest.raises(ValueError):
        engine.load_json(io.StringIO('{"key": "value"}'))


def test_load_json_from_path(tmp_path):
    engine = AuditEngine()
    p = tmp_path / "users.json"
    p.write_text(json.dumps([{"userPrincipalName": "x@y.com"}]), encoding="utf-8")
    result = engine.load_json(p)
    assert result[0]["userPrincipalName"] == "x@y.com"


# ---------------------------------------------------------------------------
# AuditEngine.load_csv
# ---------------------------------------------------------------------------

def test_load_csv_basic():
    engine = AuditEngine()
    csv_text = "userPrincipalName,mfaEnabled,assignedLicenses\na@b.com,true,Microsoft365E3\n"
    result = engine.load_csv(io.StringIO(csv_text))
    assert len(result) == 1
    assert result[0]["userPrincipalName"] == "a@b.com"
    assert result[0]["assignedLicenses"] == ["Microsoft365E3"]


def test_load_csv_multi_license():
    engine = AuditEngine()
    csv_text = "userPrincipalName,assignedLicenses\na@b.com,Microsoft365E3;ExchangeOnlinePlan1\n"
    result = engine.load_csv(io.StringIO(csv_text))
    assert result[0]["assignedLicenses"] == ["Microsoft365E3", "ExchangeOnlinePlan1"]


def test_load_csv_from_path(tmp_path):
    engine = AuditEngine()
    p = tmp_path / "users.csv"
    p.write_text("userPrincipalName,mfaEnabled\nz@z.com,false\n", encoding="utf-8")
    result = engine.load_csv(p)
    assert result[0]["userPrincipalName"] == "z@z.com"


# ---------------------------------------------------------------------------
# AuditEngine.run
# ---------------------------------------------------------------------------

def test_run_clean_user_produces_findings():
    engine = AuditEngine()
    users = [_user(mfaEnabled=False)]
    report = engine.run(users)
    assert isinstance(report, AuditReport)
    rule_ids = {f.rule_id for f in report.findings}
    assert "SEC-001" in rule_ids


def test_run_empty_users():
    engine = AuditEngine()
    report = engine.run([])
    assert report.findings == []


def test_run_custom_rules():
    called = []

    def my_rule(user):
        called.append(user)
        return []

    engine = AuditEngine(rules=[my_rule])
    engine.run([_user()])
    assert len(called) == 1


# ---------------------------------------------------------------------------
# AuditReport serialisation
# ---------------------------------------------------------------------------

def test_report_to_json_structure():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    output = report.to_json()
    parsed = json.loads(output)
    assert "generated_at" in parsed
    assert "summary" in parsed
    assert "findings" in parsed
    assert isinstance(parsed["findings"], list)


def test_report_to_csv_has_header():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    output = report.to_csv()
    assert "rule_id" in output
    assert "severity" in output


def test_report_to_text_has_header():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    output = report.to_text()
    assert "M365 Support Audit Report" in output
    assert "Summary:" in output


def test_report_summary_counts():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    summary = report.summary()
    assert sum(summary.values()) == len(report.findings)
    assert all(k in summary for k in ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"))


def test_report_by_severity():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    high = report.by_severity(Severity.HIGH)
    for f in high:
        assert f.severity == Severity.HIGH


# ---------------------------------------------------------------------------
# CLI main() — application-level errors (return code via SystemExit)
# ---------------------------------------------------------------------------

def test_main_audit_missing_file_exits_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", "/nonexistent/path/users.json"])
    assert exc_info.value.code == 2


def test_main_audit_unsupported_extension(tmp_path, capsys):
    p = tmp_path / "data.txt"
    p.write_text("nothing", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", str(p)])
    assert exc_info.value.code == 2


def test_main_audit_json_success(tmp_path):
    users = [_user(mfaEnabled=True, groupMemberships=["Staff"])]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", str(p)])
    assert exc_info.value.code == 0


def test_main_audit_fail_on_triggers(tmp_path):
    users = [_user(mfaEnabled=False, role="GlobalAdmin")]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", str(p), "--fail-on=HIGH"])
    assert exc_info.value.code == 1


def test_main_audit_json_format_output(tmp_path, capsys):
    users = [_user(mfaEnabled=False)]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["audit", str(p), "--format=json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "findings" in parsed


def test_main_audit_write_to_file(tmp_path):
    users = [_user()]
    src = tmp_path / "users.json"
    src.write_text(json.dumps(users), encoding="utf-8")
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit):
        main(["audit", str(src), "--format=json", f"--output={out}"])
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert "findings" in parsed


def test_main_audit_min_severity_filters(tmp_path, capsys):
    users = [_user(mfaEnabled=False)]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["audit", str(p), "--format=json", "--min-severity=CRITICAL"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    for f in parsed["findings"]:
        assert f["severity"] == "CRITICAL"


def test_main_summary_missing_file_exits_2(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["summary", "/nonexistent/report.json"])
    assert exc_info.value.code == 2


def test_main_summary_valid_report(tmp_path, capsys):
    users = [_user(mfaEnabled=False)]
    src = tmp_path / "users.json"
    src.write_text(json.dumps(users), encoding="utf-8")
    report_path = tmp_path / "report.json"
    with pytest.raises(SystemExit):
        main(["audit", str(src), "--format=json", f"--output={report_path}"])
    with pytest.raises(SystemExit) as exc_info:
        main(["summary", str(report_path)])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Total findings" in captured.out


def test_main_summary_invalid_json(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("not valid json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["summary", str(p)])
    assert exc_info.value.code == 2
