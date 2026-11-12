# Product development and deployment environments

This is the shared convention for products under `~/work`. Product repositories
own their application architecture and runtime adapters. The shared convention
covers environment identity, storage, lifecycle commands, and promotion.
CI application integration is deferred. Operators and agents can run the same
shell commands manually now and invoke them from CI later.

The shared checkout has its own Git history. See [installation and agent
discovery](README.md) to install the global reference and reusable skill on a
development machine or add the reference to a new product.

## Three environments

| Environment | Source and runtime | Data | Access and lifetime |
| --- | --- | --- | --- |
| worktree | The current feature worktree, rebuilt for testing | Dedicated disposable database(s), credentials and artifacts per worktree | Dynamic loopback host ports by default; removed explicitly after work is merged or abandoned |
| staging | A clean default-branch revision built into an image | Stable per-product database and artifact volumes | Reserved staging endpoint on the Mac; persists across coding sessions |
| production | A versioned artifact that passed staging acceptance | Dedicated production database, credentials and artifacts | Reserved production endpoint on the remote PC; persists across deployments |

`main` and `master` are product configuration values. The currently inspected
products use `main`. Keep the monorepo when it fits the product. Multiple runtime
applications can share one repository.

## Product-owned layout and interface

```text
product/
  deploy/
    product.json
    compose.worktree.yaml
    compose.staging.yaml
    compose.production.yaml
  scripts/
    env
    build
    deploy
    test
```

Copy the reference adapter from `.org/templates` when adopting a product, then
adapt its services and commands. All required frontend, backend, database and
support services belong in its worktree stack. The reference Compose files use
PostgreSQL as an example. AGBot Geo Hub currently uses SQLite and needs a
SQLite-volume adapter until its separate PostgreSQL migration is implemented.
Mayyam also needs its existing MySQL/Kafka and other dependencies represented.

`deploy/product.json` provides the product ID, actual default branch, app service,
container port, stable host ports and bind addresses. Optional `database_service`
selects the database service (`db` by default; null for an embedded database).
Optional `migration_command` and `seed_command` are argv arrays executed through
`docker compose run --rm <app_service>`. Keep them aligned with the image's
entrypoint. A worktree seed should be idempotent and clearly label sample data.
Example optional commands are `["/app/bin/server", "migrate"]` and
`["/app/bin/server", "seed-demo"]` for an image that supports those arguments.

The product's `scripts/env` delegates to `.org/bin/product-env.py`. Set
`ORG_DEV_ROOT` when the shared installation lives elsewhere, including on the
remote production PC. Scripts use argv execution and do not source credentials
as shell code.

```sh
# Worktree bootstrap, build, migrate/seed via configured hooks, and start
bash scripts/env worktree plan
bash scripts/build worktree
bash scripts/env worktree up
bash scripts/env worktree status
bash scripts/test unit
bash scripts/test integration
bash scripts/test ui
bash scripts/env worktree stop

# Run from a clean checkout at the configured default branch
bash scripts/build staging
bash scripts/deploy staging
bash scripts/test staging

# Run on the production PC with a tested image available there
bash scripts/deploy production --image registry.example/product@sha256:THE_DIGEST
```

The registry hostname above is illustrative. Use the product's real registry.
Build/deploy wrappers are provided. Implement `scripts/test` using the product's
real unit, integration, browser and acceptance commands. Product adapters should
supply app healthchecks and verify their normal user journey after deployment.
The shared launcher's Compose `--wait` honors healthchecks that the adapter defines.

## Identity, networks and host ports

The shared launcher derives `<product>-worktree-<path-hash>` from the resolved
worktree path. Stable environments use `<product>-staging` and
`<product>-production`. Two worktrees of one repository therefore receive
separate Compose projects even when their branches have similar names.

Use project-scoped networks and volumes and omit fixed `container_name` values.
Use bridge networks. Database services communicate on their internal service
names and container ports, for example `db:5432`. Worktree app publication uses
host port 0, letting Docker select an available port. Set `worktree_bind` in the adapter for an explicitly requested remote development
endpoint, such as a Tailscale address. Get the assigned address
with `scripts/env worktree up` or `docker compose ... port app 8080`.

Reserve stable endpoints in [projects.json](projects.json) before adoption. The
launcher checks configured ports against these reservations.
Those reservations describe the new environment convention; existing running
services retain their current endpoints during adoption. Account for all host
ports a product exposes. Docker binding errors are resolved by choosing another
reservation or stopping an environment the task owns. Never take over a port by
terminating an unrelated project.

An internal database network can be combined with an egress-enabled application
network. Satellite processing and other provider clients need outbound access.
Avoid marking every network internal when workers need the internet.

## Database lifecycle

Each worktree bootstraps its own database using its own volume and generated
credentials. Schema migrations and sample seeds belong to product commands.
Run integration tests against that worktree database or a separately named test
database inside its project. Run UI tests against that worktree's frontend/API.
Host-side database tests can use an adapter-specific loopback dynamic DB port;
staging and production databases normally stay on their private networks.

Staging and production have independent persistent volumes and credentials.
Worktree bootstrap uses sample data or a deliberately prepared copy. Keep real
production data handling within the actual task's authorization.

After merge or abandonment, run `scripts/env worktree destroy` while the
worktree still exists. This removes that project's containers, networks and
named volumes. Check for product-specific external resources such as S3 test
prefixes, then remove the Git worktree separately. `stop` preserves volumes.
Persistent staging/production data removal is an explicit maintenance action,
separate from normal deployment.

Private per-environment configuration is stored under
`~/.local/share/work-environments/<compose-project>/environment.env` with
owner-only permissions. `WORK_ENV_STATE_ROOT` overrides that location. It stays
outside Git worktrees and survives source checkout changes. The small config
record is retained after worktree destruction so a deliberate reopening has
stable credentials; remove that owned directory when its record is no longer
needed. Keep production credentials in the deployment host's private state.

## Build and promotion

A worktree build belongs to that worktree. Staging/production runtime Compose
files consume an explicit image and avoid build definitions and source mounts.
The reference launcher builds stable artifacts only from a clean checkout at
the configured default branch. Deploying an already tested image can run from
an operations checkout using `--image`.

For manual staging deployment, build the merged default-branch revision, apply
migrations, start the stack, and run the product's staging acceptance checks.
Record commit, image digest, migration version and test results. Promote the
same artifact to the remote PC. Push/pull it through the actual registry or
transfer it with `docker image save`/`docker image load` where appropriate.
Source transfer alone is not evidence that production runs the tested artifact.

Back up stable database and artifact data before migrations as appropriate to
that product. Application rollback uses a retained image. Database recovery
follows the product's migration and backup procedure because application rollback
does not reverse schema changes. Add CI orchestration later around these scripts.

## Native desktop applications

Native macOS viewers and hardware tools can use host-native worktree builds.
Give each build a separate output directory and configure its API URL to the
matching environment. Build versioned native artifacts for staging and
production on the target-compatible toolchain. Keep runtime assets with those
artifacts and let their launcher select the appropriate backend. Use containers
for the server/test dependencies that support them.

## Shared-host operation

Compose resource names and private volumes provide logical separation. Docker
Desktop, build caches, CPU, RAM and disk remain shared. Use product-appropriate
build concurrency and resource limits, and scope cleanup to the current Compose
project. Machine-wide Docker pruning, daemon resets, shared database resets and
changes to other projects require an actual task that includes those operations.

## Adoption and verification

1. Inspect the product's actual runtime, data stores and tests.
2. Add its adapter files and thin scripts, preserving existing deployment data.
3. Start two disposable worktrees, verify distinct project names, ports,
   credentials and database contents, and destroy one while the other works.
4. Verify a staging restart/deployment preserves its data and runs the recorded
   image. Verify migrations and seeds can be retried as the product supports.
5. Exercise its UI against the correct API and database. Inspect native clients
   separately where applicable.
6. Record the deployment on the intended production host when that deployment
   is requested. Report adoption status accurately.

Existing projects are inventoried in `projects.json` and currently marked
`pending`. The central convention and templates do not convert their current
Compose stacks or database drivers by themselves.

## Verify the shared reference workflow

```sh
python3 ~/work/.org/tests/verify-isolation.py
```

This creates two disposable Git worktrees and full nginx/PostgreSQL stacks,
checks independent database contents and dynamic ports, destroys one while the
other remains usable, validates stable configuration, and cleans up its owned
containers and volumes. It retains the small fixture directory for inspection.
`POSTGRES_IMAGE` can select an available compatible PostgreSQL image; the initial
Mac verification used `postgres:14-alpine`. The template default is PostgreSQL 17.

## Toolchains and target architecture

The launcher uses Git, Python 3, Bash wrappers, and Docker Compose with `--wait`
support. Use a compatible Linux/WSL shell on a Windows deployment host. Confirm
the remote PC's OS and CPU architecture in its product adapter. Mac Studio ARM64
images may need a separate AMD64 build for an x86 production PC. Product build
scripts can use `docker buildx` for target-platform or multi-platform images and
record the tested platform digest. The shared `build` command is a single-host
Compose build; cross-platform release builds belong in the product build adapter.
