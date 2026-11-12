# Shared environment validation

Validated on the Mac Studio on 2026-11-12.

- Two Git worktrees from one disposable repository ran independent full nginx/
  PostgreSQL stacks. Their Compose project IDs and dynamic host ports differed.
- A row written to one database was absent from the other. Both databases held
  their own distinct values afterward.
- Destroying one worktree removed its volumes while the other database and HTTP
  application stayed healthy. Both owned stacks were cleaned up afterward.
- Staging and production templates rendered with distinct project identities.
  Generated private configuration had mode 0600.
- Validation rejected global container names, fixed worktree host ports,
  source-mounted staging runtime, dirty stable builds and normal destruction of
  persistent staging data.
- Skill frontmatter, Python syntax, shell syntax, central links and unique stable
  port reservations passed validation.

Runtime evidence is in `/private/tmp/org-environment-validation-final.log`.
The disposable fixture is retained at
`/var/folders/0z/w3y6h7fx77jf8kbq2l40gj2c0000gn/T/org-environment-check-9oiv29jp`.
The runtime check used the already available `postgres:14-alpine` image. The
reference template defaults to PostgreSQL 17 and allows a product-specific image.

These checks validate the shared launcher and reference adapter. Existing product
adapters are marked pending in `projects.json`. Production-host deployment and
cross-platform release builds remain product-specific adoption work.

The discovery installer passed `python3 tests/verify-install.py`, including
existing global overrides, preserved product guidance, repeat installation,
conflicting skill preservation, and rejection of a missing product directory.
It installed the global instruction reference and user-level skill symlink on
this Mac. A subsequent instruction refresh included the managed global block
alongside AGBot's existing project guidance.

The shared repository versions the canonical skill and installer. Generated
global references live in the user's profile. Existing product instruction
references remain changes in those individual repositories.
