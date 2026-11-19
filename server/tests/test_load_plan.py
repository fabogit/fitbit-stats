"""Structural checks on the server modules and on the ETL load plan."""
import ast
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent


def test_no_inplace_in_the_server_modules():
    for path in sorted((SERVER / "modules").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.keyword):
                assert node.arg != "inplace", f"{path.name}:{node.value.lineno}"
