"""Tests for scripts/check_workflows.py (NFR13.6; Codex review R2 and R4)."""

from __future__ import annotations

from pathlib import Path

import check_workflows as lint
import gate_results
import pytest
import yaml
from conftest import REPO_ROOT

SHA = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "sha256:" + "a" * 64

COMPLIANT = f"""
name: ci
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@{SHA} # v4
        with:
          persist-credentials: false
      - uses: ./.github/actions/local
      - uses: docker://alpine@{DIGEST}
      - run: echo ok
"""


def _workflow(tmp_path: Path, text: str, name: str = "wf.yml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _ci(**changes: object) -> str:
    """A minimal ci.yml whose gate matches scripts/gate_results.py, then ``changes`` applied."""
    jobs: dict[str, object] = {
        "changes": {
            "runs-on": "ubuntu-24.04",
            "outputs": {key: "x" for key in gate_results.PATH_GATED.values()},
            "steps": [{"run": "echo"}],
        }
    }
    for job in gate_results.EXPECTED_JOBS:
        if job == "changes":
            continue
        body: dict[str, object] = {"runs-on": "ubuntu-24.04", "steps": [{"run": "echo"}]}
        if job in gate_results.PATH_GATED:
            body["needs"] = "changes"
            body["if"] = f"needs.changes.outputs.{gate_results.PATH_GATED[job]} == 'true'"
        jobs[job] = body
    jobs["gate"] = {
        "if": "always()",
        "needs": list(gate_results.EXPECTED_JOBS),
        "runs-on": "ubuntu-24.04",
        "steps": [{"run": "python3 scripts/gate_results.py"}],
    }
    for key, value in changes.items():
        jobs[key.replace("_", "-")] = value
    document = {"name": "ci", "on": {"push": None}, "permissions": {"contents": "read"}}
    document["jobs"] = {k: v for k, v in jobs.items() if v is not None}
    return yaml.safe_dump(document, sort_keys=False)


def test_compliant_workflow_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """NFR13.6: permissions declared, actions SHA-pinned, no pull_request_target."""
    assert lint.main([str(_workflow(tmp_path, COMPLIANT))]) == 0
    assert "1 workflow file(s) compliant" in capsys.readouterr().out


def test_missing_permissions_fails(tmp_path: Path) -> None:
    text = COMPLIANT.replace("permissions:\n  contents: read\n", "")
    violations = lint.check_file(_workflow(tmp_path, text))
    assert violations == [f"{tmp_path / 'wf.yml'}: missing top-level 'permissions:'"]


def test_unpinned_action_fails(tmp_path: Path) -> None:
    text = COMPLIANT.replace(f"actions/checkout@{SHA}", "actions/checkout@v4")
    violations = lint.check_file(_workflow(tmp_path, text))
    assert len(violations) == 1
    assert "not pinned to a full commit SHA" in violations[0]


def test_short_sha_and_docker_tag_fail(tmp_path: Path) -> None:
    text = COMPLIANT.replace(SHA, SHA[:12]).replace(f"alpine@{DIGEST}", "alpine:3")
    assert len(lint.check_file(_workflow(tmp_path, text))) == 2


@pytest.mark.parametrize(
    "replacement",
    ["persist-credentials: true", "fetch-depth: 0"],
)
def test_r4_checkout_must_not_persist_credentials(tmp_path: Path, replacement: str) -> None:
    text = COMPLIANT.replace("persist-credentials: false", replacement)
    violations = lint.check_file(_workflow(tmp_path, text))
    assert violations == [
        f"{tmp_path / 'wf.yml'}: jobs.build.steps[0] checks out without "
        "'persist-credentials: false'"
    ]


@pytest.mark.parametrize(
    "trigger",
    [
        "pull_request_target",
        "[push, pull_request_target]",
        "\n  pull_request_target:\n    types: [opened]",
    ],
)
def test_pull_request_target_fails(tmp_path: Path, trigger: str) -> None:
    text = COMPLIANT.replace("on:\n  pull_request:\n    branches: [main]", f"on: {trigger}")
    violations = lint.check_file(_workflow(tmp_path, text))
    assert any("pull_request_target" in v for v in violations)


def test_reusable_workflow_reference_is_checked(tmp_path: Path) -> None:
    text = """
on: push
permissions: {}
jobs:
  call:
    uses: owner/repo/.github/workflows/x.yml@main
"""
    violations = lint.check_file(_workflow(tmp_path, text))
    assert len(violations) == 1
    assert "jobs.call" in violations[0]


def test_invalid_yaml_and_non_mapping_fail(tmp_path: Path) -> None:
    assert (
        "cannot be read as YAML"
        in lint.check_file(_workflow(tmp_path, "a: [unclosed", "bad.yml"))[0]
    )
    assert lint.check_file(_workflow(tmp_path, "- just a list\n", "list.yml")) == [
        f"{tmp_path / 'list.yml'}: not a workflow mapping"
    ]


def test_directory_target_and_failure_exit_code(tmp_path: Path) -> None:
    _workflow(tmp_path, COMPLIANT, "good.yml")
    _workflow(tmp_path, COMPLIANT.replace(f"@{SHA}", "@v4"), "bad.yaml")
    assert lint.main([str(tmp_path)]) == 1


def test_no_workflow_files_is_a_usage_error(tmp_path: Path) -> None:
    assert lint.main([str(tmp_path / "missing")]) == 2


def test_repository_workflows_are_compliant() -> None:
    """The repository's own workflows pass the lint, including the gate checks (Step 6)."""
    workflows = REPO_ROOT / ".github" / "workflows"
    assert lint.main([str(workflows)]) == 0


# --- R2: the gate inventory in ci.yml equals gate_results.EXPECTED_JOBS ---------------------


def test_r2_a_consistent_ci_gate_passes(tmp_path: Path) -> None:
    assert lint.check_file(_workflow(tmp_path, _ci(), "ci.yml")) == []


def test_r2_the_repository_gate_needs_every_job_and_slice_e2e() -> None:
    document = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    assert lint.check_gate("ci.yml", document) == []
    assert "slice-e2e" in document["jobs"]["gate"]["needs"]
    job = document["jobs"]["slice-e2e"]
    assert job["permissions"] == {"contents": "read"}
    assert job["runs-on"] == "ubuntu-24.04"
    assert "slice_e2e" in document["jobs"]["changes"]["outputs"]


def test_r2_a_job_missing_from_the_gate_needs_fails(tmp_path: Path) -> None:
    gate = {
        "needs": [j for j in gate_results.EXPECTED_JOBS if j != "gitleaks"],
        "runs-on": "x",
        "steps": [{"run": "x"}],
    }
    violations = lint.check_file(_workflow(tmp_path, _ci(gate=gate), "ci.yml"))
    assert any("differs from scripts/gate_results.py EXPECTED_JOBS" in v for v in violations)
    assert any("job 'gitleaks' is not in jobs.gate.needs" in v for v in violations)


def test_r2_a_job_outside_the_inventory_fails(tmp_path: Path) -> None:
    extra = {"runs-on": "x", "steps": [{"run": "x"}]}
    violations = lint.check_file(_workflow(tmp_path, _ci(new_job=extra), "ci.yml"))
    assert violations == [f"{tmp_path / 'ci.yml'}: job 'new-job' is not in jobs.gate.needs"]


def test_r2_a_gate_needing_an_unknown_job_fails(tmp_path: Path) -> None:
    gate = {"needs": [*gate_results.EXPECTED_JOBS, "ghost"], "runs-on": "x", "steps": []}
    violations = lint.check_file(_workflow(tmp_path, _ci(gate=gate), "ci.yml"))
    assert len(violations) == 1 and "differs from" in violations[0]


def test_r2_missing_output_and_wrong_condition_fail(tmp_path: Path) -> None:
    changes = {"runs-on": "x", "outputs": {"python": "x"}, "steps": [{"run": "x"}]}
    slice_job = {"needs": "changes", "if": "always()", "runs-on": "x", "steps": [{"run": "x"}]}
    text = _ci(changes=changes, slice_e2e=slice_job)
    violations = " | ".join(lint.check_file(_workflow(tmp_path, text, "ci.yml")))
    assert "declares no output 'slice_e2e' for slice-e2e" in violations
    assert "declares no output 'web' for web" in violations
    assert (
        "job 'slice-e2e' must run only if exactly needs.changes.outputs.slice_e2e == 'true'"
        in violations
    )


def test_r2_ci_without_a_gate_fails(tmp_path: Path) -> None:
    violations = lint.check_file(_workflow(tmp_path, COMPLIANT, "ci.yml"))
    assert violations == [f"{tmp_path / 'ci.yml'}: has no 'gate' job, the single required check"]


def test_r2_gate_needs_as_a_single_string_is_read(tmp_path: Path) -> None:
    gate = {"needs": "changes", "runs-on": "x", "steps": []}
    violations = lint.check_file(_workflow(tmp_path, _ci(gate=gate), "ci.yml"))
    assert any("jobs.gate.needs ['changes'] differs" in v for v in violations)


# --- S0-5: least-privilege permissions and exact path-gated conditions -----------------------


@pytest.mark.parametrize(
    "condition",
    [
        "needs.changes.outputs.slice_e2e == 'true' || always()",
        "always() || needs.changes.outputs.slice_e2e == 'true'",
        "${{ needs.changes.outputs.slice_e2e == 'true' }} || true",
        "needs.changes.outputs.slice_e2e != 'false'",
    ],
)
def test_s0_5_a_path_gated_condition_must_match_exactly(tmp_path: Path, condition: str) -> None:
    job = {"needs": "changes", "if": condition, "runs-on": "x", "steps": [{"run": "x"}]}
    violations = lint.check_file(_workflow(tmp_path, _ci(slice_e2e=job), "ci.yml"))
    assert violations == [
        f"{tmp_path / 'ci.yml'}: job 'slice-e2e' must run only if exactly "
        "needs.changes.outputs.slice_e2e == 'true'"
    ]


@pytest.mark.parametrize("level", ["top", "job"])
@pytest.mark.parametrize("value", ["write-all", "read-all"])
def test_s0_5_write_all_and_read_all_fail_at_any_level(
    tmp_path: Path, level: str, value: str
) -> None:
    if level == "top":
        text = COMPLIANT.replace("permissions:\n  contents: read\n", f"permissions: {value}\n")
    else:
        text = COMPLIANT.replace("    runs-on:", f"    permissions: {value}\n    runs-on:")
    violations = lint.check_file(_workflow(tmp_path, text))
    assert len(violations) == 1 and f"is '{value}'" in violations[0]


@pytest.mark.parametrize(
    "block",
    [
        "contents: write",
        "pull-requests: write",
        "id-token: write",
        "security-events: write",
        "actions: read",
    ],
)
def test_s0_5_a_job_may_only_read_contents(tmp_path: Path, block: str) -> None:
    text = COMPLIANT.replace("    runs-on:", f"    permissions:\n      {block}\n    runs-on:")
    violations = lint.check_file(_workflow(tmp_path, text))
    assert violations == [
        f"{tmp_path / 'wf.yml'}: jobs.build.permissions.{block.replace(': ', ': ', 1)} "
        "is not allowed"
    ]


def test_s0_5_the_top_level_may_only_read_contents(tmp_path: Path) -> None:
    text = COMPLIANT.replace("  contents: read\n", "  contents: read\n  issues: write\n", 1)
    assert lint.check_file(_workflow(tmp_path, text)) == [
        f"{tmp_path / 'wf.yml'}: permissions.issues: write is not allowed"
    ]
    text = COMPLIANT.replace("permissions:\n  contents: read\n", "permissions: [contents]\n")
    assert "must be a mapping of scopes" in lint.check_file(_workflow(tmp_path, text))[0]


def test_s0_5_only_the_codeql_analyze_job_gets_its_extra_scopes(tmp_path: Path) -> None:
    job_block = (
        "    permissions:\n      contents: read\n      security-events: write\n"
        "      actions: read\n    runs-on:"
    )
    text = COMPLIANT.replace("    runs-on:", job_block).replace("  build:", "  analyze:")
    assert lint.check_file(_workflow(tmp_path, text, "codeql.yml")) == []
    assert len(lint.check_file(_workflow(tmp_path, text, "other.yml"))) == 2
    renamed = text.replace("  analyze:", "  build:")
    assert len(lint.check_file(_workflow(tmp_path, renamed, "codeql.yml"))) == 2
    extra = text.replace("      actions: read\n", "      actions: write\n")
    assert len(lint.check_file(_workflow(tmp_path, extra, "codeql.yml"))) == 1
