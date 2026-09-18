"""
The local model's job, and the strict limit on it.

Module summary
--------------
A language model reading a repository is good at one thing this package wants:
saying what kind of work the code does, in a sentence, when the file names and
imports do not make it obvious. It is bad at another thing this package must
never let it do: producing a number.

So the contract here is narrow and enforced by the shape of the request. The model
is asked for a small set of categorical fields and one line of prose. Anything
numeric it returns is discarded. Every number in a cost model comes from a file
that can be opened or a counter that can be read, and a figure that came out of a
model is a figure nobody can check.

The model runs locally through Ollama. No key, no account, no request leaving the
machine. When Ollama is not running, which is the normal case, every function here
returns ``None`` quickly and the audit proceeds on the static reading alone.

Usage example
-------------
>>> from saggio.analyze.llm import is_available
>>> isinstance(is_available(), bool)
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Final

import os_helper as osh

#: Where Ollama listens by default.
DEFAULT_HOST: Final[str] = "http://127.0.0.1:11434"

#: Environment variables a user sets to point elsewhere or pick a model.
HOST_ENVIRONMENT_VARIABLE: Final[str] = "OLLAMA_HOST"
MODEL_ENVIRONMENT_VARIABLE: Final[str] = "SAGGIO_MODEL"

#: Models preferred for reading code, best first. The first one installed is used.
PREFERRED_MODELS: Final[tuple[str, ...]] = (
    "qwen2.5-coder:7b",
    "qwen2.5-coder:latest",
    "deepseek-coder-v2:latest",
    "codellama:latest",
    "qwen2.5:7b",
    "llama3.1:8b",
)

#: Seconds to wait when checking whether Ollama is up. An absent server is the
#: normal case, so the check must be quick enough that nobody notices it.
PROBE_TIMEOUT_SECONDS: Final[float] = 1.5

#: Seconds to wait for a classification. A local model that has not answered in
#: this long is not going to make the audit better by answering later.
GENERATE_TIMEOUT_SECONDS: Final[float] = 90.0

#: The only fields the model is allowed to fill in. Everything else it returns is
#: dropped, which is how "the model never supplies a number" is enforced rather
#: than merely requested.
ALLOWED_FIELDS: Final[frozenset[str]] = frozenset(
    {"workload_kind", "dominant_operation", "compute_bound", "reasoning"}
)

#: Workload kinds the model may choose between. A free-text answer would be
#: unusable downstream, so the choice is closed.
WORKLOAD_KINDS: Final[tuple[str, ...]] = (
    "training",
    "inference",
    "batch-pipeline",
    "service",
    "command-line-tool",
    "library",
    "unknown",
)

#: How much of the repository to show the model. Enough for the shape, little
#: enough to stay inside a small local model's context.
_MAX_PROMPT_CHARACTERS: Final[int] = 12_000


def host() -> str:
    """Return the Ollama endpoint to talk to.

    Returns
    -------
    str
        The configured host, or the local default.

    Examples
    --------
    >>> host().startswith("http")
    True
    """
    configured = os.environ.get(HOST_ENVIRONMENT_VARIABLE, "").strip()
    if not configured:
        return DEFAULT_HOST
    return configured if configured.startswith("http") else f"http://{configured}"


def _get(path: str, *, timeout: float) -> dict[str, Any] | None:
    """Fetch JSON from the local server, returning ``None`` on any failure.

    Parameters
    ----------
    path : str
        The endpoint path, beginning with a slash.
    timeout : float
        Seconds to wait.

    Returns
    -------
    dict or None
        The decoded response, or ``None``. An absent server is expected, so it is
        not logged as an error.

    Examples
    --------
    >>> answer = _get("/api/tags", timeout=PROBE_TIMEOUT_SECONDS)
    >>> answer is None or isinstance(answer, dict)
    True
    """
    try:
        with urllib.request.urlopen(f"{host()}{path}", timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def is_available() -> bool:
    """Return whether a local Ollama server is reachable.

    Returns
    -------
    bool
        ``True`` when the server answered. ``False`` is the common case and is
        not a problem: the audit runs on the static reading alone.

    Examples
    --------
    >>> isinstance(is_available(), bool)
    True
    """
    return _get("/api/tags", timeout=PROBE_TIMEOUT_SECONDS) is not None


def installed_models() -> tuple[str, ...]:
    """Return the model tags installed locally.

    Returns
    -------
    tuple of str
        Model tags, or an empty tuple when the server is not reachable.

    Examples
    --------
    >>> isinstance(installed_models(), tuple)
    True
    """
    payload = _get("/api/tags", timeout=PROBE_TIMEOUT_SECONDS)
    if not payload:
        return ()
    return tuple(
        str(entry.get("name"))
        for entry in payload.get("models", [])
        if isinstance(entry, dict) and entry.get("name")
    )


def pick_model() -> str | None:
    """Return the local model to use, or ``None`` when there is none.

    The environment variable wins outright, so a user can pin a model without
    editing anything. Otherwise the first preferred model that is installed is
    used, and failing that the first installed model of any kind.

    Returns
    -------
    str or None
        A model tag, or ``None``.

    Examples
    --------
    >>> pick_model() is None or isinstance(pick_model(), str)
    True
    """
    pinned = os.environ.get(MODEL_ENVIRONMENT_VARIABLE, "").strip()
    if pinned:
        return pinned
    available = installed_models()
    if not available:
        return None
    for preferred in PREFERRED_MODELS:
        if preferred in available:
            return preferred
    return available[0]


@dataclass(frozen=True, slots=True)
class Classification:
    """What the model said about the shape of the work, and which model said it.

    Parameters
    ----------
    workload_kind : str
        One of :data:`WORKLOAD_KINDS`.
    dominant_operation : str
        A short phrase naming the main cost driver, such as
        ``matrix multiplication in the training loop``.
    compute_bound : bool or None
        Whether the model thinks the work is limited by compute.
    reasoning : str
        One line saying why.
    model : str
        The model tag, recorded as the evidence source so a reader knows a model
        said this and which one.

    Examples
    --------
    >>> Classification("training", "matmul", True, "loop over batches", "q:7b").model
    'q:7b'
    """

    workload_kind: str
    dominant_operation: str
    compute_bound: bool | None
    reasoning: str
    model: str

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the classification for the model's analysis block.

        Returns
        -------
        dict
            Prose and categories only, with the evidence source naming the model.
            There is deliberately no numeric field here.

        Examples
        --------
        >>> Classification("training", "matmul", True, "why", "m").to_mapping()["evidence_source"]
        'llm:m'
        """
        mapping: dict[str, Any] = {
            "evidence_source": f"llm:{self.model}",
            "workload_kind": self.workload_kind,
            "confidence": "low",
        }
        if self.dominant_operation:
            mapping["dominant_operation"] = self.dominant_operation
        if self.compute_bound is not None:
            mapping["compute_bound"] = self.compute_bound
        if self.reasoning:
            mapping["reasoning"] = self.reasoning
        return mapping


def _build_prompt(summary: str) -> str:
    """Build the classification request.

    Parameters
    ----------
    summary : str
        A description of the repository: its files, its imports, its entry points.

    Returns
    -------
    str
        The prompt, which asks for categories and prose and forbids numbers.

    Examples
    --------
    >>> "JSON" in _build_prompt("a repository")
    True
    """
    kinds = ", ".join(WORKLOAD_KINDS)
    return (
        "You are reading a source repository to classify the shape of the work it "
        "does. Answer with a single JSON object and nothing else.\n\n"
        "Fields:\n"
        f'  "workload_kind": one of [{kinds}]\n'
        '  "dominant_operation": a short phrase naming the main cost driver\n'
        '  "compute_bound": true, false, or null if you cannot tell\n'
        '  "reasoning": one sentence saying why\n\n'
        "Do not include any number, estimate, duration, cost, or measurement in "
        "any field. Numbers come from measurement elsewhere and any you supply "
        "will be discarded.\n\n"
        f"Repository:\n{summary[:_MAX_PROMPT_CHARACTERS]}\n"
    )


def _coerce(payload: dict[str, Any], model: str) -> Classification | None:
    """Turn a model response into a classification, dropping anything else.

    Parameters
    ----------
    payload : dict
        What the model returned, already decoded.
    model : str
        The model tag.

    Returns
    -------
    Classification or None
        The classification, or ``None`` when the workload kind is not one of the
        closed set, which means the model did not answer the question asked.

    Examples
    --------
    >>> _coerce({"workload_kind": "training", "cost_usd": 3}, "m").workload_kind
    'training'
    >>> _coerce({"workload_kind": "vibes"}, "m") is None
    True
    """
    kept = {key: value for key, value in payload.items() if key in ALLOWED_FIELDS}
    kind = str(kept.get("workload_kind", "")).strip().lower()
    if kind not in WORKLOAD_KINDS:
        return None
    compute_bound = kept.get("compute_bound")
    return Classification(
        workload_kind=kind,
        dominant_operation=str(kept.get("dominant_operation") or "")[:160],
        compute_bound=compute_bound if isinstance(compute_bound, bool) else None,
        reasoning=str(kept.get("reasoning") or "")[:400],
        model=model,
    )


def classify(summary: str, *, model: str | None = None) -> Classification | None:
    """Ask a local model what shape of work a repository does.

    Parameters
    ----------
    summary : str
        A description of the repository built by the static pass.
    model : str or None, optional
        A model tag to use; resolved by :func:`pick_model` when not given.

    Returns
    -------
    Classification or None
        What the model said, or ``None`` when no model is available, the request
        failed, or the answer was not usable. Every one of those is a normal
        outcome and none of them stops an audit.

    Examples
    --------
    >>> classify("an empty repository", model="definitely-not-installed") is None
    True
    """
    chosen = model or pick_model()
    if not chosen:
        return None

    request = urllib.request.Request(  # noqa: S310 - a fixed local endpoint.
        f"{host()}/api/generate",
        data=json.dumps(
            {
                "model": chosen,
                "prompt": _build_prompt(summary),
                "stream": False,
                "format": "json",
                # A classification should not vary between two runs over the same
                # repository, so the sampler is pinned as far as it can be.
                "options": {"temperature": 0.0, "seed": 0},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=GENERATE_TIMEOUT_SECONDS) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        payload = json.loads(body.get("response", "{}"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        osh.debug(f"Local model classification unavailable: {exc}")
        return None
    if not isinstance(payload, dict):
        return None
    return _coerce(payload, chosen)
