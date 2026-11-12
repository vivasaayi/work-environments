#!/usr/bin/env python3
"""Install shared Codex discovery, preserving existing instructions."""

import argparse
import os
from pathlib import Path


START = "<!-- work-environments:start -->"
END = "<!-- work-environments:end -->"
ROOT = Path(__file__).resolve().parents[1]


def update_instructions(path, guidance):
    existing = path.read_text() if path.exists() else ""
    block = f"{START}\n{guidance.strip()}\n{END}"
    if START in existing or END in existing:
        if existing.count(START) != 1 or existing.count(END) != 1:
            raise ValueError(f"Ambiguous managed instruction block in {path}")
        start = existing.index(START)
        end_start = existing.index(END)
        if end_start < start:
            raise ValueError(f"Malformed managed instruction block in {path}")
        end = end_start + len(END)
        updated = existing[:start] + block + existing[end:]
    else:
        updated = (
            existing.rstrip() + ("\n\n" if existing.strip() else "") + block + "\n"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    if updated != existing:
        path.write_text(updated)
    print(path)


def instruction_file(directory):
    override = directory / "AGENTS.override.md"
    if override.exists() and override.read_text().strip():
        return override
    return directory / "AGENTS.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument(
        "--project", type=Path, help="Also add a project instruction reference"
    )
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    project = args.project.expanduser().resolve() if args.project else None
    if project and not project.is_dir():
        raise ValueError(f"Project directory does not exist: {project}")
    work = (args.work_root or home / "work").expanduser().resolve()
    codex = (
        (args.codex_home or Path(os.environ.get("CODEX_HOME", str(home / ".codex"))))
        .expanduser()
        .resolve()
    )
    source = ROOT / "skills/product-environments"
    destination = home / ".agents/skills/product-environments"
    # Check for a conflicting installation before editing any instructions.
    if destination.exists() or destination.is_symlink():
        if not destination.is_symlink() or destination.resolve() != source:
            raise ValueError(
                f"Existing skill at {destination}. Preserve it and choose its intended shared checkout first."
            )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=True)
    guidance = f"""## Organization development environments

For projects under `{work}`, and projects explicitly using this shared contract,
read `{ROOT / 'environments.md'}` when creating a project or changing worktree
setup, full-stack tests, database lifecycle, staging, or production deployment.
Use the `product-environments` skill at `{destination / 'SKILL.md'}` for that work.
The shared checkout is `{ROOT}`. Product repositories own their runtime adapters.
When creating a new product here, add a repository instruction reference with
`python3 {ROOT / 'bin/install.py'} --project <repository-path>`.
Follow project-specific instructions and explicit user directions.
"""
    update_instructions(instruction_file(codex), guidance)
    update_instructions(instruction_file(work), guidance)
    if project:
        project_guidance = (ROOT / "templates/AGENTS.fragment.md").read_text()
        update_instructions(instruction_file(project), project_guidance)
    print(
        f"Skill linked at {destination}. Start a new Codex session to load global guidance."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
