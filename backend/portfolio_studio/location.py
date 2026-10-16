"""Where the private content repository may live (ADR-013 security and compliance).

Private content never enters the public code repository. The Studio refuses a content
directory that:

- is inside the code repository (any of its work trees);
- is inside any other Git work tree, including a separate clone of the public repository,
  even when the content directory is a Git repository of its own (a nested repository);
- has a remote, or sits inside a repository with a remote, that names
  ``mbroadfo/architect-portfolio`` on any host, in any URL form (HTTPS, SSH, an SSH host
  alias) or after Git's ``insteadOf`` rewriting (security review LS-1).
"""

from __future__ import annotations

import re
from pathlib import Path

from portfolio_studio.errors import ContentLocationError
from portfolio_studio.gitrepo import run_git, toplevel

# The public repository's path on any host and in any URL form: https://host/..., ssh://...,
# git@alias:..., or a local path ending in it.
PUBLIC_CODE_REPOSITORY = re.compile(r"(^|[/:])mbroadfo/+architect-portfolio(\.git)?/*$", re.I)
DEFAULT_CONTENT_NAME = "architect-portfolio-content"


def code_root() -> Path:
    """The code repository work tree this package runs from (backend/portfolio_studio/..)."""
    return Path(__file__).resolve().parents[2]


def code_roots() -> set[Path]:
    """Every work tree of the code repository: this one and the main checkout."""
    root = code_root()
    roots = {root}
    completed = run_git(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"], False)
    if completed.returncode == 0:
        common = Path(completed.stdout.strip()).resolve()
        if common.name == ".git":
            roots.add(common.parent)
    listed = run_git(root, ["worktree", "list", "--porcelain"], check=False)
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            roots.add(Path(line.removeprefix("worktree ")).resolve())
    return roots


def default_content_dir() -> Path:
    """``<parent of the main checkout>/architect-portfolio-content``."""
    main_checkout = min(code_roots(), key=lambda p: len(p.parts))
    return main_checkout.parent / DEFAULT_CONTENT_NAME


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def check_outside_code(path: Path, what: str) -> Path:
    """Refuse ``path`` when it is inside a work tree of the public code repository."""
    resolved = path.resolve()
    for root in code_roots():
        if is_within(resolved, root):
            raise ContentLocationError(
                f"the {what} {resolved} is inside the public code repository {root}; "
                "private content must never be stored there"
            )
    return resolved


def remote_addresses(repo: Path) -> list[str]:
    """Every remote URL of ``repo``: as configured, and as Git resolves it (``insteadOf``)."""
    addresses: set[str] = set()
    configured = run_git(repo, ["config", "--get-regexp", r"^remote\..*\.(push)?url$"], check=False)
    names: set[str] = set()
    for line in configured.stdout.splitlines():
        key, _, url = line.partition(" ")
        addresses.add(url.strip())
        names.add(key.split(".", 1)[1].rsplit(".", 1)[0])
    for name in sorted(names):
        resolved = run_git(repo, ["ls-remote", "--get-url", name], check=False)
        if resolved.returncode == 0 and resolved.stdout.strip():
            addresses.add(resolved.stdout.strip())
        pushed = run_git(repo, ["remote", "get-url", "--push", "--all", name], check=False)
        addresses.update(line.strip() for line in pushed.stdout.splitlines() if line.strip())
    return sorted(address for address in addresses if address)


def is_public_remote(address: str) -> bool:
    normalized = address.strip().replace("\\", "/")  # Windows paths as local remotes
    return PUBLIC_CODE_REPOSITORY.search(normalized) is not None


def enclosing_work_trees(path: Path) -> list[Path]:
    """Every Git work tree that contains ``path`` (not counting ``path`` itself), nearest first."""
    found: list[Path] = []
    probe = path.parent
    while True:
        top = toplevel(probe)
        if top is None or top in found:
            break
        found.append(top)
        if top.parent == top:
            break
        probe = top.parent
    return found


def _refuse_public_remotes(repo: Path, what: str) -> None:
    for address in remote_addresses(repo):
        if is_public_remote(address):
            raise ContentLocationError(
                f"{what} has a remote pointing at the public code repository ({address}); "
                "private content must never be stored there"
            )


def check_content_dir(path: Path, must_exist: bool = True) -> Path:
    """Return the resolved content directory, or raise ContentLocationError."""
    resolved = check_outside_code(path, "content directory")
    if must_exist and not resolved.is_dir():
        raise ContentLocationError(
            f"no content repository at {resolved}; create one with "
            f"'python -m portfolio_studio init --content {resolved}'"
        )
    outers = enclosing_work_trees(resolved)
    for outer in outers:
        _refuse_public_remotes(outer, f"the Git repository {outer} around the content directory")
    if outers:
        raise ContentLocationError(
            f"the content directory {resolved} is inside another Git repository "
            f"({outers[0]}); it must be a repository of its own, outside any other"
        )
    enclosing = toplevel(resolved)
    if enclosing is not None and enclosing != resolved:
        raise ContentLocationError(
            f"the content directory {resolved} is inside another Git repository ({enclosing}); "
            "it must be a repository of its own"
        )
    if enclosing is not None:
        _refuse_public_remotes(resolved, "the content repository")
    elif must_exist:
        raise ContentLocationError(f"{resolved} is not a Git repository")
    return resolved
