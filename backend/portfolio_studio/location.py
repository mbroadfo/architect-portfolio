"""Where the private content repository may live (ADR-013 security and compliance).

Private content never enters the public code repository. The Studio refuses a content
directory that is inside the code repository (any of its work trees), inside any other Git
work tree, or a repository with a remote pointing at the public code repository.
"""

from __future__ import annotations

import re
from pathlib import Path

from portfolio_studio.errors import ContentLocationError
from portfolio_studio.gitrepo import remote_urls, run_git, toplevel

PUBLIC_CODE_REPOSITORY = re.compile(
    r"github\.com[:/]+mbroadfo/architect-portfolio(\.git)?/?$", re.IGNORECASE
)
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


def check_content_dir(path: Path, must_exist: bool = True) -> Path:
    """Return the resolved content directory, or raise ContentLocationError."""
    resolved = check_outside_code(path, "content directory")
    if must_exist and not resolved.is_dir():
        raise ContentLocationError(
            f"no content repository at {resolved}; create one with "
            f"'python -m portfolio_studio init --content {resolved}'"
        )
    enclosing = toplevel(resolved)
    if enclosing is not None and enclosing != resolved:
        raise ContentLocationError(
            f"the content directory {resolved} is inside another Git repository ({enclosing}); "
            "it must be a repository of its own"
        )
    if enclosing is not None:
        for url in remote_urls(resolved):
            if PUBLIC_CODE_REPOSITORY.search(url):
                raise ContentLocationError(
                    f"the content repository has a remote pointing at the public code "
                    f"repository ({url}); remove it before using the Studio"
                )
    elif must_exist:
        raise ContentLocationError(f"{resolved} is not a Git repository")
    return resolved
