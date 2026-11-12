# Work environments

Shared product development and deployment conventions for worktree, staging,
and production environments. The contract is in [environments.md](environments.md).
Product adoption status and reserved stable ports are in [projects.json](projects.json).

## Install on a development machine

```sh
git clone git@github.com:vivasaayi/work-environments.git ~/work/.org
python3 ~/work/.org/bin/install.py
```

The installer preserves existing instructions, adds a managed reference to the
active global Codex instructions, and links the versioned skill into
`~/.agents/skills/product-environments`. Start a new Codex session after installing.
Set `--work-root`, `--codex-home`, or `--home` for another layout. Global guidance
applies to projects under the selected work root and explicitly adopting projects.

Codex reads global instructions before project instructions. Its project scan
starts at the repository root. The global reference therefore covers future
repositories under `~/work` even when their own instruction file is absent.
The user-level skill is available across repositories and selected for relevant
environment tasks. An instruction reference asks the agent to read the contract.

[Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [skill discovery](https://learn.chatgpt.com/docs/build-skills) describe these mechanisms.

## Adopt a new or existing product

```sh
python3 ~/work/.org/bin/install.py --project ~/work/new-product
```

This adds the shared reference to the project's active root instruction file.
Keep that file in the product's Git history so collaborators can discover the
convention. Other agents need support for `AGENTS.md` or their own instruction
entry point. Each development machine needs the shared checkout installed.

For an environment implementation task, adapt the files in `templates/` to the
product's actual services, migrations, seeds, and tests. The installer adds agent
discovery. Product-specific Compose adapters require implementation and validation.
Existing adoption work is recorded as pending in the registry.

## Update and verify

```sh
git -C ~/work/.org pull --ff-only
python3 ~/work/.org/bin/install.py
python3 ~/work/.org/tests/verify-install.py
python3 ~/work/.org/tests/verify-isolation.py
```

The skill symlink follows updates to this checkout. Re-run installation when the
checkout path or discovery instructions change. Product adapters evolve in their
own repositories. Record the shared commit alongside deployment evidence for
reproducibility. Runtime credentials and database volumes live outside this repo.
