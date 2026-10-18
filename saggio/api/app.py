"""The package reached over HTTP, for the readers who will never have it installed.

Module summary
--------------
Everything here is an adapter. Each route parses a request, calls one public
function of the library, and serialises what comes back; the shapes it returns
are the ones the command line prints with ``--json``, because two surfaces that
answer the same question differently are two tools. If a route needed logic of
its own, that logic would belong in the library instead, where every surface can
reach it.

Two refusals are built into the surface rather than into a setting, and both are
the same refusal the rest of the package makes.

**It never runs anybody's code.** Measuring executes a slice of a repository with
the permissions of whoever started the process, which is a decision for a person
at a terminal who can be asked. Over HTTP there is nobody to ask and the
permissions are the server's, so ``measure`` and ``audit --run`` have no route at
all. A client that wants a measured figure runs the command line on the machine
the code actually runs on, which is also the only machine whose counters mean
anything.

**It never clones a repository unless somebody deployed it to.** Auditing a git
URL makes the server fetch an address a client chose. That is a real capability
with real consequences, so it is off unless the operator turns it on, by
``SAGGIO_API_ALLOW_CLONE`` or by the argument :func:`create_app` takes. Off, the
route answers with what it would take rather than with a stack trace.

Usage example
-------------
>>> from fastapi.testclient import TestClient
>>> client = TestClient(create_app())
>>> client.get("/health").json()["package"]
'saggio'
>>> placed = client.post("/scopes", json={"cost_model": {
...     "deployment": {"provider": "on-prem"},
...     "scenarios": [{"name": "one", "costs": {"carbon": {"value": 1.0}}}],
... }}).json()
>>> placed["placements"][0]["label"]
'Scope 2 (location-based)'

Author
------
Warith Harchaoui, Ph.D. — https://linkedin.com/in/warith-harchaoui/
"""

from __future__ import annotations

import os
from typing import Any, Final, Literal

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from .. import __version__
from ..catalog import Catalog, stale_report
from ..catalog.registry import BUNDLED_CATALOGS
from ..diff import compare
from ..estimate.ghg import placed_model
from ..model import CostModel, overall_status, validate

#: The environment variable an operator sets to allow the one route that reaches
#: the network. Named rather than read inline because two places consult it: the
#: factory below, and the test that proves the route stays shut without it.
CLONE_SWITCH: Final[str] = "SAGGIO_API_ALLOW_CLONE"

#: What the audit route answers when nobody turned cloning on. A sentence saying
#: what would resolve it, which is the same thing every refusal in this package
#: owes its reader.
CLONE_REFUSED: Final[str] = (
    "This deployment does not clone repositories. Auditing a git URL makes the "
    f"server fetch an address the client chose, so it is off unless {CLONE_SWITCH} "
    "is set. Audit the repository where it lives with `saggio audit .`, or send a "
    "cost model to /validate, /scopes and /render, which need no network at all."
)

#: The formats a report can be returned in here. Word and PDF are deliberately
#: absent: they shell out to Pandoc, which is a fat dependency to put behind a
#: public port for an artefact the client can render from the Markdown itself.
RENDERABLE: Final[tuple[str, ...]] = ("markdown", "html")


class ModelIn(BaseModel):
    r"""A cost model on its way in, as a parsed document or as the YAML of one.

    Both shapes exist because both callers exist. A program holds the document
    and sends JSON; a person holds ``cost_of_running.yaml`` and pastes its text.
    Accepting one would have made the other convert first, and conversion is
    where a model acquires a difference nobody intended.

    Examples
    --------
    >>> ModelIn(cost_model={"project": {"name": "x"}}).document()["project"]["name"]
    'x'
    >>> ModelIn(yaml_text="project:\n  name: x\n").document()["project"]["name"]
    'x'
    """

    cost_model: dict[str, Any] | None = Field(
        default=None, description="The cost model as a parsed document."
    )
    yaml_text: str | None = Field(
        default=None, description="The cost model as the text of a cost_of_running.yaml file."
    )

    @model_validator(mode="after")
    def exactly_one_was_given(self) -> ModelIn:
        """Refuse a request carrying both or neither, naming which it was.

        Examples
        --------
        >>> ModelIn()
        Traceback (most recent call last):
            ...
        pydantic_core._pydantic_core.ValidationError: ...
        """
        given = (self.cost_model is not None, self.yaml_text is not None)
        if given == (False, False):
            raise ValueError("Send the model as `cost_model` or as `yaml_text`.")
        if given == (True, True):
            raise ValueError(
                "Send `cost_model` or `yaml_text`, not both. Two documents in one "
                "request is a question about which of them the answer describes."
            )
        return self

    def document(self) -> dict[str, Any]:
        """Return the model as a mapping, whichever way it arrived.

        Returns
        -------
        dict
            The document.

        Raises
        ------
        HTTPException
            422 when the text is not YAML, or is YAML that is not a mapping. The
            message carries the parser's own complaint, which says the line.

        Examples
        --------
        >>> ModelIn(cost_model={"a": 1}).document()
        {'a': 1}
        """
        if self.cost_model is not None:
            return self.cost_model
        try:
            parsed = yaml.safe_load(self.yaml_text or "")
        except yaml.YAMLError as exc:
            raise HTTPException(422, f"That is not YAML: {exc}") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(422, "A cost model is a mapping, and that text is not one.")
        return parsed


class RenderIn(ModelIn):
    """A cost model and the shape the report should come back in.

    Examples
    --------
    >>> RenderIn(cost_model={"project": {"name": "x"}}).format
    'markdown'
    """

    format: Literal["markdown", "html"] = Field(
        default="markdown", description="Which report to render."
    )


class DiffIn(BaseModel):
    """Two models and the gate between them.

    Examples
    --------
    >>> DiffIn(before={"scenarios": []}, after={"scenarios": []}).threshold_percent
    10.0
    """

    before: dict[str, Any] = Field(description="The model as it was.")
    after: dict[str, Any] = Field(description="The model as it is now.")
    threshold_percent: float = Field(
        default=10.0, description="How far a figure may move before the comparison fails."
    )


class AuditIn(BaseModel):
    """A repository to read, and the facts only the asker holds.

    Examples
    --------
    >>> AuditIn(git_url="https://example.invalid/x.git", country="FR").use_llm
    False
    """

    git_url: str = Field(description="A git URL the server will clone shallowly and read.")
    country: str | None = Field(
        default=None,
        description=(
            "ISO 3166-1 alpha-2 code where the code runs. Without it the carbon "
            "and money figures stay open, which is the correct outcome rather "
            "than a failure. It is never inferred from the request."
        ),
    )
    provider: str | None = Field(
        default=None, description="Providers-catalogue key, which also settles the GHG scope."
    )
    instance: str | None = Field(default=None, description="Instances-catalogue key.")
    use_llm: bool = Field(
        default=False,
        description=(
            "Whether to ask a local model to classify the shape of the work. Off "
            "here, so that the same request gives the same answer on a server "
            "that has no model reachable."
        ),
    )


def create_app(*, allow_clone: bool | None = None) -> FastAPI:
    """Build the application, with the one capability that is a deployment choice.

    Parameters
    ----------
    allow_clone : bool or None, optional
        Whether ``/audit`` may clone a git URL. ``None``, the default, reads
        :data:`CLONE_SWITCH` from the environment, so a container is configured
        the way containers are configured and a library caller can still be
        explicit.

    Returns
    -------
    FastAPI
        The application.

    Examples
    --------
    >>> create_app(allow_clone=False).title
    'saggio'
    """
    permitted = (
        os.environ.get(CLONE_SWITCH, "").strip().lower() in {"1", "true", "yes"}
        if allow_clone is None
        else allow_clone
    )

    application = FastAPI(
        title="saggio",
        version=__version__,
        summary=(
            "What it costs to run code, per unit of work, with every number "
            "saying how far it can be trusted."
        ),
        description=(
            "Money, time, energy, carbon, water, and any dimension a project "
            "registers, per unit of work. Every number carries a status — "
            "measured, estimated, placeholder, or TODO — and names the numbers it "
            "was derived from, and `/scopes` says which line of a corporate "
            "greenhouse-gas inventory each figure belongs on.\n\n"
            "This surface reads and reports. It never executes a repository's "
            "code, and it clones one only where the operator has allowed it."
        ),
    )

    @application.get(
        "/health", operation_id="health", summary="Is the service up, and which version"
    )
    def health() -> dict[str, Any]:
        """Report the running version and what this deployment will do.

        Returns
        -------
        dict
            The package name, its version, and whether cloning is permitted here.

        Examples
        --------
        >>> create_app(allow_clone=False) is not None
        True
        """
        return {
            "package": "saggio",
            "version": __version__,
            "clones_repositories": permitted,
            "runs_repository_code": False,
        }

    @application.post(
        "/validate",
        operation_id="validate_cost_model",
        summary="Check a cost model against the rules, including the weakest-link rule",
    )
    def validate_route(request: ModelIn) -> dict[str, Any]:
        """Return the verdict on a model, and the weakest status anywhere in it.

        A derived figure may never claim to be better founded than the worst of
        the figures it came from. That rule is most of what fails here, and a
        failure is information: it says either the status is wrong or the
        derivation is.

        Parameters
        ----------
        request : ModelIn
            The model.

        Returns
        -------
        dict
            ``ok``, the errors and warnings with their paths, and
            ``overall_status``.

        Examples
        --------
        >>> validate_route(ModelIn(cost_model={"project": {"name": "x"}}))["ok"]
        False
        """
        document = request.document()
        report = validate(document)
        return report.to_mapping() | {"overall_status": overall_status(document)}

    @application.post(
        "/next",
        operation_id="next_question",
        summary="Say which open field would close the most numbers",
    )
    def next_route(request: ModelIn) -> dict[str, Any]:
        """Rank a model's open fields by what answering each one would close.

        A model comes back from an audit with fifteen open fields, each already
        carrying a sentence about what would resolve it, and nothing saying
        which to answer first. They are not independent: a measured runtime
        closes several figures through the derivation chain, and a water usage
        effectiveness closes one.

        Nothing is computed or written here, and no question is invented: it
        reports the fields the model already holds open, in the words the model
        already wrote for them, ordered by the size of the cascade each would
        start.

        Parameters
        ----------
        request : ModelIn
            The model.

        Returns
        -------
        dict
            ``open_total`` and the ``questions``, each with what it closes.

        Examples
        --------
        >>> out = next_route(ModelIn(cost_model={"assumptions": {
        ...     "power_draw": {"value": None, "status": "TODO", "unit": "W"}}}))
        >>> out["open_total"]
        1
        """
        from ..model.questions import questions_payload

        return questions_payload(request.document())

    @application.post(
        "/scopes",
        operation_id="place_in_inventory",
        summary="Say which line of a greenhouse-gas inventory each figure belongs on",
    )
    def scopes_route(request: ModelIn, scenario: str | None = None) -> dict[str, Any]:
        """Place a model's costs in a corporate greenhouse-gas inventory.

        The scope turns on one fact the model already states, who operates the
        machine. Owned hardware means the organisation bought the electricity, so
        it is its scope 2 and the hardware its scope 3 category 2; a vendor's
        cloud means it bought a service, and both reach it as scope 3 category 1.
        A provider nobody classified gets no scope rather than a guessed one.

        No figure is computed here, and one is refused: a market-based scope 2
        number cannot be derived from a grid average, so what comes back is what
        it would take.

        Parameters
        ----------
        request : ModelIn
            The model.
        scenario : str or None, optional
            Which scenario's costs to place. The first one when omitted.

        Returns
        -------
        dict
            The placements in the model's own dimension order, how well founded
            the placed figures are, and the standards that settle them.

        Examples
        --------
        >>> placed = scopes_route(ModelIn(cost_model={
        ...     "deployment": {"provider": "aws"},
        ...     "scenarios": [{"name": "one", "costs": {"carbon": {"value": 1.0}}}],
        ... }))
        >>> placed["placements"][0]["scope"]
        '3'
        """
        try:
            return placed_model(request.document(), scenario=scenario)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @application.post(
        "/render",
        operation_id="render_report",
        summary="Turn a cost model into a report people can read",
    )
    def render_route(request: RenderIn) -> dict[str, Any]:
        """Render a model as Markdown or as a self-contained HTML page.

        Parameters
        ----------
        request : RenderIn
            The model and the format.

        Returns
        -------
        dict
            The format and the report.

        Examples
        --------
        >>> out = render_route(RenderIn(cost_model={"project": {"name": "demo"}, "scenarios": []}))
        >>> out["report"].startswith("# Cost of running demo")
        True
        """
        from ..report import render_html, render_markdown

        document = request.document()
        rendered = (
            render_markdown(document) if request.format == "markdown" else render_html(document)
        )
        return {"format": request.format, "report": rendered}

    @application.post(
        "/diff",
        operation_id="compare_cost_models",
        summary="Compare two cost models and fail when a figure moved too far",
    )
    def diff_route(request: DiffIn) -> dict[str, Any]:
        """Report what moved between two models, and whether it passed the gate.

        Parameters
        ----------
        request : DiffIn
            The two models and the threshold.

        Returns
        -------
        dict
            ``passes``, the threshold, and every change.

        Examples
        --------
        >>> diff_route(DiffIn(before={"scenarios": []}, after={"scenarios": []}))["passes"]
        True
        """
        return compare(
            request.before, request.after, threshold_percent=request.threshold_percent
        ).to_mapping()

    @application.get(
        "/catalog",
        operation_id="list_catalogues",
        summary="Which catalogues of facts this deployment carries",
    )
    def catalogues() -> dict[str, Any]:
        """Name the bundled catalogues.

        Returns
        -------
        dict
            Their names.

        Examples
        --------
        >>> "grid" in catalogues()["catalogues"]
        True
        """
        return {"catalogues": list(BUNDLED_CATALOGS)}

    @application.get(
        "/catalog/{name}",
        operation_id="read_catalogue",
        summary="Read a catalogue's rows, each with the source it was read from",
    )
    def catalogue(name: str) -> dict[str, Any]:
        """Return one catalogue, every row carrying its source URL and the date.

        Parameters
        ----------
        name : str
            A bundled catalogue name.

        Returns
        -------
        dict
            The catalogue's sections and their rows.

        Raises
        ------
        HTTPException
            404 naming the catalogues that do exist.

        Examples
        --------
        >>> "countries" in catalogue("grid")["sections"]
        True
        """
        if name not in BUNDLED_CATALOGS:
            raise HTTPException(
                404, f"No catalogue named {name!r}. There is: " + ", ".join(BUNDLED_CATALOGS)
            )
        loaded = Catalog.load(name)
        return {
            "catalogue": name,
            "sections": {section: loaded.rows(section) for section in loaded.sections()},
        }

    @application.get(
        "/freshness",
        operation_id="catalogue_freshness",
        summary="Which catalogue figures are stale or about to be",
    )
    def freshness() -> dict[str, Any]:
        """Report the rows nobody has re-read inside their own freshness window.

        Every column goes stale on its own schedule, because a grid intensity and
        a hardware footprint do not change at the same speed. A figure past its
        window is not wrong, it is unvouched for, and the difference matters to
        anybody quoting it.

        Returns
        -------
        dict
            Stale and expiring rows, by catalogue.

        Examples
        --------
        >>> isinstance(freshness(), dict)
        True
        """
        return {"freshness": stale_report()}

    @application.post(
        "/audit",
        operation_id="audit_repository",
        summary="Read a repository and build a cost model from it, without running it",
    )
    def audit_route(request: AuditIn) -> dict[str, Any]:
        """Clone a repository shallowly, read it, and return the model it implies.

        Reading only. Nothing in the repository is executed, so every figure that
        would have come from a measurement comes back open, with a note saying
        that running the command line where the code lives is what closes it.

        Parameters
        ----------
        request : AuditIn
            The URL and the facts only the asker holds.

        Returns
        -------
        dict
            The model, its verdict, and the notes the audit made, which name
            every catalogue row that was missing and every projection refused.

        Raises
        ------
        HTTPException
            403 when this deployment does not clone, 400 when the clone failed.

        Examples
        --------
        >>> create_app(allow_clone=False) is not None
        True
        """
        if not permitted:
            raise HTTPException(403, CLONE_REFUSED)

        from ..auditor import AuditOptions, audit_git_url

        options = AuditOptions(
            run=False,
            use_llm=request.use_llm,
            country=request.country,
            provider=request.provider,
            instance=request.instance,
        )
        try:
            result = audit_git_url(request.git_url, options=options)
        except RuntimeError as exc:
            raise HTTPException(400, str(exc)) from exc
        model = (
            result.model
            if isinstance(result.model, CostModel)
            else CostModel.from_mapping(result.model)
        )
        return {
            "model": model.data,
            "report": result.report.to_mapping(),
            "notes": list(result.notes),
        }

    return application


#: The application a server imports. Built at import time with the environment's
#: answer, because that is what `uvicorn saggio.api.app:app` expects to find.
app: Final[FastAPI] = create_app()
