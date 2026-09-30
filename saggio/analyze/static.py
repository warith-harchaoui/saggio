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

#: Directory names that hold code which tests the repository rather than code the
#: repository runs. A suite is part of the project and is not part of the
#: workload, and the difference decides whether a framework named in a fixture is
#: evidence about what this thing costs to run.
TEST_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {"tests", "test", "testing", "spec", "specs", "__tests__", "e2e", "fixtures", "testdata"}
)

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

#: Directory names that say what the files under them are for. A repository that
#: keeps its configurations apart this way is telling you which of them a real run
#: reads, and reading an epoch count out of an evaluation directory is how an audit
#: of DINOv2 took the length of a training run from a config that scores a model
#: rather than one that trains it.
TRAINING_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {"train", "training", "pretrain", "pretraining", "finetune", "finetuning", "sft"}
)

#: Directories whose configurations describe something other than a production
#: run: scoring a model, timing it, or showing somebody how to call it.
SIDE_ERRAND_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {
        "eval",
        "evals",
        "evaluation",
        "benchmark",
        "benchmarks",
        "example",
        "examples",
        "demo",
        "demos",
        "tutorial",
        "tutorials",
        "doc",
        "docs",
        "notebook",
        "notebooks",
    }
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

#: How a model identifier is written where it is chosen, as an assignment:
#: ``model="gpt-4o"``, ``model_name = 'claude-3-5-sonnet'``. Only a string literal
#: is captured, because a variable would need the program to be run to know its
#: value, and this pass does not run anything.
MODEL_ASSIGNMENT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""\b(?:model|model_name|model_id|deployment_name)\s*=\s*(["'])([^"']{2,80})\1"""
)

#: The same identifier as an entry in a mapping: ``{"model": "gpt-4o"}`` in Python
#: or JSON, ``{ model: "gpt-4o" }`` in JavaScript, ``Model: "gpt-4o"`` in Go. The
#: first group says whether the key was written in quotes, which is what separates
#: a mapping from a type annotation in a language that has both.
MODEL_MAPPING_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""(["']?)\b(?:model|model_name|model_id|deployment_name)\1\s*:\s*(["'])([^"']{2,80})\2"""
)

#: Languages where ``name: "Something"`` outside a mapping is a type annotation
#: rather than a value. Python's ``def decode(model: "Whisper", mel: Tensor)`` is
#: a forward reference to a class, and reading it as a model being called is how
#: an audit of Whisper reported a model named Whisper.
_ANNOTATIONS_LOOK_LIKE_MAPPINGS: Final[frozenset[str]] = frozenset({".py", ".pyi"})

#: What a string literal is doing when one of these sits against it: being built,
#: not being named. ``model_name = "Body_" + name`` chooses no model, and reading
#: the fragment as one is how an audit of FastAPI reported a model named Body_.
_CONCATENATION: Final[tuple[str, ...]] = ("+", "%", ".join", ".format")

#: The modules whose import identifies a compute framework. Names, not lines: the
#: line that counts as an import is built below, because a substring search finds
#: the same words inside a string literal, a comment, or a table like this one,
#: and a tool that reports fourteen frameworks to a project that imports none is
#: not reading code, it is matching text.
FRAMEWORK_MODULES: Final[dict[str, tuple[str, ...]]] = {
    "pytorch": ("torch", "pytorch_lightning", "lightning"),
    "tensorflow": ("tensorflow", "keras"),
    "jax": ("jax", "flax"),
    "scikit-learn": ("sklearn",),
    "transformers": ("transformers",),
    "diffusers": ("diffusers",),
    "vllm": ("vllm",),
    "llama.cpp": ("llama_cpp",),
    "onnxruntime": ("onnxruntime",),
    "numpy": ("numpy",),
    "pandas": ("pandas",),
    "polars": ("polars",),
    "spark": ("pyspark",),
}

#: Frameworks that are run as a program rather than imported, and the shape a
#: call site gives them: the name quoted as an argument, or followed by a flag.
FRAMEWORK_INVOCATIONS: Final[dict[str, str]] = {
    "ffmpeg": r"""["']ffmpeg["']|\bffmpeg\s+-""",
}


def _framework_pattern(modules: tuple[str, ...]) -> re.Pattern[str]:
    """Build the pattern that recognises importing any of these modules.

    Python's ``import x`` and ``from x import`` both start a line, and JavaScript's
    ``require("x")`` and ``from "x"`` both quote the name. Anchoring to those two
    shapes is what separates code that uses a framework from prose that names one.

    Parameters
    ----------
    modules : tuple of str
        Module names, as the import statement spells them.

    Returns
    -------
    re.Pattern
        A multiline pattern matching an import of any of them.

    Examples
    --------
    >>> pattern = _framework_pattern(("torch",))
    >>> bool(pattern.search("import torch"))
    True
    >>> bool(pattern.search('    write("import torch")'))
    False
    """
    alternatives = "|".join(re.escape(module) for module in modules)
    return re.compile(
        rf"^[ \t]*(?:import|from)[ \t]+({alternatives})\b"
        rf"|(?:require\(|from\s+)[\"']({alternatives})[\"'/]",
        re.MULTILINE,
    )


#: One compiled pattern per framework, built once at import time.
FRAMEWORK_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    **{name: _framework_pattern(modules) for name, modules in FRAMEWORK_MODULES.items()},
    **{name: re.compile(source) for name, source in FRAMEWORK_INVOCATIONS.items()},
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


#: Said of a service or a model whose only evidence line is in the suite. It is
#: reported rather than dropped, and it is flagged rather than counted, because
#: the suite calling an API is not the workload calling it.
FOUND_ONLY_IN_SUITE: Final[str] = (
    "Found only in the code that tests this repository, so it may not be part of "
    "the workload. Confirm before pricing it."
)


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
        >>> ServiceHit("k", "n", "tests/test_x.py", 1, "l").to_mapping()["caveat"][:5]
        'Found'
        """
        mapping: dict[str, Any] = {
            "key": self.key,
            "name": self.name,
            "detected_at": f"{self.path}:{self.line_number}",
            "evidence": self.line,
        }
        if is_test_path(Path(self.path)):
            mapping["caveat"] = FOUND_ONLY_IN_SUITE
        return mapping


@dataclass(frozen=True, slots=True)
class ModelHit:
    """One model identifier the code names, with the line that names it.

    A price is per model, not per vendor: ``gpt-4o`` and ``gpt-4o-mini`` are the
    same API at an eightfold difference. So the audit has to know which model is
    called before it can price anything, and the only honest way to know from
    reading is to find the identifier written down.

    Parameters
    ----------
    identifier : str
        The string literal as the code spells it.
    path : str
        Repository-relative path of the file it was found in.
    line_number : int
        One-based line number.
    line : str
        The matching line, stripped, kept as the evidence.

    Examples
    --------
    >>> ModelHit("gpt-4o", "app.py", 12, 'model="gpt-4o"').identifier
    'gpt-4o'
    """

    identifier: str
    path: str
    line_number: int
    line: str

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the hit, evidence included.

        Returns
        -------
        dict
            A mapping naming the model and where it was found.

        Examples
        --------
        >>> sorted(ModelHit("m", "p", 1, "l").to_mapping())
        ['detected_at', 'evidence', 'model']
        >>> "caveat" in ModelHit("m", "tests/test_x.py", 1, "l").to_mapping()
        True
        """
        mapping: dict[str, Any] = {
            "model": self.identifier,
            "detected_at": f"{self.path}:{self.line_number}",
            "evidence": self.line,
        }
        if is_test_path(Path(self.path)):
            mapping["caveat"] = FOUND_ONLY_IN_SUITE
        return mapping


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
        Compute frameworks the workload imports, found by import fingerprint.
    frameworks_in_suite_only : tuple of str
        Frameworks that appear only in the code that tests the repository. Kept
        and reported rather than dropped, because a reader who expected to see
        one of them is owed the reason it is not counted.
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
    models : tuple of ModelHit
        Model identifiers the code names, with evidence. A price is per model, so
        this is what makes pricing an API call possible at all.
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
    frameworks_in_suite_only: tuple[str, ...] = field(default_factory=tuple)
    work_size: WorkSizeCandidate | None = None
    work_size_candidates: tuple[WorkSizeCandidate, ...] = field(default_factory=tuple)
    work_size_conflicts: tuple[str, ...] = field(default_factory=tuple)
    services: tuple[ServiceHit, ...] = field(default_factory=tuple)
    models: tuple[ModelHit, ...] = field(default_factory=tuple)
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
        if self.frameworks_in_suite_only:
            mapping["frameworks_in_suite_only"] = list(self.frameworks_in_suite_only)
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


def is_test_path(path: Path) -> bool:
    """Return whether a file is part of the suite rather than the workload.

    Parameters
    ----------
    path : pathlib.Path
        Any file inside the repository.

    Returns
    -------
    bool
        ``True`` when the file tests the repository rather than running it.

    Examples
    --------
    >>> is_test_path(Path("tests/unit/test_static.py"))
    True
    >>> is_test_path(Path("src/app.py"))
    False
    """
    if any(part.lower() in TEST_DIRECTORIES for part in path.parts):
        return True
    name = path.name.lower()
    return (
        name == "conftest.py"
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js"))
    )


def _iter_source_files(root: Path):
    """Yield the repository's own source files, skipping vendored trees.

    The workload's own code comes first and the suite that tests it comes last.
    Every detector below keeps the first place it saw a thing, so that ordering
    is what makes a service called from ``app.py`` outrank the same service named
    in a fixture, and what makes a hit whose evidence line is a test file mean
    that the suite is the only place it appears.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Yields
    ------
    pathlib.Path
        Files that are part of the code under study, workload before suite.

    Examples
    --------
    >>> any(p.suffix == ".py" for p in _iter_source_files(Path(".")))
    True
    """
    deferred: list[Path] = []
    for path in root.rglob("*"):
        # Only the path *inside* the repository decides the skip: a repository
        # legitimately cloned under ~/build or /tmp/dist must not read as empty
        # because an ancestor directory happens to share a vendored-tree name.
        inside = path.relative_to(root) if path.is_relative_to(root) else path
        if any(part in SKIPPED_DIRECTORIES for part in inside.parts):
            continue
        if not path.is_file():
            continue
        if is_test_path(path.relative_to(root) if path.is_relative_to(root) else path):
            deferred.append(path)
            continue
        yield path
    yield from deferred


def _iter_workload_files(root: Path):
    """Yield only the files the repository runs, leaving out the suite.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Yields
    ------
    pathlib.Path
        Files that are part of the workload.

    Examples
    --------
    >>> all(not is_test_path(p) for p in _iter_workload_files(Path("saggio")))
    True
    """
    for path in _iter_source_files(root):
        if is_test_path(path.relative_to(root) if path.is_relative_to(root) else path):
            return
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


def _filename_weight_at_depth(depth: int) -> float:
    """Return how much a file name counts as evidence at that depth.

    A file at the root is what the repository is about; the same name three
    directories down is a detail of how it is built. An ``app.py`` inside
    ``src/cli/`` is not a web service, and weighing it as one is how a
    command-line tool gets reported as a server.

    Parameters
    ----------
    depth : int
        How many directories separate the file from the root.

    Returns
    -------
    float
        One at the root, falling away below it.

    Examples
    --------
    >>> _filename_weight_at_depth(0) > _filename_weight_at_depth(2)
    True
    """
    return 1.0 / (1.0 + depth)


def declares_console_script(root: Path) -> bool:
    r"""Return whether the packaging metadata installs a command.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    bool
        ``True`` when ``pyproject.toml``, ``setup.py`` or ``package.json`` says
        the project installs an executable.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as folder:
    ...     _ = (Path(folder) / "pyproject.toml").write_text(
    ...         '[project.scripts]\\nthing = "thing:run"\\n', encoding="utf-8")
    ...     declares_console_script(Path(folder))
    True
    """
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            if "[project.scripts]" in pyproject.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            pass
    setup = root / "setup.py"
    if setup.is_file():
        try:
            if "console_scripts" in setup.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            pass
    package = root / "package.json"
    if package.is_file():
        try:
            return '"bin"' in package.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
    return False


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
    scores: dict[str, float] = {}
    present: set[str] = set()
    for path in _iter_workload_files(root):
        present.add(path.name.lower())
        relative = path.relative_to(root) if path.is_relative_to(root) else path
        for label, names in ARCHETYPE_FILES:
            if path.name.lower() in names:
                scores[label] = scores.get(label, 0.0) + _filename_weight_at_depth(
                    len(relative.parts) - 1
                )

    if declares_console_script(root):
        # Packaging metadata is a statement about what the thing is, where a file
        # name is an inference about it. A repository that installs a command is
        # a command, whatever a file three directories down happens to be called.
        scores["command-line-tool"] = scores.get("command-line-tool", 0.0) + 1.0

    if scores:
        order = [label for label, _ in ARCHETYPE_FILES]
        # Ties go to the earlier label, which is how a project that both trains
        # and serves is reported as the expensive one it is.
        return max(scores, key=lambda label: (scores[label], -order.index(label)))
    if "Python" in languages and ("setup.py" in present or "pyproject.toml" in present):
        return "library"
    return "unknown"


def detect_frameworks(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the frameworks the workload imports, and those only its suite names.

    A suite writes fixtures, and a fixture that writes ``import torch`` into a
    temporary file is not a repository that trains anything. Reading both at once
    is how a tool ends up reporting a dozen frameworks to a project that uses
    none, so the two are read apart and reported apart.

    Parameters
    ----------
    root : pathlib.Path
        The repository root.

    Returns
    -------
    tuple of (tuple of str, tuple of str)
        Frameworks the workload imports, then frameworks that appear only in the
        code that tests it. Both in catalogue order.

    Examples
    --------
    >>> workload, in_suite_only = detect_frameworks(Path("."))
    >>> isinstance(workload, tuple) and isinstance(in_suite_only, tuple)
    True
    """
    workload_blobs: list[str] = []
    suite_blobs: list[str] = []
    for path in _iter_source_files(root):
        if path.suffix.lower() not in _SCANNED_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > _MAX_SCANNED_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root) if path.is_relative_to(root) else path
        (suite_blobs if is_test_path(relative) else workload_blobs).append(text)

    workload = "\n".join(workload_blobs)
    suite = "\n".join(suite_blobs)
    found: list[str] = []
    in_suite_only: list[str] = []
    for name, pattern in FRAMEWORK_PATTERNS.items():
        if pattern.search(workload):
            found.append(name)
        elif pattern.search(suite):
            in_suite_only.append(name)
    return tuple(found), tuple(in_suite_only)


def _purpose_rank(relative_path: str) -> int:
    """Return how far a file's directory is trusted to state the length of a run.

    Only directory names are read, never the file's own name: a repository that
    separates ``configs/train`` from ``configs/eval`` is saying which of the two a
    real run reads, and that statement is worth more than any guess from a stem.

    Parameters
    ----------
    relative_path : str
        Repository-relative path.

    Returns
    -------
    int
        ``0`` under a training directory, ``2`` under an evaluation, benchmark or
        example one, ``1`` everywhere else. Smaller means more trusted.

    Examples
    --------
    >>> _purpose_rank("configs/train/vitg14.yaml")
    0
    >>> _purpose_rank("configs/ssl_default.yaml")
    1
    >>> _purpose_rank("configs/eval/linear.yaml")
    2
    """
    directories = {part.lower() for part in Path(relative_path).parts[:-1]}
    if directories & TRAINING_DIRECTORIES:
        return 0
    if directories & SIDE_ERRAND_DIRECTORIES:
        return 2
    return 1


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
    >>> _config_rank("tests/conftest.py") > _config_rank("some/other.py")
    True
    """
    lowered = relative_path.lower()
    # A suite states a size so that a test finishes quickly, which is the opposite
    # of what a real run does. It ranks below every file the workload owns, so it
    # only ever wins when the workload states no size at all.
    penalty = len(CONFIG_FILE_PRECEDENCE) + 1 if is_test_path(Path(relative_path)) else 0
    for rank, name in enumerate(CONFIG_FILE_PRECEDENCE):
        if lowered == name or lowered.endswith(f"/{name}") or f"/{name}/" in f"/{lowered}/":
            return rank + penalty
    return len(CONFIG_FILE_PRECEDENCE) + penalty


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
        lines = text.splitlines()
        for key in WORK_SIZE_KEYS:
            # The number may be written 600000, 600_000, or 6e5; stopping at the
            # mantissa would read 6e5 as six and cap the run at a millionth of
            # its size while still calling the figure file-sourced.
            pattern = re.compile(
                rf'(?<![\w.]){re.escape(key)}["\']?\s*[=:]\s*'
                r"([0-9][0-9_]*(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)",
                re.IGNORECASE,
            )
            for line in lines:
                if _is_prose_line(line):
                    # A commented-out size is prose about the code. Letting it
                    # win the precedence contest is exactly the silent-cap
                    # failure this pass exists to prevent.
                    continue
                match = pattern.search(line)
                if not match:
                    continue
                value = float(match.group(1).replace("_", ""))
                if value > 0:
                    candidates.append(WorkSizeCandidate(key, value, f"{relative}::{key}"))
                break

    candidates.sort(
        key=lambda item: (
            _config_rank(item.source.split("::", 1)[0]),
            _purpose_rank(item.source.split("::", 1)[0]),
            WORK_SIZE_KEYS.index(item.key) if item.key in WORK_SIZE_KEYS else len(WORK_SIZE_KEYS),
            item.source,
        )
    )

    chosen = candidates[0] if candidates else None
    conflicts: list[str] = []
    # A suite states a small size so that a test finishes, and the workload states
    # the real one. That is not a disagreement, it is the two files doing their
    # jobs, and reporting it as one buries the disagreements that matter.
    from_workload = [
        candidate
        for candidate in candidates
        if not is_test_path(Path(candidate.source.split("::", 1)[0]))
    ]
    considered = from_workload or candidates
    by_key: dict[str, list[WorkSizeCandidate]] = {}
    for candidate in considered:
        by_key.setdefault(candidate.key, []).append(candidate)
    for key, group in by_key.items():
        values = {candidate.value for candidate in group}
        if len(values) > 1:
            listed = "; ".join(f"{item.source} says {item.value:g}" for item in group)
            # Only one candidate in the whole repository is actually used, and it
            # may well belong to another key. Saying "was used" of each key's own
            # front-runner would name a figure nothing read.
            if chosen is not None and chosen.key == key:
                outcome = f"{chosen.source} was used; check it is the one a real run reads."
            elif chosen is not None:
                outcome = (
                    f"{group[0].source} takes precedence among them, but none of them "
                    f"was used: the size this read went with is {chosen.source} "
                    f"({chosen.value:g})."
                )
            else:
                outcome = f"{group[0].source} takes precedence among them."
            conflicts.append(
                f"{key} is stated more than once and the statements disagree ({listed}). {outcome}"
            )

    return chosen, tuple(candidates), tuple(conflicts)


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
        # Via the filtered walk, so a test file inside .venv or node_modules does
        # not make the tool run somebody else's suite as if it were this one's.
        has_tests = any(
            path.name.startswith("test_")
            for path in _iter_source_files(root)
            if path.suffix == ".py"
        )
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


#: How many differently sized slices a scaling series runs by default. Three is
#: the fewest that can produce a goodness of fit, and the fit is the whole point:
#: an exponent nobody can check is worth less than the assumption it replaced.
DEFAULT_SCALING_STEPS: Final[int] = 3

#: How much bigger each rung of the ladder is than the one below it. Four rather
#: than two for two reasons at once: it spans a factor of sixteen over three
#: rungs instead of four, which is what makes a curve distinguishable from a
#: line, and it costs less — the rungs below the top add 1/4 + 1/16 of it, so the
#: whole series is about 1.3 times the single slice it replaces.
DEFAULT_SCALING_GROWTH: Final[float] = 4.0


def scaling_ladder(
    reading: RepositoryReading,
    *,
    cap_fraction: float = DEFAULT_CAP_FRACTION,
    steps: int = DEFAULT_SCALING_STEPS,
    growth: float = DEFAULT_SCALING_GROWTH,
) -> tuple[tuple[tuple[str, ...], float, float], ...]:
    """Build several capped commands of increasing size, to measure the scaling.

    The top rung is the slice that would have been run anyway, so nothing about
    the cost figures changes by asking for a ladder: the rungs below it exist
    only to establish how the work grows, and they are small by construction.

    Sizes are integers because they are passed to somebody else's flag, so two
    rungs can collide after rounding on a repository whose stated size is small.
    Colliding rungs are dropped rather than run twice, which means a short ladder
    is a possible answer and the caller has to be ready for one: fewer than three
    distinct sizes licenses no exponent.

    Parameters
    ----------
    reading : RepositoryReading
        The static reading, which must carry a work size and an entry point.
    cap_fraction : float, optional
        The share of the whole run the largest rung aims for.
    steps : int, optional
        How many rungs to build, before collisions are dropped.
    growth : float, optional
        The factor between one rung and the next.

    Returns
    -------
    tuple
        One ``(command, fraction, size)`` triple per rung, smallest first, or an
        empty tuple when there is no entry point or no stated size to cap
        against.

    Examples
    --------
    >>> reading = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("max_iters", 600000.0, "config.py::max_iters"))
    >>> ladder = scaling_ladder(reading)
    >>> [size for _, _, size in ladder]
    [37.0, 150.0, 600.0]
    >>> ladder[-1][0][-2:]
    ('--max_iters', '600')

    A repository whose whole run is tiny cannot be cut three ways, and says so
    by returning fewer rungs than were asked for:

    >>> tiny = RepositoryReading(
    ...     root=Path("."), entrypoint="train.py",
    ...     work_size=WorkSizeCandidate("epochs", 2.0, "config.yaml::epochs"))
    >>> [size for _, _, size in scaling_ladder(tiny)]
    [1.0]

    >>> scaling_ladder(RepositoryReading(root=Path(".")))
    ()
    """
    if reading.entrypoint is None or reading.work_size is None:
        return ()
    if steps < 1 or growth <= 1.0:
        return ()

    total = reading.work_size.value
    rungs: dict[int, tuple[tuple[str, ...], float, float]] = {}
    for step in reversed(range(steps)):
        share = cap_fraction / (growth**step)
        capped = max(1, int(total * share))
        if capped in rungs:
            continue
        rungs[capped] = (
            (
                sys.executable,
                str(reading.root / reading.entrypoint),
                f"--{reading.work_size.key}",
                str(capped),
            ),
            min(capped / total, 1.0),
            float(capped),
        )
    return tuple(rungs[size] for size in sorted(rungs))


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

    frameworks, frameworks_in_suite_only = detect_frameworks(root)

    return RepositoryReading(
        root=root,
        languages=languages,
        archetype=archetype,
        frameworks=frameworks,
        frameworks_in_suite_only=frameworks_in_suite_only,
        work_size=chosen,
        work_size_candidates=candidates,
        work_size_conflicts=conflicts,
        services=detect_services(root, overlay=overlay),
        models=detect_models(root),
        has_tests=has_tests,
        test_command=test_command,
        entrypoint=find_entrypoint(root),
        source_files=sum(languages.values()),
    )
