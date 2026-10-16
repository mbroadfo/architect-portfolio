"""Tests for scripts/gate_results.py, the single required check (AC0.10, BR5.1, NFR13.2;
Codex review R2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gate_results as gate
import pytest

PATH_GATED = ("python", "web", "guard", "audit", "slice-e2e")
ALL_SUCCESS: dict[str, Any] = {
    "changes": {
        "result": "success",
        "outputs": {
            "python": "true",
            "web": "true",
            "guard": "true",
            "audit": "true",
            "slice_e2e": "true",
        },
    },
    "python": {"result": "success"},
    "web": {"result": "success"},
    "guard": {"result": "success"},
    "audit": {"result": "success"},
    "slice-e2e": {"result": "success"},
    "workflow-lint": {"result": "success"},
    "review-check": {"result": "success"},
    "gitleaks": {"result": "success"},
}


def _needs(**overrides: Any) -> dict[str, Any]:
    needs = json.loads(json.dumps(ALL_SUCCESS))
    for job, value in overrides.items():
        needs[job.replace("_", "-")] = value
    return needs


def _run(needs: dict[str, Any], event: str = "pull_request", tmp_path: Path | None = None) -> int:
    env = {"NEEDS_JSON": json.dumps(needs), "EVENT_NAME": event}
    if tmp_path is not None:
        env["GITHUB_STEP_SUMMARY"] = str(tmp_path / "summary.md")
    return gate.main(env)


def _outcomes(needs: dict[str, Any], event: str = "pull_request") -> dict[str, gate.JobOutcome]:
    return {o.job: o for o in gate.evaluate(needs, event)}


def test_ac0_10_all_success_passes_and_writes_the_summary(tmp_path: Path) -> None:
    """AC0.10 / NFR13.2: every check ran and passed; the summary lists each one."""
    assert _run(_needs(), tmp_path=tmp_path) == 0
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| python | ran: passed |" in summary
    assert "| slice-e2e | ran: passed |" in summary
    assert "| gitleaks | ran: passed |" in summary


def test_ac0_10_skipped_path_gated_job_passes_when_its_output_is_false() -> None:
    for job in PATH_GATED:
        needs = _needs(**{job: {"result": "skipped"}})
        needs["changes"]["outputs"][gate.PATH_GATED[job]] = "false"
        outcome = _outcomes(needs)[job]
        assert outcome.passed and outcome.status == "skipped: not needed"
        assert _run(needs) == 0


def test_ac0_10_skipped_path_gated_job_fails_when_its_paths_changed() -> None:
    """A job that should have run but was skipped fails the gate."""
    assert _run(_needs(guard={"result": "skipped"})) == 1
    assert _run(_needs(slice_e2e={"result": "skipped"})) == 1


@pytest.mark.parametrize("result", ["failure", "cancelled"])
def test_ac0_10_failed_or_cancelled_jobs_fail_the_gate(result: str) -> None:
    assert _run(_needs(python={"result": result})) == 1
    assert _run(_needs(gitleaks={"result": result})) == 1
    assert _run(_needs(slice_e2e={"result": result})) == 1


def test_r2_cancelled_path_gated_job_fails_even_when_not_needed() -> None:
    needs = _needs(slice_e2e={"result": "cancelled"})
    needs["changes"]["outputs"]["slice_e2e"] = "false"
    assert not _outcomes(needs)["slice-e2e"].passed
    assert _run(needs) == 1


def test_ac0_10_failed_change_detection_fails_the_gate() -> None:
    needs = _needs(changes={"result": "failure", "outputs": {}})
    for job in PATH_GATED:
        needs[job] = {"result": "skipped"}
    outcomes = _outcomes(needs)
    assert not outcomes["changes"].passed
    assert all(not outcomes[job].passed and outcomes[job].required for job in PATH_GATED)
    assert _run(needs) == 1


def test_r2_failed_change_detection_with_valid_outputs_still_fails() -> None:
    needs = _needs()
    needs["changes"]["result"] = "failure"
    assert _run(needs) == 1


def test_r2_codex_reproduction_missing_outputs_no_longer_pass(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R2 (Codex reproduction): successful changes, workflow-lint, review-check and gitleaks,
    skipped python, web, guard and audit, and no outputs at all. Before the fix every skip
    was "not needed" and the gate passed; now it fails."""
    needs = {
        "changes": {"result": "success"},
        "workflow-lint": {"result": "success"},
        "review-check": {"result": "success"},
        "gitleaks": {"result": "success"},
        "python": {"result": "skipped"},
        "web": {"result": "skipped"},
        "guard": {"result": "skipped"},
        "audit": {"result": "skipped"},
    }
    assert _run(needs) == 1
    err = capsys.readouterr().err
    for job in ("changes", "python", "web", "guard", "audit", "slice-e2e"):
        assert job in err


def test_r2_missing_job_fails_the_gate(capsys: pytest.CaptureFixture[str]) -> None:
    needs = _needs()
    del needs["gitleaks"]
    outcome = _outcomes(needs)["gitleaks"]
    assert not outcome.passed and outcome.status == "FAILED (missing, required; not in NEEDS_JSON)"
    assert _run(needs) == 1
    assert "failing because of: gitleaks" in capsys.readouterr().err


def test_r2_unexpected_job_fails_the_gate() -> None:
    needs = _needs(extra_job={"result": "success"})
    outcome = _outcomes(needs)["extra-job"]
    assert not outcome.passed and "unexpected job" in outcome.status
    assert _run(needs) == 1


def test_r2_missing_outputs_fail_the_gate_even_when_every_job_succeeded() -> None:
    needs = _needs()
    del needs["changes"]["outputs"]
    outcome = _outcomes(needs)["changes"]
    assert not outcome.passed and "output python=None" in outcome.status
    assert _run(needs) == 1
    needs["changes"]["outputs"] = "not a mapping"
    assert _run(needs) == 1


def test_r2_one_missing_output_marks_its_job_required() -> None:
    needs = _needs(slice_e2e={"result": "skipped"})
    del needs["changes"]["outputs"]["slice_e2e"]
    outcomes = _outcomes(needs)
    assert not outcomes["changes"].passed
    assert outcomes["slice-e2e"].required and not outcomes["slice-e2e"].passed
    assert "its changes output is missing or malformed" in outcomes["slice-e2e"].status
    assert _run(needs) == 1


@pytest.mark.parametrize("value", ["yes", "", "TRUE", "False", " true", "1", None, True, 1])
def test_r2_malformed_booleans_fail_the_gate(value: object) -> None:
    needs = _needs(web={"result": "skipped"})
    needs["changes"]["outputs"]["web"] = value
    outcomes = _outcomes(needs)
    assert not outcomes["changes"].passed
    assert outcomes["web"].required and not outcomes["web"].passed
    assert _run(needs) == 1


@pytest.mark.parametrize("job", ["workflow-lint", "gitleaks", "changes"])
def test_r2_skipped_always_required_job_fails(job: str) -> None:
    assert _run(_needs(**{job.replace("-", "_"): {"result": "skipped"}}), event="push") == 1


def test_ac0_10_review_check_skip_is_allowed_only_on_push(
    capsys: pytest.CaptureFixture[str],
) -> None:
    needs = _needs(review_check={"result": "skipped"})
    assert _run(needs, event="push") == 0
    assert _run(needs, event="pull_request") == 1
    assert "failing because of: review-check" in capsys.readouterr().err
    assert _run(needs, event="workflow_dispatch") == 1, "an unknown event fails closed"


def test_r2_push_and_pull_request_judge_path_gated_jobs_the_same() -> None:
    for event in ("push", "pull_request"):
        needs = _needs(audit={"result": "skipped"})
        assert _run(needs, event=event) == 1
        needs["changes"]["outputs"]["audit"] = "false"
        assert _run(needs, event=event) == 0


@pytest.mark.parametrize("raw", ["not json", "[]", "{}"])
def test_unreadable_input_is_a_usage_error(raw: str) -> None:
    assert gate.main({"NEEDS_JSON": raw, "EVENT_NAME": "push"}) == 2


def test_status_text_for_a_required_failure() -> None:
    outcome = gate.JobOutcome("python", "failure", required=True, passed=False)
    assert outcome.status == "FAILED (failure, required)"
    assert (
        gate.JobOutcome("x", "cancelled", required=False, passed=False).status
        == "FAILED (cancelled)"
    )


def test_inventory_and_path_gated_outputs_agree() -> None:
    assert set(gate.PATH_GATED) <= set(gate.EXPECTED_JOBS)
    assert gate.PATH_GATED["slice-e2e"] == "slice_e2e"
    assert len(gate.EXPECTED_JOBS) == len(set(gate.EXPECTED_JOBS))
