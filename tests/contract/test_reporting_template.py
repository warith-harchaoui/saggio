"""The contract between the authored report template and the copy the wheel ships."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPORTING = Path(__file__).resolve().parents[2] / "reporting"

#: Loaded by path rather than imported, because ``reporting/`` is authoring
#: material next to the package rather than part of it.
_spec = importlib.util.spec_from_file_location("reporting_sync", REPORTING / "sync.py")
assert _spec is not None and _spec.loader is not None
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def test_the_packaged_copy_matches_what_was_authored() -> None:
    """An edit made in one copy and not the other must fail here, not ship."""
    stale = sync.assets_out_of_date()
    assert not stale, (
        f"{', '.join(stale)} differ between reporting/ and the package. "
        "Edit reporting/, then run `python reporting/sync.py`."
    )


def test_the_template_declares_exactly_the_tokens_the_renderer_fills() -> None:
    """A token on one side and not the other is a report with a hole in it.

    The renderer raises on a token it was given nothing for, so that direction is
    already covered at runtime. This catches the other one: a keyword passed to a
    template that stopped asking for it, which nothing would otherwise notice.
    """
    from saggio.report import html

    template = (REPORTING / "report.html").read_text("utf-8")
    in_template = set(re.findall(r"\{\{([A-Z_]+)\}\}", template))
    # The keyword names at the call site are the other half of the contract;
    # reading them from the source keeps this test from restating the list.
    call = Path(html.__file__).read_text("utf-8").split("_fill(")[-1]
    filled = set(re.findall(r"^\s+([A-Z_]+)=", call, re.M))
    assert in_template == filled, (
        f"template tokens {sorted(in_template)} do not match the renderer's {sorted(filled)}"
    )
