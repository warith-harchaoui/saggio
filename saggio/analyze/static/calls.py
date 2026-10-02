"""Which paid services and which models the code calls.

Module summary
--------------
Both are read line by line, and both refuse a line that is prose about code
rather than code: a service named in a comment is not a service being called.
A model identifier being built by concatenation is refused too, because the
string in the source is not the string that reaches the API.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from pathlib import Path

from ...catalog.registry import Catalog
from .findings import ModelHit, ServiceHit
from .tables import (
    _ANNOTATIONS_LOOK_LIKE_MAPPINGS,
    _CONCATENATION,
    _MAX_SCANNED_BYTES,
    _SCANNED_EXTENSIONS,
    MODEL_ASSIGNMENT_PATTERN,
    MODEL_MAPPING_PATTERN,
)
from .walking import _is_prose_line, _iter_source_files


def detect_services(root: Path, *, overlay: Path | None = None) -> tuple[ServiceHit, ...]:
    r"""Find the paid services the repository calls, keeping the evidence.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory.

    Returns
    -------
    tuple of ServiceHit
        One hit per service, the first occurrence of each.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "app.py").write_text("import openai\\n", encoding="utf-8")
    ...     detect_services(Path(folder))[0].key
    'openai'
    """
    services = Catalog.load("services", overlay=overlay).rows("services")
    hits: dict[str, ServiceHit] = {}
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SCANNED_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_SCANNED_BYTES:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        relative = str(path.relative_to(root))
        for number, line in enumerate(lines, start=1):
            if _is_prose_line(line):
                continue
            for key, row in services.items():
                if key in hits:
                    continue
                # A hint must end at a word boundary: `from openai` naming the
                # vendor's own package must not also match `from openai_agents`,
                # which is somebody else's.
                if any(
                    re.search(rf"{re.escape(str(hint))}(?![\w-])", line)
                    for hint in (row.get("detect") or [])
                ):
                    hits[key] = ServiceHit(
                        key=key,
                        name=str(row.get("name") or key),
                        path=relative,
                        line_number=number,
                        line=line.strip()[:200],
                        pricing_source_url=str(row.get("pricing_source_url") or ""),
                    )
    return tuple(hits[key] for key in sorted(hits))


def _identifier_if_not_being_built(line: str, match: re.Match[str], *, group: int) -> str | None:
    """Return the matched literal unless it is a fragment of a larger string.

    Parameters
    ----------
    line : str
        The line the match came from.
    match : re.Match
        The match.
    group : int
        Which group holds the literal.

    Returns
    -------
    str or None
        The identifier, or ``None`` when the literal is being concatenated,
        interpolated, or formatted into something else.

    Examples
    --------
    >>> line = 'model = "gpt-" + version'
    >>> _identifier_if_not_being_built(
    ...     line, MODEL_ASSIGNMENT_PATTERN.search(line), group=2) is None
    True
    """
    after = line[match.end() :].lstrip()
    before = line[: match.start(group) - 1].rstrip()
    if after.startswith(_CONCATENATION) or before.endswith(_CONCATENATION):
        return None
    identifier = match.group(group).strip()
    return identifier or None


def model_named_on(line: str, *, suffix: str) -> str | None:
    r"""Return the model identifier a line chooses, or ``None``.

    Three things look alike to a regular expression and are not alike at all: a
    model being chosen, a type being annotated, and a string being built. The
    first is what this looks for; the other two produced two of the wrong answers
    in this package's own gallery, and both are decidable from the line.

    Parameters
    ----------
    line : str
        One line of source, already known not to be prose.
    suffix : str
        The file's extension, lowercased. It decides whether an unquoted key
        before a colon is a mapping entry or a type annotation.

    Returns
    -------
    str or None
        The identifier, or ``None`` when the line names none.

    Examples
    --------
    >>> model_named_on('client.chat(model="gpt-4o")', suffix=".py")
    'gpt-4o'
    >>> model_named_on('reply = call({"model": "gpt-4o"})', suffix=".py")
    'gpt-4o'
    >>> model_named_on('    model: "Whisper", mel: Tensor', suffix=".py") is None
    True
    >>> model_named_on('const body = { model: "gpt-4o" };', suffix=".ts")
    'gpt-4o'
    >>> model_named_on('model_name = "Body_" + name', suffix=".py") is None
    True
    """
    for match in MODEL_ASSIGNMENT_PATTERN.finditer(line):
        identifier = _identifier_if_not_being_built(line, match, group=2)
        if identifier is not None:
            return identifier
    for match in MODEL_MAPPING_PATTERN.finditer(line):
        key_was_quoted = bool(match.group(1))
        if not key_was_quoted and suffix in _ANNOTATIONS_LOOK_LIKE_MAPPINGS:
            # Python has no unquoted mapping keys, so this is an annotation.
            continue
        identifier = _identifier_if_not_being_built(line, match, group=3)
        if identifier is not None:
            return identifier
    return None


def detect_models(root: Path) -> tuple[ModelHit, ...]:
    r"""Find the model identifiers the code names, keeping the evidence.

    Every distinct identifier is reported once, at its first occurrence, in the
    order the walk meets them. Nothing is verified here: whether a string is a
    real model is a question for whoever prices it, and a string this pass cannot
    price is still worth showing to a reader who can.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple of ModelHit
        One hit per distinct identifier.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "app.py").write_text(
    ...         'client.chat(model="gpt-4o")\n', encoding="utf-8")
    ...     detect_models(Path(folder))[0].identifier
    'gpt-4o'
    """
    hits: dict[str, ModelHit] = {}
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SCANNED_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_SCANNED_BYTES:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        relative = str(path.relative_to(root))
        for number, line in enumerate(lines, start=1):
            if _is_prose_line(line):
                continue
            identifier = model_named_on(line, suffix=path.suffix.lower())
            if identifier is not None and identifier not in hits:
                hits[identifier] = ModelHit(
                    identifier=identifier,
                    path=relative,
                    line_number=number,
                    line=line.strip()[:200],
                )
    return tuple(hits.values())
