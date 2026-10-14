"""Aggregate the CI component results into the single required check (BR5.1, NFR13.2).

The ``gate`` job in ``.github/workflows/ci.yml`` passes ``toJSON(needs)`` and the event name.
The gate fails closed (Codex review R2):

- **Inventory.** ``NEEDS_JSON`` must name exactly the jobs in ``EXPECTED_JOBS``; a missing or
  an unexpected job fails the gate. ``scripts/check_workflows.py`` checks that the gate's
  ``needs:`` list in ci.yml equals this inventory, and that every other ci.yml job is in it.
- **Change detection.** The ``changes`` job must succeed and must output, for every
  path-gated job, exactly ``"true"`` or ``"false"``. A missing, empty or malformed value
  (``"yes"``, ``""``, ``"TRUE"``) fails the gate, and the job it controls is then treated as
  required.
- **Each job** passes when it succeeded, or when it was skipped and was not required: a
  path-gated job whose output is ``"false"``, or ``review-check`` on a push event. A failed or
  cancelled job, or a required job that was skipped, fails the gate.

Each job's result is written to the job summary (``$GITHUB_STEP_SUMMARY``) when it is set.

Usage (as in CI): ``NEEDS_JSON='...' EVENT_NAME=pull_request python scripts/gate_results.py``.
Exit codes: 0 every required check passed, 1 at least one failed, 2 unreadable input.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CHANGES = "changes"
# Every job the gate needs, in ci.yml order. check_workflows.py keeps ci.yml in step.
EXPECTED_JOBS: tuple[str, ...] = (
    "changes",
    "python",
    "web",
    "guard",
    "audit",
    "slice-e2e",
    "workflow-lint",
    "review-check",
    "gitleaks",
)
# Path-gated job -> the `changes` output that says whether it had to run.
PATH_GATED: dict[str, str] = {
    "python": "python",
    "web": "web",
    "guard": "guard",
    "audit": "audit",
    "slice-e2e": "slice_e2e",
}
PULL_REQUEST_ONLY: frozenset[str] = frozenset({"review-check"})
BOOLEAN_OUTPUTS: frozenset[str] = frozenset({"true", "false"})


@dataclass(frozen=True)
class JobOutcome:
    """One needed job and how the gate judged it."""

    job: str
    result: str
    required: bool
    passed: bool
    detail: str = ""

    @property
    def status(self) -> str:
        if self.passed:
            return "ran: passed" if self.result == "success" else "skipped: not needed"
        text = self.result
        if self.required:
            text += ", required"
        if self.detail:
            text += f"; {self.detail}"
        return f"FAILED ({text})"


def _outputs(needs: Mapping[str, Any]) -> Mapping[str, Any]:
    changes = needs.get(CHANGES)
    outputs = changes.get("outputs") if isinstance(changes, Mapping) else None
    return outputs if isinstance(outputs, Mapping) else {}


def output_problems(needs: Mapping[str, Any]) -> dict[str, str]:
    """Path-gated job -> why its output is missing or not exactly "true" or "false"."""
    outputs = _outputs(needs)
    problems: dict[str, str] = {}
    for job, key in PATH_GATED.items():
        value = outputs.get(key)
        if not isinstance(value, str) or value not in BOOLEAN_OUTPUTS:
            problems[job] = f"output {key}={value!r} is not 'true' or 'false'"
    return problems


def is_required(job: str, outputs: Mapping[str, Any], event: str) -> bool:
    """Whether the job had to run for this event and these changed paths.

    A path-gated job is optional only when its output is exactly "false".
    """
    if job in PATH_GATED:
        return outputs.get(PATH_GATED[job]) != "false"
    if job in PULL_REQUEST_ONLY:
        return event != "push"
    return True


def _result(info: object) -> str:
    return str(info.get("result", "unknown")) if isinstance(info, Mapping) else "unknown"


def evaluate(needs: Mapping[str, Any], event: str) -> list[JobOutcome]:
    """Judge every expected job, plus any job the gate did not expect."""
    outputs = _outputs(needs)
    problems = output_problems(needs)
    outcomes = []
    for job in EXPECTED_JOBS:
        if job not in needs:
            outcomes.append(JobOutcome(job, "missing", True, False, "not in NEEDS_JSON"))
            continue
        result = _result(needs[job])
        required = is_required(job, outputs, event)
        passed = result == "success" or (result == "skipped" and not required)
        detail = ""
        if job == CHANGES and problems:
            passed, detail = False, "; ".join(problems.values())
        elif job in problems:
            detail = "its changes output is missing or malformed"
        outcomes.append(JobOutcome(job, result, required, passed, detail))
    for job in needs:
        if job not in EXPECTED_JOBS:
            result = _result(needs[job])
            outcomes.append(JobOutcome(job, result, True, False, "unexpected job"))
    return outcomes


def summary(outcomes: Sequence[JobOutcome]) -> str:
    rows = [f"| {o.job} | {o.status} |" for o in outcomes]
    return "\n".join(["## gate", "", "| Check | Result |", "|---|---|", *rows, ""])


def main(environ: Mapping[str, str] | None = None) -> int:
    """Read NEEDS_JSON and EVENT_NAME, write the summary, and return the exit code."""
    env = os.environ if environ is None else environ
    try:
        needs = json.loads(env.get("NEEDS_JSON", ""))
    except json.JSONDecodeError:
        print("gate: NEEDS_JSON is not valid JSON", file=sys.stderr)
        return 2
    if not isinstance(needs, dict) or not needs:
        print("gate: NEEDS_JSON names no jobs", file=sys.stderr)
        return 2
    outcomes = evaluate(needs, env.get("EVENT_NAME", ""))
    text = summary(outcomes)
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text)
    print(text)
    failed = [o.job for o in outcomes if not o.passed]
    if failed:
        print(f"gate: failing because of: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("gate: every required check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
