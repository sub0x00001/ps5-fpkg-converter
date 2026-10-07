"""Generate PyInstaller --hidden-import flags for the vendored engine.

Scans engine/backend with ast, collects every top-level import, drops modules
provided inside the backend tree itself, keeps stdlib modules and installed
third-party packages, and prints one module per line. Used by
scripts/build-portable.ps1 so the bundle never misses an engine dependency.
"""

import ast
import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "engine" / "backend"


def main() -> int:
    local = set()
    for p in BACKEND.rglob("*.py"):
        local.add(p.stem)
        if p.name == "__init__.py":
            local.add(p.parent.name)
    local.discard("__init__")
    local.discard("__main__")
    local.update({"ultra_core", "unrar", "app", "tests"})  # not bundled paths

    stdlib_names = set(sys.stdlib_module_names)

    found = set()
    for p in BACKEND.rglob("*.py"):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in local:
                        found.add(alias.name)  # full dotted path (submodules too)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module.split(".")[0] not in local:
                    found.add(node.module)

    def available(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    keep = set()
    for module in sorted(found):
        if module in ("__future__", "fcntl"):  # future import / POSIX-only
            continue
        if module.split(".")[0] in stdlib_names or available(module):
            keep.add(module)

    for module in sorted(keep):
        print(module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
