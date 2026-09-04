import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps/api/src/api"
CORE_MODULES = (
    "auth",
    "camera_policy",
    "deliveries",
    "entitlements",
    "errors",
    "events",
    "execution",
    "frame_processing",
    "media",
    "rate_limits",
    "workflow_validation",
)
PROTECTED_FILES = (
    *API.joinpath("domain").rglob("*.py"),
    *(API / "application" / f"{module}.py" for module in CORE_MODULES),
    *ROOT.joinpath("apps/inference/src/inference/application").rglob("*.py"),
)
OUTER_DEPENDENCIES = (
    "api.adapters",
    "api.entrypoints",
    "api.config",
    "api.main",
    "api.bootstrap",
    "inference.adapters",
    "inference.entrypoints",
    "inference.config",
    "sqlalchemy",
    "fastapi",
    "faststream",
    "redis",
    "httpx",
)


@pytest.mark.parametrize("path", PROTECTED_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_domain_and_application_core_do_not_import_infrastructure(path):
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    violations = [
        module
        for module in imports
        if any(module == outer or module.startswith(f"{outer}.") for outer in OUTER_DEPENDENCIES)
    ]

    assert violations == []
