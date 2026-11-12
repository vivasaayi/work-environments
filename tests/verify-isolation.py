import json, os, pathlib, shutil, subprocess, tempfile, urllib.request

root = pathlib.Path(tempfile.mkdtemp(prefix="org-environment-check-"))
org = pathlib.Path(__file__).resolve().parents[1]
a = root / "primary"
b = root / "feature"
a.mkdir()
shutil.copytree(org / "templates/deploy", a / "deploy")
shutil.copytree(org / "templates/scripts", a / "scripts")
config = json.loads((a / "deploy/product.json").read_text())
config.update(
    id="org-validation", app_port=80, staging_port=29080, production_port=39080
)
(a / "deploy/product.json").write_text(json.dumps(config))
(a / "Dockerfile").write_text("FROM nginx:1.27-alpine\n")
env = {
    **os.environ,
    "WORK_ENV_STATE_ROOT": str(root / "state"),
    "POSTGRES_IMAGE": os.environ.get("POSTGRES_IMAGE", "postgres:17-alpine"),
}


def run(command, **kwargs):
    return subprocess.check_output(
        command, text=True, env=env, stderr=subprocess.STDOUT, **kwargs
    ).strip()


run(["git", "init", "-b", "main", str(a)])
run(["git", "-C", str(a), "add", "."])
run(
    [
        "git",
        "-C",
        str(a),
        "-c",
        "user.name=Environment validation",
        "-c",
        "user.email=validation@example.invalid",
        "commit",
        "-m",
        "Disposable environment fixture",
    ]
)
run(["git", "-C", str(a), "worktree", "add", "-b", "feature", str(b)])


def helper(repo, action, *extra, profile="worktree"):
    return run(
        [
            "python3",
            str(org / "bin/product-env.py"),
            "--repo",
            str(repo),
            profile,
            action,
            *extra,
        ]
    )


def identity(repo):
    return json.loads(helper(repo, "plan"))


def container(project, service):
    return run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--filter",
            f"label=com.docker.compose.service={service}",
            "--format",
            "{{.ID}}",
        ]
    )


def query(project, sql):
    return run(
        [
            "docker",
            "exec",
            container(project, "db"),
            "psql",
            "-U",
            "app",
            "-d",
            "app",
            "-Atc",
            sql,
        ]
    )


def endpoint(project):
    return "http://" + run(["docker", "port", container(project, "app"), "80/tcp"])


pa, pb = identity(a)["project"], identity(b)["project"]
assert pa != pb
print("Different worktree identities verified", flush=True)
try:
    for repo in [a, b]:
        helper(repo, "up")
    print("Both full stacks started", flush=True)
    url_a, url_b = endpoint(pa), endpoint(pb)
    assert url_a != url_b
    assert urllib.request.urlopen(url_a, timeout=10).status == 200
    assert urllib.request.urlopen(url_b, timeout=10).status == 200
    query(
        pa, "CREATE TABLE isolated(value text); INSERT INTO isolated VALUES ('alpha');"
    )
    assert query(pb, "SELECT to_regclass('public.isolated') IS NULL") == "t"
    query(
        pb, "CREATE TABLE isolated(value text); INSERT INTO isolated VALUES ('beta');"
    )
    assert query(pa, "SELECT value FROM isolated") == "alpha"
    assert query(pb, "SELECT value FROM isolated") == "beta"
    print("Distinct ports and independent PostgreSQL contents verified", flush=True)
    helper(a, "destroy")
    assert urllib.request.urlopen(url_b, timeout=10).status == 200
    assert query(pb, "SELECT value FROM isolated") == "beta"
    assert (
        run(
            [
                "docker",
                "volume",
                "ls",
                "--filter",
                f"label=com.docker.compose.project={pa}",
                "--format",
                "{{.Name}}",
            ]
        )
        == ""
    )
    print(
        "Destroying one worktree left the other healthy and removed only owned volumes",
        flush=True,
    )
    for profile in ["staging", "production"]:
        summary = json.loads(
            helper(a, "config", "--image", "nginx:1.27-alpine", profile=profile)
        )
        assert summary["project"] == f"org-validation-{profile}"
        file = root / "state" / summary["project"] / "environment.env"
        assert file.stat().st_mode & 0o777 == 0o600
    print("Stable Compose configs and private state verified", flush=True)
finally:
    for repo in [a, b]:
        try:
            helper(repo, "destroy")
        except Exception as e:
            print("Cleanup error", e, flush=True)
print("PASS; disposable evidence retained at " + str(root), flush=True)
