---
name: product-environments
description: Implement or operate isolated worktree, staging, and production environments for products under ~/work, including product Compose files, scripts, database bootstrap, testing, and promotion. Use when changing those workflows.
---

Read the central environment contract at `${ORG_DEV_ROOT:-$HOME/work/.org}/environments.md`.
The installed global instructions identify the shared checkout when its location differs.
Inspect the product's instructions, existing Compose files, database support,
build entry points, and active environments before adapting it.

Use the three product-owned Compose files and the scripts/env interface in the
contract. Templates and the shared launcher are in that shared checkout.
Adapt service definitions to the real product, including every UI/backend and
required dependency. Preserve existing deployments during adoption.

Verify two worktrees can run together with separate data and host ports.
Check staging runs a specific built revision with persistent storage. Production
promotion consumes a tested image or native artifact. Report unimplemented
adapters and unverified deployments explicitly. CI integration is outside the
current request. Changes to a running production installation require task
scope that actually includes that deployment.
