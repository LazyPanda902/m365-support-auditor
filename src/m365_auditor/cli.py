"""CLI entry point for m365-auditor."""

from __future__ import annotations

import argparse
import pathlib
import sys

from m365_auditor.auditor import AuditEngine, Severity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m365-auditor",
        description="Audit M365 user accounts for security, license, and compliance issues.",
    )
    parser.add_argument("--version", action="version", version="m365-auditor 0.1.0")

    sub = parser.add_subparsers(dest="command", required=True)

    # --- audit subcommand ---
    audit_p = sub.add_parser("audit", help="Run security and compliance audit on user data.")
    audit_p.add_argument(
        "input",
        metavar="FILE",
        type=pathlib.Path,
        help="Path to user data file (.json or .csv).",
    )
    audit_p.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    audit_p.add_argument(
        "--output",
        metavar="FILE",
        type=pathlib.Path,
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    audit_p.add_argument(
        "--min-severity",
        choices=["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="INFO",
        dest="min_severity",
        help="Only report findings at or above this severity (default: INFO).",
    )
    audit_p.add_argument(
        "--fail-on",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default=None,
        dest="fail_on",
        metavar="SEVERITY",
        help="Exit with code 1 if any finding meets or exceeds SEVERITY.",
    )

    # --- summary subcommand ---
    summary_p = sub.add_parser("summary", help="Print a finding count summary from a report file.")
    summary_p.add_argument(
        "report",
        metavar="REPORT",
        type=pathlib.Path,
        help="Path to a JSON report previously produced by 'audit --format json'.",
    )

    return parser


def _run_audit(args: argparse.Namespace) -> int:
    path: pathlib.Path = args.input
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    engine = AuditEngine()
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            users = engine.load_json(path)
        elif suffix == ".csv":
            users = engine.load_csv(path)
        else:
            print(f"error: unsupported file type {suffix!r}. Use .json or .csv.", file=sys.stderr)
            return 2
    except (ValueError, OSError) as exc:
        print(f"error: failed to load {path}: {exc}", file=sys.stderr)
        return 2

    report = engine.run(users)

    # filter by severity
    min_rank = {s.value: i for i, s in enumerate(Severity)}[args.min_severity]
    report.findings = [
        f for f in report.findings
        if {s.value: i for i, s in enumerate(Severity)}[f.severity.value] >= min_rank
    ]

    # render
    fmt = args.output_format
    if fmt == "json":
        rendered = report.to_json()
    elif fmt == "csv":
        rendered = report.to_csv()
    else:
        rendered = report.to_text()

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(rendered)

    # exit code
    if args.fail_on:
        threshold = {s.value: i for i, s in enumerate(Severity)}[args.fail_on]
        sev_rank = {s.value: i for i, s in enumerate(Severity)}
        if any(sev_rank[f.severity.value] >= threshold for f in report.findings):
            return 1

    return 0


def _run_summary(args: argparse.Namespace) -> int:
    import json as _json

    path: pathlib.Path = args.report
    if not path.exists():
        print(f"error: report file not found: {path}", file=sys.stderr)
        return 2

    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        print(f"error: could not read report: {exc}", file=sys.stderr)
        return 2

    generated_at = data.get("generated_at", "unknown")
    summary: dict[str, int] = data.get("summary", {})
    total = sum(summary.values())

    print(f"Report: {path}")
    print(f"Generated: {generated_at}")
    print(f"Total findings: {total}")
    print()
    for sev, count in summary.items():
        if count:
            print(f"  {sev:<8} {count}")

    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "audit":
        code = _run_audit(args)
    elif args.command == "summary":
        code = _run_summary(args)
    else:
        parser.print_help()
        code = 2

    sys.exit(code)


if __name__ == "__main__":
    main()
