import argparse
import json
import subprocess
import time
from pathlib import Path

REPO = "romanhlavac/ddd-accelerator"
CFG_PATH = Path("config/governance/github-bootstrap.json")
REPORT_PATH = Path(".reports/cr-delivery-audit-v6/release-planning.json")
READBACK_ATTEMPTS = 10
READBACK_DELAY_SECONDS = 2


def cmd(*args, json_out=False, stdin=None):
    p = subprocess.run(list(args), input=stdin, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def gh_json(method, path, body):
    return cmd(
        "gh", "api", "--method", method, path, "--input", "-",
        json_out=True, stdin=json.dumps(body),
    )


def load_specs():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    specs = list(cfg.get("milestones") or [])
    if not specs:
        legacy = cfg.get("milestone")
        if legacy:
            specs = [legacy]
    if not specs:
        raise RuntimeError("No milestone contract configured")
    titles = [x["title"] for x in specs]
    if len(titles) != len(set(titles)):
        raise RuntimeError("Duplicate configured milestone title")
    assigned = {}
    for spec in specs:
        for raw in list(spec.get("issues") or []) + list(spec.get("pulls") or []):
            n = int(raw)
            if n in assigned:
                raise RuntimeError(f"#{n} appears in multiple configured milestones: {assigned[n]} and {spec['title']}")
            assigned[n] = spec["title"]
    return specs


def list_milestones():
    return gh("api", f"repos/{REPO}/milestones?state=all&per_page=100", json_out=True) or []


def milestone_items(number):
    pages = gh("api", "--paginate", "--slurp", f"repos/{REPO}/issues?state=all&milestone={number}&per_page=100", json_out=True) or []
    rows = []
    for page in pages:
        rows.extend(page)
    return {int(x["number"]): x for x in rows}


def desired_numbers(spec):
    return {int(x) for x in list(spec.get("issues") or []) + list(spec.get("pulls") or [])}


def ensure_milestone(spec, repairs):
    matches = [x for x in list_milestones() if x.get("title") == spec["title"]]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous milestone title: {spec['title']}")
    wanted_state = spec.get("state") or "open"
    wanted_description = spec.get("description") or ""
    if not matches:
        created = gh_json("POST", f"repos/{REPO}/milestones", {
            "title": spec["title"], "state": wanted_state, "description": wanted_description,
        })
        repairs.append({"milestone": spec["title"], "action": "CREATE_MILESTONE", "number": int(created["number"])})
        return created
    current = matches[0]
    patch = {}
    if current.get("state") != wanted_state:
        patch["state"] = wanted_state
    if (current.get("description") or "") != wanted_description:
        patch["description"] = wanted_description
    if patch:
        current = gh_json("PATCH", f"repos/{REPO}/milestones/{current['number']}", patch)
        repairs.append({"milestone": spec["title"], "action": "ALIGN_MILESTONE", "value": patch})
    return current


def reconcile(specs):
    repairs = []
    resolved = []
    for spec in specs:
        milestone = ensure_milestone(spec, repairs)
        number = int(milestone["number"])
        wanted = desired_numbers(spec)
        current = milestone_items(number)
        for extra in sorted(set(current) - wanted):
            gh_json("PATCH", f"repos/{REPO}/issues/{extra}", {"milestone": None})
            repairs.append({"issue": extra, "action": "REMOVE_FROM_MILESTONE", "milestone": spec["title"]})
        for missing in sorted(wanted - set(current)):
            gh_json("PATCH", f"repos/{REPO}/issues/{missing}", {"milestone": number})
            repairs.append({"issue": missing, "action": "ASSIGN_MILESTONE", "milestone": spec["title"]})
        resolved.append({"title": spec["title"], "number": number})
    return repairs, resolved


def verify(specs):
    problems = []
    rows = []
    live = list_milestones()
    by_title = {}
    for item in live:
        by_title.setdefault(item.get("title"), []).append(item)
    for spec in specs:
        matches = by_title.get(spec["title"], [])
        if len(matches) != 1:
            problems.append({"milestone": spec["title"], "result": "MILESTONE_IDENTITY_MISMATCH", "count": len(matches)})
            continue
        milestone = matches[0]
        wanted = desired_numbers(spec)
        actual = set(milestone_items(int(milestone["number"])))
        row = {
            "title": spec["title"],
            "number": int(milestone["number"]),
            "state": milestone.get("state"),
            "desired": sorted(wanted),
            "actual": sorted(actual),
            "result": "PASS",
        }
        if actual != wanted:
            row["result"] = "MILESTONE_MEMBERSHIP_MISMATCH"
            problems.append(dict(row))
        elif milestone.get("state") != (spec.get("state") or "open"):
            row["result"] = "MILESTONE_STATE_MISMATCH"
            problems.append(dict(row))
        elif (milestone.get("description") or "") != (spec.get("description") or ""):
            row["result"] = "MILESTONE_DESCRIPTION_MISMATCH"
            problems.append(dict(row))
        rows.append(row)
    return rows, problems


def verify_eventually(
    specs,
    max_attempts=READBACK_ATTEMPTS,
    delay_seconds=READBACK_DELAY_SECONDS,
    verify_fn=None,
    sleep_fn=None,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    verify_fn = verify_fn or verify
    sleep_fn = sleep_fn or time.sleep
    for attempt in range(1, max_attempts + 1):
        rows, problems = verify_fn(specs)
        if not problems or attempt == max_attempts:
            return rows, problems, attempt
        sleep_fn(delay_seconds)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reconcile", "verify"), default="verify")
    args = parser.parse_args(argv)
    specs = load_specs()
    repairs = []
    if args.mode == "reconcile":
        repairs, _ = reconcile(specs)
        rows, problems, readback_attempts = verify_eventually(specs)
    else:
        rows, problems = verify(specs)
        readback_attempts = 1
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_sha = cmd("git", "rev-parse", "HEAD")
    report = {
        "schema_version": 1,
        "mode": args.mode,
        "source_sha": source_sha,
        "repair_count": len(repairs),
        "readback_attempts": readback_attempts,
        "remaining_count": len(problems),
        "repairs": repairs,
        "milestones": rows,
        "problems": problems,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if problems:
        raise RuntimeError("Release planning mismatches: " + json.dumps(problems, ensure_ascii=False))
    print(json.dumps({"mode": args.mode, "repairs": len(repairs), "remaining": 0, "milestones": len(rows)}))


if __name__ == "__main__":
    main()
