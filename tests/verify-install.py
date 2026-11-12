#!/usr/bin/env python3
"""Check discovery installation in a disposable home and product."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="org-discovery-") as directory:
    home = Path(directory)
    product = home / "work/new-product"
    product.mkdir(parents=True)
    (product / "AGENTS.md").write_text("# Product instructions\nPreserve this.\n")
    codex = home / ".codex"
    codex.mkdir()
    override = codex / "AGENTS.override.md"
    override.write_text("# Existing global override\nPreserve this too.\n")
    command = [
        sys.executable,
        str(root / "bin/install.py"),
        "--home",
        str(home),
        "--project",
        str(product),
    ]
    environment = dict(os.environ)
    environment.pop("CODEX_HOME", None)
    subprocess.run(command, check=True, env=environment)
    first = {
        path: path.read_bytes()
        for path in (override, product / "AGENTS.md", home / "work/AGENTS.md")
    }
    subprocess.run(command, check=True, env=environment)
    assert all(path.read_bytes() == content for path, content in first.items())
    assert override.read_text().startswith(
        "# Existing global override\nPreserve this too.\n"
    )
    assert (
        (product / "AGENTS.md")
        .read_text()
        .startswith("# Product instructions\nPreserve this.\n")
    )
    assert not (codex / "AGENTS.md").exists()
    skill = home / ".agents/skills/product-environments"
    assert (
        skill.is_symlink() and skill.resolve() == root / "skills/product-environments"
    )
    assert (skill / "SKILL.md").is_file()
    skill.unlink()
    skill.mkdir()
    (skill / "SKILL.md").write_text("Unrelated existing skill")
    result = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert (skill / "SKILL.md").read_text() == "Unrelated existing skill"
    assert all(path.read_bytes() == content for path, content in first.items())
print(
    "PASS discovery installation, overrides, preservation, idempotence, and conflict handling"
)

with tempfile.TemporaryDirectory(prefix="org-discovery-invalid-") as directory:
    home = Path(directory)
    environment = dict(os.environ)
    environment.pop("CODEX_HOME", None)
    command = [
        sys.executable,
        str(root / "bin/install.py"),
        "--home",
        str(home),
        "--project",
        str(home / "missing-product"),
    ]
    result = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert (
        list(home.iterdir()) == []
    ), "Invalid project must be rejected before installation"
print("PASS invalid project leaves discovery unchanged")
