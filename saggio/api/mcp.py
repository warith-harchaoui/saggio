"""The same endpoints, offered to an agent instead of to a browser.

Module summary
--------------
Model Context Protocol tools, generated from the HTTP routes rather than written
beside them. The generator reads the application's own OpenAPI document, so a
tool's name is the route's ``operation_id``, its description is the route's
docstring, and its arguments are the request model's fields. Nothing here
decides what a tool says: a thin wrapper that paraphrased the routes would be a
second description of the same endpoint, free to drift, and the drift would show
up as an agent confidently telling somebody the wrong thing about a scope.

Which is the point of the surface. A sustainability or finance reader can ask,
in their own words and their own language, *which scope does our inference land
on, and how well founded is that number*, and the answer comes back from the
same function that answers the command line.

The refusals come with it. There is no tool for measuring, because the HTTP
surface has no route for it, and ``audit_repository`` exists even where this
deployment does not clone: a refusal naming what would resolve it is a better
answer to an agent than a tool that is not there.

Usage example
-------------
>>> tools = [tool.name for tool in attach_mcp(create_app(allow_clone=False)).tools]
>>> "place_in_inventory" in tools
True
>>> "measure" in tools
False

Running it:

.. code-block:: console

    uvicorn saggio.api.mcp:app --host 127.0.0.1 --port 8000
    # the endpoint an agent connects to is then http://127.0.0.1:8000/mcp

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import re
from typing import Final

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from .. import __version__
from .app import create_app

#: Where the protocol endpoint lives. The convention clients expect, named here
#: because the documentation and the compose file both quote it.
MOUNT_PATH: Final[str] = "/mcp"


#: Numpydoc section headings whose content an agent either cannot use or already
#: has. ``Parameters`` is the pointed one: the arguments reach the agent typed,
#: in the tool's own input schema, and the prose version of them names the
#: Python request class instead -- ``request : RenderIn``, a class the agent
#: cannot see and has no way to build.
_NOT_FOR_AN_AGENT: Final[tuple[str, ...]] = (
    "Parameters",
    "Returns",
    "Raises",
    "Yields",
    "Examples",
    "Notes",
    "See Also",
    "References",
)

_SECTION = re.compile(
    r"\n[ \t]*(?:" + "|".join(_NOT_FOR_AN_AGENT) + r")[ \t]*\n[ \t]*-{3,}.*",
    re.S,
)


def agent_prose(description: str) -> str:
    r"""Return the part of a generated tool description an agent can act on.

    The descriptions come from the routes' own docstrings, which is the point of
    this module: one text, no second copy to drift. But a docstring is written
    for somebody reading the source, and three of its parts reach an agent as
    noise or worse.

    **Measured over the eleven tools before this existed: 45% of what the agent
    received was usable prose.** For ``render_report`` it was 22% -- two useful
    sentences, then three hundred and ninety characters about a Python class,
    a doctest, and a content type.

    And the worst of it is not noise, it is wrong. The only worked example in
    ``render_report`` read ``render_route(RenderIn(cost_model={...}))``: a
    function and a class that do not exist in the agent's world, where the tool
    actually takes ``cost_model``, ``format``, ``language`` and ``yaml_text``.
    An agent that patterns off examples is being shown the wrong shape of call
    by the very text that is supposed to teach it the right one.

    So the numpydoc sections go, the doctests with them, and the protocol's own
    ``### Responses:`` block too -- the content type of an HTTP response is not
    a fact about a tool an agent reaches through the protocol. What stays is the
    summary line and the prose explaining *when to reach for this one*, which is
    the only thing a caller choosing between eleven tools needs.

    Parameters
    ----------
    description : str
        The generated description, summary and docstring and responses block.

    Returns
    -------
    str
        The prose, with nothing added. Never empty: every route here opens with
        a summary line, and a contract test refuses one that does not.

    Examples
    --------
    >>> agent_prose("Do a thing\n\nAt length.\n\nReturns\n-------\nint\n    A number.")
    'Do a thing\n\nAt length.'
    >>> agent_prose("Only a summary\n\n### Responses:\n\n**200**: Successful Response")
    'Only a summary'
    """
    text = description.split("### Responses:", 1)[0]
    text = _SECTION.sub("", text)
    text = re.sub(r"^[ \t]*>>>.*$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def attach_mcp(application: FastAPI, *, mount_path: str = MOUNT_PATH) -> FastApiMCP:
    """Expose an application's documented routes as agent tools, in place.

    Parameters
    ----------
    application : FastAPI
        The application to read. Its routes are not modified; the protocol
        endpoint is added beside them.
    mount_path : str, optional
        Where the protocol endpoint is mounted.

    Returns
    -------
    FastApiMCP
        The server, whose ``tools`` are the routes it found.

    Examples
    --------
    >>> server = attach_mcp(create_app(allow_clone=False))
    >>> sorted(tool.name for tool in server.tools)[:2]
    ['audit_repository', 'catalogue_freshness']
    >>> server.server.version == __version__
    True
    """
    server = FastApiMCP(application)

    # fastapi-mcp builds the protocol server as `Server(name, description)`, and
    # the second parameter of that constructor is the *version*. So a client
    # listing its servers shows this package's whole description where a version
    # belongs, which is both unreadable and unanswerable: an agent that reports
    # which version answered it would report a paragraph. Put the version back,
    # and leave the description where it is already carried, in the application.
    low_level = getattr(server, "server", None)
    if low_level is not None:
        low_level.version = __version__

    # The descriptions are the routes' docstrings, which is deliberate, and a
    # docstring carries parts written for somebody reading the source. They are
    # trimmed here rather than at the routes, so the one text keeps serving both
    # readers and neither gets the other's half.
    for tool in server.tools:
        tool.description = agent_prose(tool.description or "")

    server.mount_http(application, mount_path=mount_path)
    return server


def create_mcp_app(*, allow_clone: bool | None = None) -> FastAPI:
    """Build the application with the protocol endpoint already mounted.

    Parameters
    ----------
    allow_clone : bool or None, optional
        Passed through to :func:`saggio.api.app.create_app`.

    Returns
    -------
    FastAPI
        The application, serving both HTTP and the protocol.

    Examples
    --------
    >>> paths = {route.path for route in create_mcp_app(allow_clone=False).routes}
    >>> "/scopes" in paths and "/mcp" in paths
    True
    """
    application = create_app(allow_clone=allow_clone)
    attach_mcp(application)
    return application


#: What a server imports: `uvicorn saggio.api.mcp:app`.
app: Final[FastAPI] = create_mcp_app()
