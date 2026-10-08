"""
Generate learner templates from a module's solutions.

    python3 make_templates.py <module_dir> <hints.py>

For every file named in HINTS, reads <module_dir>/solutions/<file> and writes
<module_dir>/<file>: each listed function keeps its signature and docstring, its body is
replaced by a `# TODO: <hint>` line and `raise NotImplementedError("<qualname>")`.
Everything else (imports, constants, helpers you did not list) is copied unchanged.

hints.py defines:
    HINTS = {"file.py": {"function_or_Class.method": "one-line graded hint", ...}, ...}

Fails if a listed function does not exist, and checks the output still parses.
Templates are regenerated, never hand-edited: change the solution or the hint instead.
"""
import ast
import importlib.util
import sys
from pathlib import Path

# Importing `_build/hints.py` through importlib would otherwise leave a
# __pycache__ directory inside the module's _build/; audits require a clean tree.
sys.dont_write_bytecode = True


def qualname(node, parents):
    return ".".join([p.name for p in parents if isinstance(p, ast.ClassDef)] + [node.name])

def make(src: Path, dst: Path, hints: dict):
    text = src.read_text()
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    edits, found = [], set()
    def visit(node, parents):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = qualname(child, parents)
                if q in hints:
                    found.add(q)
                    body = child.body
                    has_doc = isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str)
                    first = body[1] if has_doc and len(body) > 1 else (None if has_doc else body[0])
                    indent = " " * (child.col_offset + 4)
                    hint_lines = f"{indent}# TODO: {hints[q]}\n"
                    stub = hint_lines + f'{indent}raise NotImplementedError("{q}")\n'
                    if first is None:  # docstring-only body
                        edits.append((body[0].end_lineno, body[0].end_lineno, stub))
                    else:
                        edits.append((first.lineno - 1, child.end_lineno, stub))
            visit(child, parents + [child] if isinstance(child, ast.ClassDef) else parents)
    visit(tree, [])
    missing = set(hints) - found
    if missing:
        sys.exit(f"{src.name}: functions not found {missing}")
    for start, end, stub in sorted(edits, reverse=True):
        lines[start:end] = [stub]
    out = "".join(lines)
    ast.parse(out)
    dst.write_text(out)

def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    root = Path(argv[0])
    spec = importlib.util.spec_from_file_location("hints", argv[1])
    hints_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hints_mod)
    for name, hints in hints_mod.HINTS.items():
        make(root / "solutions" / name, root / name, hints)
        print("template", name)


if __name__ == "__main__":
    main(sys.argv[1:])
