"""Pack src/coach/ into the notebook's BUNDLE line, so Colab gets the same package code.

  python3 scripts/build_bundle.py      run after changing anything under src/coach/
"""
import base64
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "pipeline.ipynb"


def bundle() -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted((ROOT / "src" / "coach").rglob("*.py")):
            zf.write(path, path.relative_to(ROOT).as_posix())
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    nb = json.loads(NOTEBOOK.read_text())
    cell = next(c for c in nb["cells"] if c.get("id") == "c02")
    lines = "".join(cell["source"]).splitlines(keepends=True)
    at = next(i for i, line in enumerate(lines) if line.startswith("BUNDLE = "))
    lines[at] = f'BUNDLE = "{bundle()}"\n'
    cell["source"] = lines
    NOTEBOOK.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
    print(f"wrote the bundle ({len(lines[at]) // 1024} KB) into {NOTEBOOK.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
