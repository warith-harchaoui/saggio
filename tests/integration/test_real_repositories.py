"""Audits of repositories that look like repositories, checked answer by answer.

Every other test here builds the smallest input that exercises one rule. That is
how a tool ends up reporting fourteen compute frameworks to a project that
imports none: each rule was right, and nobody ran the whole thing against
something shaped like real code and read the reply.

A real repository has a suite, a README that names technologies it does not use,
a vendored directory, and a language the archetype table has never heard of. The
repositories below have all four, and the assertions are about the whole answer:
what was found, and just as much, what was not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.auditor import AuditOptions, audit
from saggio.model import validate

ROOT = Path(__file__).resolve().parents[2]


def static_options(**kwargs) -> AuditOptions:
    kwargs.setdefault("run", False)
    kwargs.setdefault("use_llm", False)
    return AuditOptions(**kwargs)


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- Four repositories, each shaped like one --------------------------------


@pytest.fixture
def python_training_repository(tmp_path: Path) -> Path:
    """A training project whose suite and prose name things it does not use."""
    root = tmp_path / "trainer"
    write(root, "train.py", "import torch\nfrom torch import nn\n\nmax_iters = 600000\n")
    write(root, "model.py", "import torch.nn.functional as F\n")
    write(
        root,
        "README.md",
        "# trainer\n\nCompared against TensorFlow and JAX. We could import torch\n"
        "differently one day. Runs ffmpeg nowhere.\n",
    )
    write(root, "tests/conftest.py", "max_iters = 10\n")
    write(root, "tests/test_train.py", "import pytest\nimport tensorflow\n")
    write(root, ".venv/lib/site-packages/vllm/__init__.py", "import vllm\n")
    return root


@pytest.fixture
def typescript_service_repository(tmp_path: Path) -> Path:
    """A service in TypeScript, with a suite beside it."""
    root = tmp_path / "service"
    write(root, "src/index.ts", 'import express from "express";\nexport const app = express();\n')
    write(root, "src/api.ts", 'import OpenAI from "openai";\nconst client = new OpenAI();\n')
    write(root, "src/__tests__/api.test.ts", 'import { app } from "../index";\n')
    write(root, "node_modules/openai/index.js", 'require("openai");\n')
    return root


@pytest.fixture
def go_tool_repository(tmp_path: Path) -> Path:
    """A command-line tool in a language the archetype table has never heard of."""
    root = tmp_path / "tool"
    write(root, "main.go", 'package main\n\nimport "fmt"\n\nfunc main() { fmt.Println("hi") }\n')
    write(root, "internal/run.go", "package internal\n")
    write(root, "main_test.go", "package main\n")
    return root


@pytest.fixture
def documentation_only_repository(tmp_path: Path) -> Path:
    """A repository that talks about frameworks and calls none of them."""
    root = tmp_path / "handbook"
    write(
        root,
        "guide.py",
        '"""How to pick between torch, tensorflow, jax and sklearn."""\n'
        "# import torch  # left for later\n"
        'FRAMEWORKS = ["torch", "tensorflow", "jax"]\n',
    )
    return root


# --- What the audit says about each -----------------------------------------


def test_a_training_repository_reports_what_it_imports_and_nothing_else(
    python_training_repository: Path,
) -> None:
    analysis = audit(python_training_repository, options=static_options(country="FR")).model.data[
        "analysis"
    ]
    # The README names TensorFlow and JAX, the suite imports TensorFlow, and a
    # vendored tree under .venv imports vLLM. None of them is this workload.
    assert analysis["frameworks"] == ["pytorch"]
    assert analysis.get("frameworks_in_suite_only") == ["tensorflow"]
    assert analysis["archetype"] == "training"


def test_a_training_repository_takes_its_size_from_its_own_code(
    python_training_repository: Path,
) -> None:
    # tests/conftest.py says ten iterations so that a test finishes. The real run
    # does six hundred thousand, and the two are not in disagreement.
    analysis = audit(python_training_repository, options=static_options(country="FR")).model.data[
        "analysis"
    ]
    assert analysis["total_work"]["stated_as"] == "600000"
    assert "conftest" not in analysis["total_work"]["source"]
    assert "total_work_conflicts" not in analysis


def test_a_typescript_service_is_read_as_a_service_in_typescript(
    typescript_service_repository: Path,
) -> None:
    model = audit(typescript_service_repository, options=static_options(country="FR")).model.data
    assert "TypeScript" in model["analysis"]["languages"]
    assert model["analysis"]["archetype"] == "service"
    # The API call is in src/api.ts, not in the suite, so it is priced as work.
    services = model.get("external_services", [])
    assert [service["key"] for service in services] == ["openai"]
    assert "caveat" not in services[0]


def test_a_language_the_table_does_not_know_is_not_guessed_at(
    go_tool_repository: Path,
) -> None:
    # The honest answer for a Go repository is that the shape was not established.
    # A guess here would be the one thing this package exists not to do.
    model = audit(go_tool_repository, options=static_options(country="FR")).model.data
    assert "Go" in model["analysis"]["languages"]
    assert model["analysis"]["archetype"] == "unknown"
    assert model["unit_of_work"]["status"] in {"placeholder", "TODO"}


def test_a_repository_that_only_talks_about_frameworks_uses_none(
    documentation_only_repository: Path,
) -> None:
    analysis = audit(
        documentation_only_repository, options=static_options(country="FR")
    ).model.data["analysis"]
    assert "frameworks" not in analysis
    assert "frameworks_in_suite_only" not in analysis


@pytest.mark.parametrize(
    "repository",
    [
        "python_training_repository",
        "typescript_service_repository",
        "go_tool_repository",
        "documentation_only_repository",
    ],
)
def test_every_one_of_them_produces_a_model_that_passes_its_own_rules(
    repository: str, request: pytest.FixtureRequest
) -> None:
    root = request.getfixturevalue(repository)
    result = audit(root, options=static_options(country="FR"))
    assert validate(result.model).ok


# --- And the repository this package lives in --------------------------------


def test_auditing_this_repository_does_not_invent_a_machine_learning_project() -> None:
    # This is the regression guard for the defect that prompted the whole family
    # of tests above: reading this package used to report PyTorch, TensorFlow,
    # JAX, vLLM, llama.cpp and Spark, because its own detector table spells those
    # names out and its own fixtures write them into temporary files.
    analysis = audit(ROOT, options=static_options(country="FR")).model.data["analysis"]
    invented = {"pytorch", "tensorflow", "jax", "vllm", "llama.cpp", "spark", "transformers"}
    assert not invented & set(analysis.get("frameworks", []))
    assert not invented & set(analysis.get("frameworks_in_suite_only", []))


def test_auditing_this_repository_produces_a_model_that_passes_its_own_rules() -> None:
    result = audit(ROOT, options=static_options(country="FR"))
    assert validate(result.model).ok
    # Every service and model this package appears to call is named in a test.
    for entry in result.model.data.get("external_services", []) + result.model.data.get(
        "models_called", []
    ):
        assert "caveat" in entry, f"{entry} is reported as workload and is not"


def test_a_cloned_repository_says_whose_machine_the_deployment_block_describes(
    python_training_repository: Path,
) -> None:
    # Auditing a URL records the auditing machine, which is almost never where the
    # code runs. A reader taking a laptop's core count for a training cluster's
    # would carry that mistake into every energy figure below it.
    result = audit(
        python_training_repository,
        options=static_options(country="FR"),
        origin="https://github.com/someone/their-project",
    )
    provenance = result.model.data["deployment"]["machine_provenance"]
    assert "ran the audit" in provenance
    assert "github.com/someone/their-project" in provenance


def test_auditing_a_directory_claims_nothing_about_whose_machine_it_is(
    python_training_repository: Path,
) -> None:
    result = audit(python_training_repository, options=static_options(country="FR"))
    assert "machine_provenance" not in result.model.data["deployment"]
