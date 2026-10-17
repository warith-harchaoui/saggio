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

from typing import Final

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from .app import create_app

#: Where the protocol endpoint lives. The convention clients expect, named here
#: because the documentation and the compose file both quote it.
MOUNT_PATH: Final[str] = "/mcp"


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
    """
    server = FastApiMCP(application)
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
