import json
import shutil
import subprocess
from pathlib import Path

REPO = "romanhlavac/ddd-accelerator"
BRANCH = "feature/github-native-backlog-governance"


def run(*args, input_text=None):
    p = subprocess.run(list(args), input=input_text, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    return p.stdout.strip()


def gh_json(*args, payload=None):
    if payload is None:
        out = run("gh", *args)
    else:
        out = run("gh", *args, "--input", "-", input_text=json.dumps(payload))
    return json.loads(out) if out else None


def create_blob(content):
    return gh_json("api", "--method", "POST", f"repos/{REPO}/git/blobs", payload={"content": content, "encoding": "utf-8"})["sha"]


def finalize_versioned_state():
    local_head = run("git", "rev-parse", "HEAD")
    ref = gh_json("api", f"repos/{REPO}/git/ref/heads/{BRANCH}")
    remote_head = ref["object"]["sha"]
    if remote_head != local_head:
        raise RuntimeError(f"Governance branch moved during restructuring: local={local_head} remote={remote_head}")
    commit = gh_json("api", f"repos/{REPO}/git/commits/{remote_head}")
    base_tree = commit["tree"]["sha"]

    workflow_path = Path(".github/workflows/reconcile-ddda-project-backlog.yml")
    workflow = workflow_path.read_text(encoding="utf-8")
    workflow = workflow.replace(
        "git diff --exit-code -- config/governance/github-bootstrap.json config/governance/backlog-policy.yaml docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md",
        "git diff --exit-code -- config/governance docs/roadmap scripts/platform/Reconcile-DDDAProjectBacklog.py",
    )
    workflow = workflow.replace("ddda-project-backlog-audit\n", "ddda-project-backlog-audit-v5\n")
    workflow = workflow.replace(".reports/cr-backlog-audit-v4/**", ".reports/cr-backlog-audit-v5/**")

    final_reconciler = Path("scripts/platform/Reconcile-DDDAProjectBacklog.v5.py").read_text(encoding="utf-8")

    files = {
        "config/governance/github-bootstrap.json": Path("config/governance/github-bootstrap.json").read_text(encoding="utf-8"),
        "config/governance/backlog-policy.yaml": Path("config/governance/backlog-policy.yaml").read_text(encoding="utf-8"),
        "docs/roadmap/README.md": Path("docs/roadmap/README.md").read_text(encoding="utf-8"),
        "docs/roadmap/backlog-index.md": Path("docs/roadmap/backlog-index.md").read_text(encoding="utf-8"),
        "docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md": Path("docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md").read_text(encoding="utf-8"),
        "docs/roadmap/work-packages/WP-11-eventstorming-multi-agent-orchestration.md": Path("docs/roadmap/work-packages/WP-11-eventstorming-multi-agent-orchestration.md").read_text(encoding="utf-8"),
        "docs/roadmap/work-packages/WP-11-eventstorming-methodology-workshop-runtime.md": Path("docs/roadmap/work-packages/WP-11-eventstorming-methodology-workshop-runtime.md").read_text(encoding="utf-8"),
        "docs/roadmap/work-packages/WP-12-miro-platform-environments-lifecycle.md": Path("docs/roadmap/work-packages/WP-12-miro-platform-environments-lifecycle.md").read_text(encoding="utf-8"),
        "docs/roadmap/work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md": Path("docs/roadmap/work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md").read_text(encoding="utf-8"),
        "scripts/platform/Reconcile-DDDAProjectBacklog.py": final_reconciler,
        ".github/workflows/reconcile-ddda-project-backlog.yml": workflow,
    }
    tree = []
    for path, content in files.items():
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": create_blob(content)})
    tree.append({"path": "scripts/platform/Reconcile-DDDAProjectBacklog.v5.py", "mode": "100644", "type": "blob", "sha": None})
    tree.append({"path": "scripts/platform/Restructure-DDDAWorkPackages.py", "mode": "100644", "type": "blob", "sha": None})

    new_tree = gh_json("api", "--method", "POST", f"repos/{REPO}/git/trees", payload={"base_tree": base_tree, "tree": tree})["sha"]
    new_commit = gh_json("api", "--method", "POST", f"repos/{REPO}/git/commits", payload={
        "message": "docs(governance): split platform work-package boundaries (#16)",
        "tree": new_tree,
        "parents": [remote_head],
    })["sha"]
    gh_json("api", "--method", "PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}", payload={"sha": new_commit, "force": False})

    run("git", "fetch", "origin", BRANCH)
    run("git", "reset", "--hard", f"origin/{BRANCH}")
    return new_commit


def main():
    run("python", "scripts/platform/Restructure-DDDAWorkPackages.py")
    run("python", "scripts/platform/Reconcile-DDDAProjectBacklog.v5.py")

    src = Path(".reports/cr-backlog-audit-v5")
    dst = Path(".reports/cr-backlog-audit-v4")
    dst.mkdir(parents=True, exist_ok=True)
    for name in ["audit.json", "audit.md"]:
        shutil.copy2(src / name, dst / name)

    commit = finalize_versioned_state()
    print(json.dumps({"status": "PASS", "final_governance_commit": commit}))


if __name__ == "__main__":
    main()
