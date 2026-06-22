# Testing Guide

## Running Tests

### Quick Test Run

```bash
pytest tests/
```

Output:

```
tests/test_auditor.py::test_build_parser_constructs PASSED
tests/test_auditor.py::test_build_parser_audit_defaults PASSED
tests/test_auditor.py::test_parse_bool PASSED
...
======================== 80 passed in 0.42s ========================
```

### With Coverage Report

```bash
pip install pytest-cov
pytest --cov=m365_auditor --cov-report=html tests/
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Verbose Output

```bash
pytest -v tests/
```

Shows the name and result of each test.

### Run Specific Test

```bash
# Test a single function
pytest tests/test_auditor.py::test_rule_mfa_not_enabled_critical_for_admin

# Test a class or module
pytest tests/test_auditor.py::test_parse_bool -v
```

### Run Tests Matching a Pattern

```bash
# Test all rules
pytest tests/test_auditor.py -k "rule_" -v

# Test all CLI tests
pytest tests/test_auditor.py -k "main_" -v
```

## Test Categories

### 1. Parser Tests

Test command-line argument parsing.

**File:** `tests/test_auditor.py::test_build_parser_*`

Coverage:

- Parser construction
- `audit` subcommand with all flag combinations
- `summary` subcommand
- Argument defaults
- Invalid argument rejection
- Exit code handling

Example:

```python
def test_build_parser_audit_defaults():
    parser = build_parser()
    args = parser.parse_args(["audit", "data.json"])
    assert args.command == "audit"
    assert args.output_format == "text"
    assert args.min_severity == "INFO"
```

### 2. Helper Function Tests

Test utility functions.

**File:** `tests/test_auditor.py::test_parse_bool_*` and `test_days_since_*`

Coverage:

- `_parse_bool()` with boolean, string, and edge cases
- `_days_since()` with valid/invalid date formats
- Date math correctness

Example:

```python
@pytest.mark.parametrize("value,expected", [
    (True, True),
    ("true", True),
    ("yes", True),
    (False, False),
    ("disabled", False),
])
def test_parse_bool(value, expected):
    assert _parse_bool(value) is expected
```

### 3. Rule Tests

Test each audit rule for correctness and edge cases.

**File:** `tests/test_auditor.py::test_rule_*`

Rules tested:

| Rule | Tests | Examples |
|------|-------|----------|
| `mfa_not_enabled` | Severity varies by role | HIGH for users, CRITICAL for admins |
| `account_disabled_with_license` | Triggers only if disabled + licensed | No finding if no license |
| `unrecognised_license` | Detects unknown SKUs | Valid SKUs produce no finding |
| `password_never_expires_privileged` | Privileged only | Non-privileged users ignored |
| `stale_account` | 90/180 day thresholds | No finding if no sign-in date |
| `no_assigned_group` | Active users only | Disabled users ignored |
| `privileged_no_dedicated_account` | Admin naming convention | `adm.*`, `admin.*`, `svc.*`, `priv.*` allowed |

Example rule test:

```python
def test_rule_mfa_not_enabled_critical_for_admin():
    user = _user(mfaEnabled=False, role="GlobalAdmin")
    findings = _Rules.mfa_not_enabled(user)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].rule_id == "SEC-001"
```

### 4. Engine Tests

Test input loading, report generation, and filtering.

**File:** `tests/test_auditor.py::test_load_json_*`, `test_load_csv_*`, `test_run_*`

Coverage:

- JSON parsing (array, wrapped)
- CSV parsing (basic, multi-value fields)
- File I/O and error handling
- Report generation with multiple users
- Custom rule injection

Example:

```python
def test_load_json_wrapped():
    engine = AuditEngine()
    data = {"users": [{"userPrincipalName": "a@b.com"}]}
    result = engine.load_json(io.StringIO(json.dumps(data)))
    assert result == data["users"]

def test_load_csv_multi_license():
    engine = AuditEngine()
    csv_text = "userPrincipalName,assignedLicenses\na@b.com,Microsoft365E3;ExchangeOnlinePlan1\n"
    result = engine.load_csv(io.StringIO(csv_text))
    assert result[0]["assignedLicenses"] == ["Microsoft365E3", "ExchangeOnlinePlan1"]
```

### 5. Report Serialization Tests

Test output formatting (JSON, CSV, text).

**File:** `tests/test_auditor.py::test_report_*`

Coverage:

- JSON structure and encoding
- CSV formatting and headers
- Text formatting and readability
- Summary aggregation
- Filtering by severity

Example:

```python
def test_report_to_json_structure():
    engine = AuditEngine()
    report = engine.run([_user(mfaEnabled=False)])
    output = report.to_json()
    parsed = json.loads(output)
    assert "generated_at" in parsed
    assert "summary" in parsed
    assert "findings" in parsed
```

### 6. CLI Integration Tests

Test end-to-end CLI workflows.

**File:** `tests/test_auditor.py::test_main_*`

Coverage:

- File not found errors
- Invalid file formats
- Successful audit and exit codes
- JSON/CSV/text output
- `--fail-on` threshold behavior
- `--min-severity` filtering
- `--output` file writing
- `summary` subcommand

Example:

```python
def test_main_audit_fail_on_triggers(tmp_path):
    users = [_user(mfaEnabled=False, role="GlobalAdmin")]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", str(p), "--fail-on=HIGH"])
    assert exc_info.value.code == 1
```

## Test Data

All tests use synthetic sample data via the `_user()` helper:

```python
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
```

Create test users by overriding fields:

```python
# Disabled account with license
user = _user(accountEnabled=False, assignedLicenses=["Microsoft365E3"])

# Admin with no MFA
user = _user(mfaEnabled=False, role="GlobalAdmin")

# Stale account
user = _user(lastSignInDateTime="2020-01-01T00:00:00")
```

## Coverage Report

The test suite aims for >95% code coverage. Generate a report:

```bash
pytest --cov=m365_auditor --cov-report=term-missing tests/
```

Output shows uncovered lines:

```
m365_auditor/auditor.py
  189    if days is None:
  221    elif days >= 90:
  ...

TOTAL   255    2    99%
```

## Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e . pytest pytest-cov
      - run: pytest --cov=m365_auditor tests/
      - uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Template

```python
def test_my_new_feature():
    # Arrange: Set up test data
    user = _user(someField="someValue")
    
    # Act: Execute the function
    result = some_function(user)
    
    # Assert: Verify the result
    assert result == expected_value
```

### Testing a New Rule

```python
def test_rule_my_new_rule_triggers():
    user = _user(badCondition=True)
    findings = _Rules.my_new_rule(user)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-ID"
    assert findings[0].severity == Severity.MEDIUM

def test_rule_my_new_rule_no_finding():
    user = _user(goodCondition=True)
    findings = _Rules.my_new_rule(user)
    assert findings == []
```

### Testing CLI

```python
def test_main_my_new_flag(tmp_path, capsys):
    # Create test data
    users = [_user(someField="value")]
    p = tmp_path / "data.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    
    # Run CLI with new flag
    with pytest.raises(SystemExit) as exc_info:
        main(["audit", str(p), "--my-new-flag=value"])
    
    # Verify
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "expected output" in captured.out
```

## Debugging Tests

### Run with Print Output

```bash
pytest -s tests/test_auditor.py::test_specific_test
```

The `-s` flag shows `print()` output.

### Run with Debugger

```bash
pytest --pdb tests/test_auditor.py::test_specific_test
```

Stops at the first failure and opens the Python debugger.

### Inspect Test Data

```python
def test_inspect():
    user = _user(mfaEnabled=False)
    print(user)  # View the test user structure
```

Run with `-s`:

```bash
pytest -s tests/test_auditor.py::test_inspect
```
