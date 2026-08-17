import argparse
import json
import re
import subprocess
from pathlib import Path

OWNER = "romanhlavac"
REPO = "romanhlavac/ddd-accelerator"
CFG_PATH = Path("config/governance/github-bootstrap.json")
REPORT_PATH = Path(".reports/cr-delivery-audit-v6/presentation.json")
WP_PREFIX_RE = re.compile(r"\[WP-(\d{2})\]", re.I)


def cmd(program, *args, json_out=False):
    p = subprocess.run([program, *args], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(
            f"{program} {' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}"
        )
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def issue(number):
    return gh("api", f"repos/{REPO}/issues/{number}", json_out=True)


def load_authority():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    wp_parent = {}
    item_meta = {}
    for group in cfg.get("item_groups", []):
        if group.get("kind") != "issue":
            continue
        meta = dict(group.get("metadata") or {})
        for raw in group.get("numbers", []):
            number = int(raw)
            item_meta.setdefault(number, {}).update(meta)
            if meta.get("Item Type") == "Work Package" and meta.get("Work Package"):
                wp_parent[meta["Work Package"]] = number

    authority = {number: wp for wp, number in wp_parent.items()}
    for relation in cfg.get("hierarchy", []):
        parent = int(relation["parent"])
        wp = next((name for name, number in wp_parent.items() if number == parent), None)
        if not wp:
            raise RuntimeError(f"Hierarchy parent #{parent} has no Work Package metadata")
        for raw_child in relation.get("children", []):
            child = int(raw_child)
            if child in authority and authority[child] != wp:
                raise RuntimeError(f"Issue #{child} has ambiguous Work Package authority")
            authority[child] = wp

    for number, meta in item_meta.items():
        if meta.get("Item Type") == "Change Request" and meta.get("Work Package") == "Other":
            authority[number] = "Other"
    return authority


def title_prefixes(title):
    return [f"WP-{value}" for value in WP_PREFIX_RE.findall(title or "")]


def presentation_mismatch(title, wp):
    prefixes = title_prefixes(title)
    if not prefixes:
        return False
    return len(prefixes) != 1 or wp == "Other" or prefixes[0] != wp


def aligned_title(title, wp):
    prefixes = title_prefixes(title)
    if not prefixes:
        return title
    if len(prefixes) != 1:
        raise ValueError(f"Ambiguous WP title prefixes cannot be repaired mechanically: {title!r}")
    if wp == "Other":
        return WP_PREFIX_RE.sub("", title, count=1).strip()
    return WP_PREFIX_RE.sub(f"[{wp}]", title, count=1)


def plan_title_repair(number, title, wp):
    if not presentation_mismatch(title, wp):
        return None
    return {
        "issue": int(number),
        "wp": wp,
        "action": "ALIGN_ISSUE_WP_TITLE_PREFIX",
        "from": title,
        "to": aligned_title(title, wp),
    }


def update_issue_title(number, title):
    gh(
        "api",
        "--method",
        "PATCH",
        f"repos/{REPO}/issues/{number}",
        "-f",
        f"title={title}",
    )


def inspect(authority):
    mismatches = []
    rows = []
    for number, wp in sorted(authority.items()):
        data = issue(number)
        title = data.get("title") or ""
        repair = plan_title_repair(number, title, wp)
        row = {
            "issue": number,
            "wp": wp,
            "title": title,
            "prefixes": title_prefixes(title),
            "result": "PRESENTATION_WP_MISMATCH" if repair else "PASS",
        }
        rows.append(row)
        if repair:
            mismatches.append(repair)
    return rows, mismatches


def run(mode):
    authority = load_authority()
    before_rows, before = inspect(authority)
    repairs = []
    if mode == "reconcile":
        for repair in before:
            update_issue_title(repair["issue"], repair["to"])
            repairs.append(repair)

    final_rows, remaining = inspect(authority)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "mode": mode,
        "authority_count": len(authority),
        "before_count": len(before),
        "repair_count": len(repairs),
        "remaining_count": len(remaining),
        "before": before,
        "repairs": repairs,
        "final": final_rows,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if remaining:
        raise RuntimeError(
            "Planning presentation read-back mismatches: "
            + json.dumps(remaining, ensure_ascii=False)
        )
    print(
        json.dumps(
            {
                "mode": mode,
                "authority": len(authority),
                "before": len(before),
                "repairs": len(repairs),
                "remaining": len(remaining),
            }
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reconcile", "verify"), default="verify")
    args = parser.parse_args(argv)
    run(args.mode)


if __name__ == "__main__":
    main()
