"""
Reading a repository without running it.

Module summary
--------------
Before anything is executed, a great deal can be learned by reading. Which
languages the repository is written in, what shape of work it does, which compute
frameworks it imports, how much work a full run performs, which paid services it
calls and on which line, and what could be run as a short representative slice.

Everything in this module is deterministic and quotes its evidence. That is the
division of labour the package keeps: **the static pass owns every number**, and
the local model, when one is available, owns only qualitative judgements. A number
that came out of a language model is a number nobody can check.

The work-size read is where care is needed. A repository often states its size in
more than one place, and an earlier file saying ``max_iters = 300`` while the real
configuration says ``600000`` would silently cap a measured slice at two thousand
times the intended size. So every candidate is collected, precedence is explicit
and documented, and a disagreement is recorded rather than resolved in silence.

Usage example
-------------
>>> from saggio.analyze.static import read_repository
>>> reading = read_repository(".")
>>> reading.languages.get("Python", 0) > 0
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from ..catalog.registry import Catalog

#: File extension to language name. Broad on purpose: a mixed repository should be
#: described as mixed rather than reduced to whatever it has most of.
LANGUAGE_BY_EXTENSION: Final[dict[str, str]] = {
    ".py": "Python",
    ".ipynb": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".scala": "Scala",
    ".jl": "Julia",
    ".r": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
}

#: Directories that are never the code under study.
SKIPPED_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
        "site-packages",
        "vendor",
        "third_party",
        ".next",
        "target",
    }
)

#: Extensions worth reading line by line when hunting for service calls.
_SCANNED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".scala"}
)

#: Line openings that mean a line is prose about code rather than code. A line
#: that mentions a service in a comment or an example is not a line that calls it.
PROSE_MARKERS: Final[tuple[str, ...]] = (
    "#",
    "//",
    "/*",
    "*",
    chr(34) * 3,
    chr(39) * 3,
    ">>>",
    "...",
    "--",
)

#: A file larger than this is not scanned: a generated bundle would dominate the
#: evidence and slow the read to no purpose.
_MAX_SCANNED_BYTES: Final[int] = 512_000

#: Filenames that most often hold a run's configuration, in the order they are
#: trusted. This is the documented precedence for the work-size read: a file whose
#: whole job is configuration outranks a training script that may carry a default.
CONFIG_FILE_PRECEDENCE: Final[tuple[str, ...]] = (
    "config.yaml",
    "config.yml",
    "config.json",
    "config.py",
    "configs",
    "params.yaml",
    "hyperparameters.json",
    "train.py",
    "training.py",
    "main.py",
    "run.py",
    "pyproject.toml",
)

#: Keys that state how much work a whole run performs, in the order they are
#: trusted. An iteration count is more precise than an epoch count, which depends
#: on a dataset size that may not be stated anywhere.
WORK_SIZE_KEYS: Final[tuple[str, ...]] = (
    "max_iters",
    "max_steps",
    "total_steps",
    "num_train_epochs",
    "n_epochs",
    "epochs",
    "num_samples",
    "n_samples",
)

#: Import fingerprints that identify a compute framework.
FRAMEWORK_HINTS: Final[dict[str, tuple[str, ...]]] = {
    "pytorch": ("import torch", "from torch", "pytorch_lightning"),
    "tensorflow": ("import tensorflow", "from tensorflow", "import keras"),
    "jax": ("import jax", "from jax", "import flax"),
    "scikit-learn": ("import sklearn", "from sklearn"),
    "transformers": ("from transformers", "import transformers"),
    "diffusers": ("from diffusers", "import diffusers"),
    "vllm": ("from vllm", "import vllm"),
    "llama.cpp": ("llama_cpp", "llama-cpp-python"),
    "onnxruntime": ("import onnxruntime", "from onnxruntime"),
    "numpy": ("import numpy", "from numpy"),
    "pandas": ("import pandas", "from pandas"),
    "polars": ("import polars", "from polars"),
    "spark": ("pyspark", "from pyspark"),
    "ffmpeg": ("ffmpeg", "subprocess.*ffmpeg"),
}

#: Filenames whose presence suggests a workload shape. Checked in the order the
#: tuple lists, so a training script outranks a generic entry point.
ARCHETYPE_FILES: Final[tuple[tuple[str, frozenset[str]], ...]] = (
    ("training", frozenset({"train.py", "training.py", "finetune.py", "pretrain.py", "sft.py"})),
    (
        "inference",
        frozenset({"inference.py", "predict.py", "serve.py", "infer.py", "predictor.py"}),
    ),
    ("batch-pipeline", frozenset({"pipeline.py", "etl.py", "ingest.py", "dag.py", "flow.py"})),
    ("service", frozenset({"app.py", "server.py", "api.py", "index.ts", "index.js"})),
    ("command-line-tool", frozenset({"cli.py", "__main__.py", "cli.js", "cli.ts"})),
)

#: Work-size keys that, on their own, say the repository trains something.
_TRAINING_KEYS: Final[frozenset[str]] = frozenset(
    {"max_iters", "max_steps", "total_steps", "num_train_epochs", "n_epochs", "epochs"}
)

#: Entry points to try for a capped slice of the real workload, in priority order.
ENTRYPOINT_NAMES: Final[tuple[str, ...]] = ("train.py", "main.py", "run.py", "benchmark.py")

#: Share of the total work a capped slice aims for. A thousandth is small enough
#: to finish on a laptop and large enough to get past start-up cost.
DEFAULT_CAP_FRACTION: Final[float] = 0.001

#: Per-file byte cap when reading configuration for the work size.
_CONFIG_READ_BYTES: Final[int] = 24_000


@dataclass(frozen=True, slots=True)
class WorkSizeCandidate:
    """One statement, somewhere in the repository, of how big a run is.

    Parameters
    ----------
    key : str
        The configuration key, such as ``max_iters``.
    value : float
        The number as written in the file.
    source : str
        ``path::key``, so the figure can be checked by opening the file.

    Examples
    --------
    >>> WorkSizeCandidate("max_iters", 600000.0, "config.py::max_iters").value
    600000.0
    """

    key: str
    value: float
    source: str


@dataclass(slots=True)
class ServiceHit:
    """One call to a paid service, with the line that gave it away.

    The line is kept because it is evidence. It goes into the report so a reader
    can confirm the detection, and into a catalogue contribution so a maintainer
    reviewing the pull request can see why the row was proposed.

    Parameters
    ----------
    key : str
        The service catalogue key, such as ``openai``.
    name : str
        The service's human name.
    path : str
        Repository-relative path of the file it was found in.
    line_number : int
        One-based line number.
    line : str
        The matching line, stripped.
    pricing_source_url : str
        Where that service publishes its prices.

    Examples
    --------
    >>> ServiceHit("openai", "OpenAI API", "app.py", 3, "import openai", "https://x.invalid").path
    'app.py'
    """

    key: str
    name: str
    path: str
    line_number: int
    line: str
    pricing_source_url: str = ""

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the hit for the model's external services block.

        Returns
        -------
        dict
            A mapping carrying the evidence alongside the identification.

        Examples
        --------
        >>> sorted(ServiceHit("k", "n", "p", 1, "l").to_mapping())
        ['detected_at', 'evidence', 'key', 'name']
        """
        return {
            "key": self.key,
            "name": self.name,
            "detected_at": f"{self.path}:{self.line_number}",
            "evidence": self.line,
        }


@dataclass(slots=True)
class RepositoryReading:
    """Everything reading the repository, without running it, established.

    Parameters
    ----------
    root : pathlib.Path
        The repository root that was read.
    languages : dict
        Language name to source-file count, most files first.
    archetype : str
        A coarse shape: ``training``, ``inference``, ``batch-pipeline``,
        ``service``, ``command-line-tool``, or ``unknown``.
    frameworks : tuple of str
        Compute frameworks found by import fingerprint.
    work_size : WorkSizeCandidate or None
        The size of a whole run, as stated in a file, or ``None``.
    work_size_candidates : tuple of WorkSizeCandidate
        Every statement of size that was found, in precedence order.
    work_size_conflicts : tuple of str
        Sentences naming the disagreements between those statements. A run capped
        against the wrong one would be off by whatever the two differ by, so the
        disagreement is surfaced rather than resolved quietly.
    services : tuple of ServiceHit
        Paid services the code calls, with evidence.
    has_tests : bool
        Whether a runnable test suite was found.
    test_command : tuple of str
        A bounded command that runs the suite, empty when there is none.
    entrypoint : str or None
        Repository-relative path of the script a capped slice would run.
    source_files : int
        How many source files were counted.

    Examples
    --------
    >>> RepositoryReading(root=Path("."), archetype="training").archetype
    'training'
    """

    root: Path
    languages: dict[str, int] = field(default_factory=dict)
    archetype: str = "unknown"
    frameworks: tuple[str, ...] = field(default_factory=tuple)
    work_size: WorkSizeCandidate | None = None
    work_size_candidates: tuple[WorkSizeCandidate, ...] = field(default_factory=tuple)
    work_size_conflicts: tuple[str, ...] = field(default_factory=tuple)
    services: tuple[ServiceHit, ...] = field(default_factory=tuple)
    has_tests: bool = False
    test_command: tuple[str, ...] = field(default_factory=tuple)
    entrypoint: str | None = None
    source_files: int = 0

    def dominant_language(self) -> str | None:
        """Return the language with the most source files.

        Returns
        -------
        str or None
            The language name, or ``None`` when no source file was found.

        Examples
        --------
        >>> RepositoryReading(Path("."), languages={"Python": 9, "Shell": 1}).dominant_language()
        'Python'
        """
        return next(iter(self.languages), None)

    def is_compute_bound(self) -> bool | None:
        """Return whether the work looks compute-bound, or ``None`` if unclear.

        A deep-learning framework in a training repository is a strong enough
        signal to say yes. Anything else declines to guess, because a wrong yes
        would licence a machine-to-machine projection that does not hold.

        Returns
        -------
        bool or None
            ``True``, or ``None`` when the static read cannot tell.

        Examples
        --------
        >>> RepositoryReading(Path("."), archetype="training",
        ...                   frameworks=("pytorch",)).is_compute_bound()
        True
        >>> RepositoryReading(Path("."), archetype="service").is_compute_bound() is None
        True
        """
        heavy = {"pytorch", "tensorflow", "jax", "vllm", "diffusers", "llama.cpp"}
        if self.archetype in {"training", "inference"} and set(self.frameworks) & heavy:
            return True
        return None

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the reading for the model's analysis block.

        Returns
        -------
        dict
            Prose and counts only. Nothing here is a cost, so nothing here is a
            quantity; the schema exempts the language byte counts by path.

        Examples
        --------
        >>> "archetype" in RepositoryReading(Path(".")).to_mapping()
        True
        """
        mapping: dict[str, Any] = {
            "evidence_source": "static",
            "archetype": self.archetype,
            "languages": list(self.languages),
            "language_file_counts": dict(self.languages),
        }
        if self.frameworks:
            mapping["frameworks"] = list(self.frameworks)
        compute_bound = self.is_compute_bound()
        if compute_bound is not None:
            mapping["compute_bound"] = compute_bound
        if self.work_size is not None:
            mapping["total_work"] = {
                "unit": self.work_size.key,
                "stated_as": f"{self.work_size.value:g}",
                "source": self.work_size.source,
            }
        if self.work_size_conflicts:
            mapping["total_work_conflicts"] = list(self.work_size_conflicts)
        if self.entrypoint:
            mapping["entrypoint"] = self.entrypoint
        mapping["has_tests"] = self.has_tests
        return mapping


def _iter_source_files(root: Path):
    """Yield the repository's own source files, skipping vendored trees.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Yields
    ------
    pathlib.Path
        Files that are part of the code under study.

    Examples
    --------
    >>> any(p.suffix == ".py" for p in _iter_source_files(Path(".")))
    True
    """
    for path in root.rglob("*"):
        if any(part in SKIPPED_DIRECTORIES for part in path.parts):
            continue
        if path.is_file():
            yield path


def detect_languages(root: Path) -> dict[str, int]:
    """Count source files per language, most files first.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    dict
        Language name to file count, in descending order of count.

    Examples
    --------
    >>> "Python" in detect_languages(Path("."))
    True
    """
    counts: dict[str, int] = {}
    for path in _iter_source_files(root):
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def detect_archetype(root: Path, languages: dict[str, int]) -> str:
    """Return a coarse label for the shape of work the repository does.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.
    languages : dict
        The language counts, used only as a last resort.

    Returns
    -------
    str
        One of the archetype labels, or ``unknown``.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "train.py").write_text("pass", encoding="utf-8")
    ...     detect_archetype(Path(folder), {"Python": 1})
    'training'
    """
    present = {path.name.lower() for path in _iter_source_files(root)}
    for label, names in ARCHETYPE_FILES:
        if present & names:
            return label
    if "Python" in languages and ("setup.py" in present or "pyproject.toml" in present):
        return "library"
    return "unknown"


def detect_frameworks(root: Path) -> tuple[str, ...]:
    """Return the compute frameworks the repository imports.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple of str
        Framework names, in catalogue order.

    Examples
    --------
    >>> isinstance(detect_frameworks(Path(".")), tuple)
    True
    """
    found: list[str] = []
    blobs: list[str] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SCANNED_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_SCANNED_BYTES:
                continue
            blobs.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    blob = "\n".join(blobs)
    for name, hints in FRAMEWORK_HINTS.items():
        if any(hint in blob for hint in hints):
            found.append(name)
    return tuple(found)


def _config_rank(relative_path: str) -> int:
    """Return how far a file is trusted to state the size of a run.

    Parameters
    ----------
    relative_path : str
        Repository-relative path.

    Returns
    -------
    int
        A smaller number means more trusted. Files not named in
        :data:`CONFIG_FILE_PRECEDENCE` rank after all of them.

    Examples
    --------
    >>> _config_rank("config.py") < _config_rank("train.py")
    True
    >>> _config_rank("some/other.py") == len(CONFIG_FILE_PRECEDENCE)
    True
    """
    lowered = relative_path.lower()
    for rank, name in enumerate(CONFIG_FILE_PRECEDENCE):
        if lowered == name or lowered.endswith(f"/{name}") or f"/{name}/" in f"/{lowered}/":
            return rank
    return len(CONFIG_FILE_PRECEDENCE)


def find_work_size(
    root: Path,
) -> tuple[WorkSizeCandidate | None, tuple[WorkSizeCandidate, ...], tuple[str, ...]]:
    """Find every statement of how much work a whole run performs.

    Precedence is documented and applied in this order: the file's rank in
    :data:`CONFIG_FILE_PRECEDENCE` first, then the key's rank in
    :data:`WORK_SIZE_KEYS`, then the path alphabetically so the result does not
    depend on filesystem ordering. When two files state different sizes for the
    same key, that disagreement is returned rather than settled, because capping a
    measured slice against the wrong one is off by however much they differ.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple
        The chosen candidate or ``None``, every candidate in precedence order, and
        a sentence for each disagreement found.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     here = Path(folder)
    ...     _ = (here / "config.py").write_text("max_iters = 600000", encoding="utf-8")
    ...     _ = (here / "train.py").write_text("max_iters = 300", encoding="utf-8")
    ...     chosen, every, conflicts = find_work_size(here)
    ...     chosen.value, len(every), len(conflicts)
    (600000.0, 2, 1)
    """
    candidates: list[WorkSizeCandidate] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in {".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:_CONFIG_READ_BYTES]
        except OSError:
            continue
        relative = str(path.relative_to(root))
        for key in WORK_SIZE_KEYS:
            pattern = re.compile(
                rf'(?<![\w.]){re.escape(key)}["\']?\s*[=:]\s*([0-9][0-9_]*)', re.IGNORECASE
            )
            match = pattern.search(text)
            if not match:
                continue
            value = float(match.group(1).replace("_", ""))
            if value > 0:
                candidates.append(WorkSizeCandidate(key, value, f"{relative}::{key}"))

    candidates.sort(
        key=lambda item: (
            _config_rank(item.source.split("::", 1)[0]),
            WORK_SIZE_KEYS.index(item.key) if item.key in WORK_SIZE_KEYS else len(WORK_SIZE_KEYS),
            item.source,
        )
    )

    conflicts: list[str] = []
    by_key: dict[str, list[WorkSizeCandidate]] = {}
    for candidate in candidates:
        by_key.setdefault(candidate.key, []).append(candidate)
    for key, group in by_key.items():
        values = {candidate.value for candidate in group}
        if len(values) > 1:
            listed = "; ".join(f"{item.source} says {item.value:g}" for item in group)
            conflicts.append(
                f"{key} is stated more than once and the statements disagree ({listed}). "
                f"{group[0].source} was used; check it is the one a real run reads."
            )

    return (candidates[0] if candidates else None), tuple(candidates), tuple(conflicts)


def _is_prose_line(line: str) -> bool:
    """Return whether a line is a comment or documentation rather than code.

    Service detection reads source files line by line, and a line that merely
    talks about a service is not a line that calls one. Skipping comments and
    documentation markers is what stops this package's own description of the
    services catalogue from being reported as a repository full of paid APIs.

    Parameters
    ----------
    line : str
        One line of source.

    Returns
    -------
    bool
        ``True`` when the line opens with a comment or documentation marker.

    Examples
    --------
    >>> _is_prose_line("    # from openai import OpenAI")
    True
    >>> _is_prose_line("from openai import OpenAI")
    False
    >>> _is_prose_line("    >>> import openai")
    True
    """
    stripped = line.lstrip()
    return stripped.startswith(PROSE_MARKERS)


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
                if any(str(hint) in line for hint in (row.get("detect") or [])):
                    hits[key] = ServiceHit(
                        key=key,
                        name=str(row.get("name") or key),
                        path=relative,
                        line_number=number,
                        line=line.strip()[:200],
                        pricing_source_url=str(row.get("pricing_source_url") or ""),
                    )
    return tuple(hits[key] for key in sorted(hits))


def detect_tests(root: Path) -> tuple[bool, tuple[str, ...]]:
    """Return whether the repository has a test suite, and how to run a slice of it.

    A repository's own tests are the safest representative thing to execute: they
    were written to be run, they exercise the real code paths, and they are
    expected to terminate.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple
        Whether tests were found, and a bounded command, empty when they were not.

    Examples
    --------
    >>> found, command = detect_tests(Path("."))
    >>> found and command[1:3] == ("-m", "pytest")
    True
    """
    has_tests = (root / "tests").is_dir() or (root / "test").is_dir()
    if not has_tests:
        has_tests = any(True for _ in root.rglob("test_*.py"))
    if not has_tests:
        return False, ()
    # sys.executable is the interpreter actually running, which is the only
    # spelling that is correct on macOS, Linux, and Windows alike. `-x` stops at
    # the first failure so a broken suite does not become a long slice.
    return True, (sys.executable, "-m", "pytest", "-q", "-x")


def find_entrypoint(root: Path) -> str | None:
    """Return the script a capped slice of the real workload would run.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    str or None
        A repository-relative filename, or ``None`` when none of the well-known
        entry points is present at the root.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "main.py").write_text("pass", encoding="utf-8")
    ...     find_entrypoint(Path(folder))
    'main.py'
    """
    for name in ENTRYPOINT_NAMES:
        if (root / name).is_file():
            return name
    return None


def capped_entrypoint_command(
    reading: RepositoryReading,
    *,
    cap_fraction: float = DEFAULT_CAP_FRACTION,
) -> tuple[tuple[str, ...], float] | tuple[None, None]:
    """Build a command that runs a known share of the real workload.

    The size comes from the repository's own configuration, so the fraction is a
    fact read from a file rather than a guess. The command passes the size key as
    a flag, which assumes the entry point parses flags in the usual way; when it
    does not, the run exits non-zero and the caller must say so in the model
    rather than quietly projecting from whatever did happen.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which must carry a work size and an entry point.
    cap_fraction : float, optional
        The share of the whole run to aim for.

    Returns
    -------
    tuple
        The command and the exact fraction it covers, or ``(None, None)`` when
        there is no entry point or no stated size to cap against.

    Examples
    --------
    >>> reading = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("max_iters", 600000.0, "config.py::max_iters"))
    >>> command, fraction = capped_entrypoint_command(reading)
    >>> command[-2:], round(fraction, 6)
    (('--max_iters', '600'), 0.001)
    """
    if reading.entrypoint is None or reading.work_size is None:
        return None, None
    total = reading.work_size.value
    capped = max(1, int(total * cap_fraction))
    fraction = min(capped / total, 1.0)
    command = (
        sys.executable,
        str(reading.root / reading.entrypoint),
        f"--{reading.work_size.key}",
        str(capped),
    )
    return command, fraction


def read_repository(path: str | Path, *, overlay: Path | None = None) -> RepositoryReading:
    """Read a repository and return everything the static pass established.

    Parameters
    ----------
    path : str or pathlib.Path
        The repository root.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory, for service detection.

    Returns
    -------
    RepositoryReading
        What was found.

    Raises
    ------
    AssertionError
        If the path is not a directory, reported through ``os_helper.check``.

    Examples
    --------
    >>> read_repository(".").source_files > 0
    True
    """
    root = Path(path).resolve()
    osh.check(osh.dir_exists(str(root)), f"Not a directory: {root}")

    languages = detect_languages(root)
    chosen, candidates, conflicts = find_work_size(root)
    has_tests, test_command = detect_tests(root)
    archetype = detect_archetype(root, languages)
    if archetype == "unknown" and chosen is not None and chosen.key in _TRAINING_KEYS:
        archetype = "training"

    for sentence in conflicts:
        osh.warning(sentence)

    return RepositoryReading(
        root=root,
        languages=languages,
        archetype=archetype,
        frameworks=detect_frameworks(root),
        work_size=chosen,
        work_size_candidates=candidates,
        work_size_conflicts=conflicts,
        services=detect_services(root, overlay=overlay),
        has_tests=has_tests,
        test_command=test_command,
        entrypoint=find_entrypoint(root),
        source_files=sum(languages.values()),
    )
