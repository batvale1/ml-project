"""Execute the EDA notebook with a fresh, project-local Jupyter kernel."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", choices=("root", "notebooks"), default="root")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run with .venv/Scripts/python.exe (Windows) or .venv/bin/python.")

    directories = {
        "IPYTHONDIR": "ipython",
        "JUPYTER_CONFIG_DIR": "jupyter/config",
        "JUPYTER_DATA_DIR": "jupyter/data",
        "JUPYTER_RUNTIME_DIR": "jupyter/runtime",
        "MPLCONFIGDIR": "matplotlib",
    }
    for variable, directory in directories.items():
        target = ROOT / ".local" / directory
        target.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(target)

    # Install only into the active environment, never into the user's profile.
    subprocess.run(
        [sys.executable, "-m", "ipykernel", "install", "--prefix", sys.prefix,
         "--name", "review-decoder", "--display-name", "Python (Review Decoder)"],
        check=True, capture_output=True, text=True,
    )

    import nbformat
    from nbclient import NotebookClient

    path = ROOT / "notebooks" / "01_eda.ipynb"
    notebook = nbformat.read(path, as_version=4)
    working_directory = ROOT if args.cwd == "root" else ROOT / "notebooks"
    client = NotebookClient(
        notebook, timeout=180, kernel_name="review-decoder",
        resources={"metadata": {"path": str(working_directory)}},
    )
    try:
        client.execute()
    except Exception:
        nbformat.write(notebook, ROOT / ".local" / "failed-eda.ipynb")
        raise
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(output.output_type == "error" for cell in code_cells for output in cell.outputs)
    nbformat.write(notebook, path)
    validation = {
        "fresh_kernel": True,
        "executed_code_cells": len(code_cells),
        "error_outputs": 0,
        "notebook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    target = ROOT / "reports" / "tables" / "execution.json"
    target.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(f"Executed {len(code_cells)} code cells without errors (cwd={args.cwd}).")
    print("Saved notebooks/01_eda.ipynb and reports/ artifacts.")


if __name__ == "__main__":
    main()
