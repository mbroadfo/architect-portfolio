"""Workflow security lint (NFR13.6).

Fails when a GitHub Actions workflow:

- has no top-level ``permissions:`` (least privilege must be declared explicitly), uses
  ``write-all`` or ``read-all`` at any level, or grants any scope other than
  ``contents: read``, except the job scopes listed in ``JOB_PERMISSIONS`` (the CodeQL job's
  ``security-events: write`` and ``actions: read``) (security re-review S0-5);
- uses an action that is not pinned to a full 40-character commit SHA
  (local ``./`` actions and ``docker://`` images pinned by ``@sha256:`` digest are allowed);
- checks out code without ``persist-credentials: false``;
- is triggered by ``pull_request_target``.

For the CI workflow (``ci.yml``) it also checks the required ``gate`` job against
``scripts/gate_results.py`` (Codex review R2): the gate's ``needs:`` list must equal the
evaluator's inventory, every other job must be in it, the ``changes`` job must declare an
output for every path-gated job, and each path-gated job's ``if:`` must be exactly
``needs.changes.outputs.<x> == 'true'`` (so ``... || always()`` fails).

Usage: ``python scripts/check_workflows.py [workflow files or directories]``
(default: ``.github/workflows``). Exit codes: 0 compliant, 1 violations, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import gate_results
import yaml

PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
PINNED_DOCKER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
DEFAULT_WORKFLOW_DIR = Path(".github") / "workflows"
CI_WORKFLOW = "ci.yml"
GATE_JOB = "gate"
CHECKOUT_ACTION = "actions/checkout@"
# Least privilege (security re-review S0-5): the only scope any workflow or job may grant...
DEFAULT_PERMISSIONS: dict[str, str] = {"contents": "read"}
# ...except these jobs, keyed by (workflow file, job id), which get exactly these scopes.
JOB_PERMISSIONS: dict[tuple[str, str], dict[str, str]] = {
    ("codeql.yml", "analyze"): {
        "contents": "read",
        "security-events": "write",
        "actions": "read",
    },
}


def _triggers(document: dict[Any, Any]) -> set[str]:
    # YAML 1.1 parses a bare ``on`` key as the boolean True.
    raw = document.get("on", document.get(True))
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    return set()


def _iter_uses(document: dict[Any, Any]) -> Iterator[tuple[str, str]]:
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            yield f"jobs.{job_id}", job["uses"]
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if isinstance(step, dict) and isinstance(step.get("uses"), str):
                yield f"jobs.{job_id}.steps[{index}]", step["uses"]


def is_pinned(uses: str) -> bool:
    """Return True when an action reference is local, SHA-pinned or digest-pinned."""
    reference = uses.strip()
    if reference.startswith("./"):
        return True
    if reference.startswith("docker://"):
        return bool(PINNED_DOCKER.match(reference))
    return bool(PINNED_ACTION.match(reference))


def _checkout_violations(name: str, document: dict[Any, Any]) -> list[str]:
    jobs = document.get("jobs")
    violations: list[str] = []
    for job_id, job in (jobs or {}).items() if isinstance(jobs, dict) else ():
        steps = job.get("steps") if isinstance(job, dict) else None
        for index, step in enumerate(steps if isinstance(steps, list) else []):
            uses = step.get("uses") if isinstance(step, dict) else None
            if not isinstance(uses, str) or not uses.startswith(CHECKOUT_ACTION):
                continue
            options = step.get("with")
            if not isinstance(options, dict) or options.get("persist-credentials") is not False:
                violations.append(
                    f"{name}: jobs.{job_id}.steps[{index}] checks out without "
                    "'persist-credentials: false'"
                )
    return violations


def _needs(job: object) -> list[str]:
    raw = job.get("needs") if isinstance(job, dict) else None
    if isinstance(raw, str):
        return [raw]
    return [str(item) for item in raw] if isinstance(raw, list) else []


def check_gate(name: str, document: dict[Any, Any]) -> list[str]:
    """R2: the gate job, its inventory and the path-gated outputs agree with gate_results."""
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or GATE_JOB not in jobs:
        return [f"{name}: has no '{GATE_JOB}' job, the single required check"]
    needs = _needs(jobs[GATE_JOB])
    expected = list(gate_results.EXPECTED_JOBS)
    violations: list[str] = []
    if sorted(needs) != sorted(expected) or len(needs) != len(set(needs)):
        violations.append(
            f"{name}: jobs.gate.needs {needs} differs from scripts/gate_results.py "
            f"EXPECTED_JOBS {expected}"
        )
    for job_id in jobs:
        if job_id != GATE_JOB and job_id not in needs:
            violations.append(f"{name}: job '{job_id}' is not in jobs.gate.needs")
    changes = jobs.get(gate_results.CHANGES)
    outputs = changes.get("outputs") if isinstance(changes, dict) else None
    for job_id, key in gate_results.PATH_GATED.items():
        if not isinstance(outputs, dict) or key not in outputs:
            violations.append(f"{name}: the changes job declares no output '{key}' for {job_id}")
        job = jobs.get(job_id)
        condition = job.get("if") if isinstance(job, dict) else None
        wanted = f"needs.changes.outputs.{key} == 'true'"
        # Exact match (S0-5): `... || always()` or any other addition fails.
        if not isinstance(condition, str) or condition.strip() != wanted:
            violations.append(f"{name}: job '{job_id}' must run only if exactly {wanted}")
    return violations


def _permission_violations(
    name: str, where: str, value: object, allowed: dict[str, str]
) -> list[str]:
    """Each entry of a ``permissions:`` block must be in ``allowed`` with exactly that value."""
    if isinstance(value, str):
        return [f"{name}: {where} is '{value}'; declare individual scopes instead"]
    if not isinstance(value, dict):
        return [f"{name}: {where} must be a mapping of scopes"]
    return [
        f"{name}: {where}.{scope}: {access} is not allowed"
        for scope, access in value.items()
        if allowed.get(str(scope)) != access
    ]


def permissions_violations(name: str, document: dict[Any, Any]) -> list[str]:
    """S0-5: least privilege at every level.

    The top level may grant only ``contents: read``. A job may grant only ``contents: read``,
    except the jobs in ``JOB_PERMISSIONS``, keyed by workflow file and job. ``write-all`` and
    ``read-all`` (or any other string) fail at any level.
    """
    workflow = Path(name).name
    violations: list[str] = []
    if "permissions" not in document:
        violations.append(f"{name}: missing top-level 'permissions:'")
    else:
        violations += _permission_violations(
            name, "permissions", document["permissions"], DEFAULT_PERMISSIONS
        )
    jobs = document.get("jobs")
    for job_id, job in (jobs or {}).items() if isinstance(jobs, dict) else ():
        if isinstance(job, dict) and "permissions" in job:
            allowed = JOB_PERMISSIONS.get((workflow, str(job_id)), DEFAULT_PERMISSIONS)
            violations += _permission_violations(
                name, f"jobs.{job_id}.permissions", job["permissions"], allowed
            )
    return violations


def check_document(name: str, document: object) -> list[str]:
    """Return the violations found in one parsed workflow document."""
    if not isinstance(document, dict):
        return [f"{name}: not a workflow mapping"]
    violations: list[str] = permissions_violations(name, document)
    if "pull_request_target" in _triggers(document):
        violations.append(f"{name}: uses the forbidden 'pull_request_target' trigger")
    for where, uses in _iter_uses(document):
        if not is_pinned(uses):
            violations.append(f"{name}: {where} uses '{uses}', not pinned to a full commit SHA")
    violations.extend(_checkout_violations(name, document))
    return violations


def check_file(path: Path) -> list[str]:
    """Parse and check one workflow file (ci.yml also gets the gate checks)."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return [f"{path}: cannot be read as YAML ({error})"]
    violations = check_document(str(path), document)
    if path.name == CI_WORKFLOW and isinstance(document, dict):
        violations.extend(check_gate(str(path), document))
    return violations


def collect_files(targets: Sequence[str]) -> list[Path]:
    """Expand directories into their workflow files."""
    paths = [Path(target) for target in targets] or [DEFAULT_WORKFLOW_DIR]
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted([*path.glob("*.yml"), *path.glob("*.yaml")]))
        elif path.is_file():
            files.append(path)
    return files


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Workflow security lint (NFR13.6).")
    parser.add_argument("targets", nargs="*", help="workflow files or directories")
    args = parser.parse_args(argv)
    files = collect_files(args.targets)
    if not files:
        print("check_workflows: FAIL - no workflow files found", file=sys.stderr)
        return 2
    violations = [violation for path in files for violation in check_file(path)]
    if violations:
        print(f"check_workflows: FAIL - {len(violations)} violation(s):", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1
    print(f"check_workflows: OK - {len(files)} workflow file(s) compliant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
