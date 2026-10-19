"""The two gates continuous integration runs, run where anybody would see them.

The defect this exists for, found on 2026-10-19 and committed by this project's
own iterations: `ruff format --check .` had been failing on `master`, across
nine files and at least five commits, all made the same day. Nobody noticed,
because the routine before a commit here is the test suite, and the formatter
was not in it. A gate that only runs somewhere nobody looks is a gate that is
off.

Ruff is pinned exactly in `[dev]` for the reason the pin's own comment gives —
an unpinned formatter changes its own rules — so the version this runs is the
version continuous integration runs, and a pass here is a pass there.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

#: The formatter itself, by full path. Found once so the skip below and the call
#: cannot disagree about whether it is there.
RUFF = shutil.which("ruff")

pytestmark = pytest.mark.skipif(
    RUFF is None,
    reason="ruff is a [dev] dependency; an install without it cannot check its own formatting",
)


def ruff(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
        [str(RUFF), *arguments, "."], cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_the_repository_is_formatted_the_way_the_build_requires() -> None:
    done = ruff("format", "--check")
    assert done.returncode == 0, (
        "`ruff format --check .` fails, so the build does too:\n"
        f"{done.stdout.strip() or done.stderr.strip()}\n"
        "Run `ruff format .`"
    )


def test_the_repository_passes_its_own_linter() -> None:
    done = ruff("check")
    assert done.returncode == 0, f"`ruff check .` fails:\n{done.stdout.strip()}"
