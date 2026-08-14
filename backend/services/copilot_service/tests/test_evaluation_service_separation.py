"""
Architectural boundary test (Batch 6 implementation prompt §15): the
Copilot evaluation harness must never import, or be imported by,
`evaluation_service` (Phase 8). This is checked structurally, against
the real source files, not just asserted in prose.
"""

import ast
from pathlib import Path

_COPILOT_EVALUATION_DIR = Path("backend/services/copilot_service/app/evaluation")
_COPILOT_EVALUATION_MODULE_PREFIX = "backend.services.copilot_service.app.evaluation"


def _imported_module_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_copilot_evaluation_package_never_imports_evaluation_service():
    py_files = list(_COPILOT_EVALUATION_DIR.glob("*.py"))
    assert py_files, "expected to find the evaluation package's own Python files"

    offending = []
    for py_file in py_files:
        for module_name in _imported_module_names(py_file):
            if "evaluation_service" in module_name:
                offending.append((str(py_file), module_name))

    assert offending == [], f"copilot_service evaluation harness must never import evaluation_service: {offending}"


def test_evaluation_service_never_imports_the_copilot_evaluation_harness():
    evaluation_service_dir = Path("backend/services/evaluation_service")
    py_files = list(evaluation_service_dir.rglob("*.py"))
    assert py_files, "expected to find evaluation_service's own Python files"

    offending = []
    for py_file in py_files:
        if "__pycache__" in py_file.parts:
            continue
        for module_name in _imported_module_names(py_file):
            if module_name.startswith(_COPILOT_EVALUATION_MODULE_PREFIX) or "copilot_service" in module_name:
                offending.append((str(py_file), module_name))

    assert offending == [], f"evaluation_service must never depend on copilot_service: {offending}"
