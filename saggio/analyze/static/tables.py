"""What this reader knows before it opens a file.

Module summary
--------------
Every table the static read consults: which extension is which language, which
directories hold a suite rather than a workload, which filenames carry a run's
configuration and in what order they are trusted, and the patterns that say a
framework is being called rather than merely mentioned.

They are data, kept apart from the code that reads with them. In the single file
this came from they were scattered through sixteen hundred lines, some above the
first function and some between the last two, so a reader asking "why did it
decide that" -- which is nearly always a question about a table -- had to go
hunting for the answer.

``FRAMEWORK_PATTERNS`` is built rather than written, so the small function that
builds it sits here too: it makes a table rather than reading one.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import re
from typing import Final

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


#: Entry points to try for a capped slice of the real workload, in priority order.
ENTRYPOINT_NAMES: Final[tuple[str, ...]] = ("train.py", "main.py", "run.py", "benchmark.py")


#: What a script that is meant to be run looks like from the outside. The guard
#: is the one honest signal: a module written to be imported does not have it,
#: and a module that has it was written to be executed.
_RUNS_ITSELF: Final[re.Pattern[str]] = re.compile(
    r"""^if\s+__name__\s*==\s*['"]__main__['"]""", re.MULTILINE
)


#: Per-file byte cap when reading configuration for the work size.
_CONFIG_READ_BYTES: Final[int] = 24_000


#: Work-size keys that, on their own, say the repository trains something.
_TRAINING_KEYS: Final[frozenset[str]] = frozenset(
    {"max_iters", "max_steps", "total_steps", "num_train_epochs", "n_epochs", "epochs"}
)


#: Share of the total work a capped slice aims for. A thousandth is small enough
#: to finish on a laptop and large enough to get past start-up cost.
DEFAULT_CAP_FRACTION: Final[float] = 0.001


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


#: Said of a service or a model whose only evidence line is in the suite. It is
#: reported rather than dropped, and it is flagged rather than counted, because
#: the suite calling an API is not the workload calling it.
FOUND_ONLY_IN_SUITE: Final[str] = (
    "Found only in the code that tests this repository, so it may not be part of "
    "the workload. Confirm before pricing it."
)
