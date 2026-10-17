"""The HTTP surface, and the agent surface built on it.

Module summary
--------------
A fifth way to reach the same engine, for the readers who will never install it:
a sustainability team, a procurement reviewer, an auditor, a colleague with a
browser. :mod:`saggio.api.app` is the application and :mod:`saggio.api.mcp` wraps
its documented routes as tools an agent can call, so the agent and the HTTP
client are told the same things about the same endpoints.

Neither is installed by default, because nobody who wants a cost model in a
pull request should have to install a web framework to get one:

.. code-block:: console

    pip install "saggio[api]"

Usage example
-------------
>>> from saggio.api import create_app
>>> create_app(allow_clone=False).title
'saggio'

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

from typing import Final

try:
    from .app import CLONE_SWITCH, app, create_app
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by hand, not in CI
    # The import that fails here is a missing optional dependency, and the
    # message a reader gets by default names a module rather than saying what to
    # install. Anything else is a real failure and is re-raised untouched.
    if exc.name not in {"fastapi", "pydantic", "starlette"}:
        raise
    raise ModuleNotFoundError(
        f"The HTTP surface needs {exc.name}, which the default install does not "
        'carry. Install it with `pip install "saggio[api]"`. Every other surface, '
        "the library, the command line and the skill, works without it."
    ) from exc

__all__: Final[list[str]] = ["CLONE_SWITCH", "app", "create_app"]
