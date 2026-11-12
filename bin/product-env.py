#!/usr/bin/env python3
"""Run a product's environment-specific Compose stack with a stable identity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("environment", choices=["worktree", "staging", "production"])
    parser.add_argument(
        "action",
        choices=[
            "plan",
            "config",
            "build",
            "up",
            "deploy",
            "status",
            "logs",
            "stop",
            "destroy",
            "migrate",
            "seed",
        ],
    )
    parser.add_argument("--image")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(git(Path(args.repo), "rev-parse", "--show-toplevel")).resolve()
    config = json.loads((root / "deploy/product.json").read_text())
    product = config["id"]
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", product):
        raise ValueError("product id must use lowercase letters, digits and dashes")
    profile = args.environment
    registry = Path(__file__).resolve().parent.parent / "projects.json"
    if registry.exists():
        reservations = json.loads(registry.read_text())["reservations"]
        for reservation in reservations:
            for target in ["staging", "production"]:
                port = config.get(f"{target}_port")
                reserved = reservation.get(f"{target}_port")
                if port is not None and reserved is not None:
                    if reservation["id"] == product and port != reserved:
                        raise ValueError(
                            f"{target} port differs from the central reservation for {product}"
                        )
                    if reservation["id"] != product and port == reserved:
                        raise ValueError(
                            f'{target} port {port} is reserved for {reservation["id"]}'
                        )
    suffix = (
        "-" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
        if profile == "worktree"
        else ""
    )
    project = f"{product}-{profile}{suffix}"
    state_root = (
        Path(
            os.environ.get(
                "WORK_ENV_STATE_ROOT",
                str(Path.home() / ".local/share/work-environments"),
            )
        )
        .expanduser()
        .resolve()
    )
    state = state_root / project
    compose_file = root / f"deploy/compose.{profile}.yaml"
    if not compose_file.is_file():
        raise ValueError(f"missing product adapter {compose_file}")
    if args.action == "destroy" and profile != "worktree":
        raise ValueError(
            "destroy is for worktree data; manage persistent staging/production data explicitly"
        )
    if args.action == "build" and profile != "worktree":
        branch = config["default_branch"]
        if git(root, "status", "--porcelain") or git(root, "rev-parse", "HEAD") != git(
            root, "rev-parse", branch
        ):
            raise ValueError(
                f"{profile} builds require a clean checkout at {branch}; deploy an existing image from other worktrees"
            )
    values = {}
    env_file = state / "environment.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                values[key] = value
    if (
        profile != "worktree"
        and args.action in ["up", "deploy"]
        and not (args.image or values.get("APP_IMAGE"))
    ):
        raise ValueError("supply --image with a tested commit-tagged image or digest")
    if args.image and any(char.isspace() for char in args.image):
        raise ValueError("image reference contains whitespace")
    values.update(
        {
            "PRODUCT_SOURCE": str(root),
            "APP_PORT": str(int(config["app_port"])),
            "BIND_ADDRESS": config.get(f"{profile}_bind", "127.0.0.1"),
            "PUBLISHED_PORT": (
                "0" if profile == "worktree" else str(int(config[f"{profile}_port"]))
            ),
        }
    )
    image = args.image or values.get("APP_IMAGE")
    if args.action == "build" or not image:
        image = args.image or (
            f"{product}-dev:{suffix[1:]}"
            if profile == "worktree"
            else f'{product}:{git(root, "rev-parse", "HEAD")}'
        )
    values["APP_IMAGE"] = image
    values.setdefault("POSTGRES_PASSWORD", secrets.token_hex(24))
    values.setdefault("PRODUCT_DOCKERFILE", config.get("dockerfile", "Dockerfile"))
    description = {
        "product": product,
        "environment": profile,
        "project": project,
        "source": str(root),
        "state": str(state),
        "compose": str(compose_file),
        "image": image,
    }
    if args.action == "plan":
        print(json.dumps(description, indent=2))
        return
    if not args.dry_run:
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(state, 0o700)
        if any("\n" in value or "\r" in value for value in values.values()):
            raise ValueError("environment values must be single-line")
        temporary = state / f"environment.{os.getpid()}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
        os.replace(temporary, env_file)
    child_env = {**os.environ, **values}
    base = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--project-directory",
        str(root),
        "--env-file",
        str(env_file),
    ]

    def compose(arguments, file=compose_file, capture=False):
        command = base + ["-f", str(file)] + arguments
        if args.dry_run:
            print(json.dumps(command))
            return ""
        return (
            subprocess.check_output(command, env=child_env, text=True)
            if capture
            else subprocess.run(command, env=child_env, check=True)
        )

    def hook(name):
        command = config.get(name)
        if command:
            if not isinstance(command, list) or not all(
                isinstance(item, str) for item in command
            ):
                raise ValueError(f"{name} must be an argument array")
            compose(["run", "--rm", config.get("app_service", "app")] + command)

    if not args.dry_run:
        rendered = json.loads(compose(["config", "--format", "json"], capture=True))
        for service in rendered.get("services", {}).values():
            if service.get("container_name") or service.get("network_mode") == "host":
                raise ValueError(
                    "product Compose must use project-scoped container names and bridge networks"
                )
            if profile != "worktree" and service.get("build"):
                raise ValueError(
                    "staging and production Compose must consume built images"
                )
            if profile == "worktree":
                for port in service.get("ports", []):
                    if str(port.get("published", "0")) not in ["", "0"]:
                        raise ValueError(
                            "worktree host ports must be assigned dynamically"
                        )
            else:
                for mount in service.get("volumes", []):
                    if mount.get("type") == "bind":
                        source = Path(mount["source"]).resolve()
                        if source == root or root in source.parents:
                            raise ValueError(
                                "stable runtime mounts must use deployment state outside the source checkout"
                            )
        for section in ["volumes", "networks"]:
            for resource in rendered.get(section, {}).values():
                if resource.get("external") or not resource.get("name", "").startswith(
                    project + "_"
                ):
                    raise ValueError(f"{section} must be scoped to {project}")
    if args.action == "config":
        # Resolved config contains credentials, so print only the safe environment summary.
        print(json.dumps(description, indent=2))
    elif args.action == "build":
        compose(["build"], root / "deploy/compose.worktree.yaml")
    elif args.action in ["up", "deploy"]:
        if profile == "worktree":
            compose(["build"])
        database = config.get("database_service", "db")
        if database:
            compose(["up", "-d", "--wait", database])
        hook("migration_command")
        if profile == "worktree":
            hook("seed_command")
        compose(["up", "-d", "--wait"])
        compose(["port", config.get("app_service", "app"), str(config["app_port"])])
    elif args.action in ["migrate", "seed"]:
        name = "migration_command" if args.action == "migrate" else "seed_command"
        if not config.get(name):
            raise ValueError(f"product adapter must define {name}")
        hook(name)
    elif args.action == "status":
        compose(["ps"])
    elif args.action == "logs":
        compose(["logs", "--tail", "100", "-f"])
    elif args.action == "stop":
        compose(["down"])
    elif args.action == "destroy":
        compose(["down", "--volumes", "--remove-orphans"])
        # Keep the small identity/config record so credentials are stable if reopened.


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"product-env: {error}", file=sys.stderr)
        sys.exit(1)
