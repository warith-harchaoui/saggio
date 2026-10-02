"""What a static read found, and how sure it is of each thing.

Module summary
--------------
The four records a read produces. Each carries where it was found and, where it
matters, the caveat that it was found only in the code that tests the repository
-- which is not the same as being part of the workload, and is the difference
between a figure somebody can price and one they cannot.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tables import FOUND_ONLY_IN_SUITE
from .walking import is_test_path


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
    >>> from saggio.analyze.static.findings import WorkSizeCandidate
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
