import json
import re
import subprocess
import time
from pathlib import Path

OWNER = "romanhlavac"
REPO = "romanhlavac/ddd-accelerator"
PROJECT_TITLE = "DDDA Platform Backlog"
WP_PARENT = {"WP-08": 17, "WP-09": 18, "WP-10": 19, "WP-11": 20}
PARENT_WP = {v: k for k, v in WP_PARENT.items()}

EXPECTED = {
    9: "WP-08", 10: "WP-08", 11: "WP-08", 12: "WP-08", 13: "WP-08", 14: "WP-08",
    45: "WP-08", 53: "WP-08", 54: "WP-08", 55: "WP-08", 56: "WP-08", 57: "WP-08",
    16: "Other", 49: "Other",
    21: "WP-09", 22: "WP-09", 23: "WP-09", 24: "WP-09", 25: "WP-09", 26: "WP-09", 50: "WP-09", 51: "WP-09",
    27: "WP-10", 28: "WP-10", 29: "WP-10", 30: "WP-10", 31: "WP-10", 32: "WP-10", 33: "WP-10",
    34: "WP-11", 35: "WP-11", 36: "WP-11", 37: "WP-11", 38: "WP-11", 39: "WP-11", 40: "WP-11", 41: "WP-11",
    46: "WP-11", 47: "WP-11", 48: "WP-11", 52: "WP-11",
}

NEW_WP08 = {
    54: "Persistent DDDA Example Project board lifecycle generated from exact candidate/release packages.",
    55: "Per-project Miro identity, team, Space, token and board provisioning UX.",
    56: "Governed rebinding of Miro execution profiles to the corporate team/Space.",
    57: "Remove generic MIRO_ACCESS_TOKEN fallback after explicit profile credential migration.",
}


def cmd(program, *args, json_out=False):
    p = subprocess.run([program, *args], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{program} {' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def gql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if value is None:
            continue
        args += (["-F", f"{key}={value}"] if isinstance(value, int) else ["-f", f"{key}={value}"])
    return gh(*args, json_out=True)


def issue(number):
    return gh("api", f"repos/{REPO}/issues/{number}", json_out=True)


def native_parent_number(data):
    url = data.get("parent_issue_url")
    if not url:
        return None
    return int(url.rstrip("/").split("/")[-1])


def is_cr(data):
    if "pull_request" in data:
        return False
    title = data.get("title") or ""
    body = data.get("body") or ""
    return bool(
        re.search(r"\[(?:CR|CHR)\]", title, re.I)
        or re.search(r"^\s*#\s*Change Request\b", body, re.I | re.M)
        or re.search(r"Item Type\s*:\s*`?Change Request`?", body, re.I)
    )


def discover_cr_numbers():
    pages = gh("api", "--paginate", "--slurp", f"repos/{REPO}/issues?state=all&per_page=100", json_out=True)
    items = []
    for page in pages or []:
        items.extend(page)
    return {int(x["number"]) for x in items if is_cr(x)}


def ensure_native_hierarchy(details, repairs):
    for number, wp in EXPECTED.items():
        data = details[number]
        parent = native_parent_number(data)
        if wp == "Other":
            if parent in PARENT_WP:
                raise RuntimeError(f"Cross-cutting CR #{number} unexpectedly has WP parent #{parent}")
            continue
        expected_parent = WP_PARENT[wp]
        if parent is None:
            gh("api", "--method", "POST", f"repos/{REPO}/issues/{expected_parent}/sub_issues", "-F", f"sub_issue_id={data['id']}")
            repairs.append({"issue": number, "action": "ADD_NATIVE_PARENT", "value": expected_parent})
            details[number] = issue(number)
            parent = native_parent_number(details[number])
        if parent != expected_parent:
            raise RuntimeError(f"CR #{number} has parent #{parent}, expected #{expected_parent}")


def ensure_issue57_dependencies(details, repairs):
    required = {53, 54, 55}
    current = gh("api", f"repos/{REPO}/issues/57/dependencies/blocked_by?per_page=100", json_out=True) or []
    current_numbers = {int(x["number"]) for x in current}
    for blocker in sorted(required - current_numbers):
        blocker_data = details.get(blocker) or issue(blocker)
        gh("api", "--method", "POST", f"repos/{REPO}/issues/57/dependencies/blocked_by", "-F", f"issue_id={blocker_data['id']}")
        repairs.append({"issue": 57, "action": "ADD_BLOCKED_BY", "value": blocker})
    final = gh("api", f"repos/{REPO}/issues/57/dependencies/blocked_by?per_page=100", json_out=True) or []
    final_numbers = {int(x["number"]) for x in final}
    missing = required - final_numbers
    if missing:
        raise RuntimeError(f"CR #57 missing required blockers after reconciliation: {sorted(missing)}")
    return sorted(final_numbers)


Q_FIELDS = """
query($login:String!,$number:Int!){
  user(login:$login){
    projectV2(number:$number){
      id
      number
      title
      fields(first:100){
        nodes{
          __typename
          ... on ProjectV2FieldCommon{id name dataType}
          ... on ProjectV2SingleSelectField{options{id name}}
        }
      }
    }
  }
}
"""

Q_ITEMS = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){
    projectV2(number:$number){
      items(first:100,after:$after){
        pageInfo{hasNextPage endCursor}
        nodes{
          id
          content{
            __typename
            ... on Issue{id number url state}
            ... on PullRequest{id number url state}
          }
          fieldValues(first:50){
            nodes{
              __typename
              ... on ProjectV2ItemFieldSingleSelectValue{
                name
                field{... on ProjectV2FieldCommon{name}}
              }
              ... on ProjectV2ItemFieldTextValue{
                text
                field{... on ProjectV2FieldCommon{name}}
              }
            }
          }
        }
      }
    }
  }
}
"""


def project_items(project_number):
    result = []
    after = None
    while True:
        block = gql(Q_ITEMS, login=OWNER, number=project_number, after=after)["data"]["user"]["projectV2"]["items"]
        result.extend(block["nodes"])
        if not block["pageInfo"]["hasNextPage"]:
            break
        after = block["pageInfo"]["endCursor"]
    return result


def project_issue_map(project_number):
    return {
        int(x["content"]["number"]): x
        for x in project_items(project_number)
        if (x.get("content") or {}).get("__typename") == "Issue"
    }


def project_values(item):
    values = {}
    for node in item.get("fieldValues", {}).get("nodes", []):
        field = (node.get("field") or {}).get("name")
        if field:
            values[field] = node.get("name") if node.get("name") is not None else node.get("text")
    return values


def set_select(project_id, fields, item_id, field_name, option_name):
    field = fields[field_name]
    option = next((x for x in field.get("options", []) if x["name"] == option_name), None)
    if option is None:
        raise RuntimeError(f"Project option not found: {field_name}={option_name}")
    mutation = """
mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){
  updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{singleSelectOptionId:$optionId}}){projectV2Item{id}}
}
"""
    gql(mutation, projectId=project_id, itemId=item_id, fieldId=field["id"], optionId=option["id"])


def set_text(project_id, fields, item_id, field_name, value):
    field = fields[field_name]
    mutation = """
mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$text:String!){
  updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{text:$text}}){projectV2Item{id}}
}
"""
    gql(mutation, projectId=project_id, itemId=item_id, fieldId=field["id"], text=str(value))


def add_project_item(project_id, data):
    mutation = """
mutation($projectId:ID!,$contentId:ID!){
  addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){item{id}}
}
"""
    return gql(mutation, projectId=project_id, contentId=data["node_id"])["data"]["addProjectV2ItemById"]["item"]["id"]


def resolve_project():
    projects = gh("project", "list", "--owner", OWNER, "--limit", "100", "--format", "json", json_out=True)
    match = next((x for x in projects.get("projects", []) if x.get("title") == PROJECT_TITLE and not x.get("closed")), None)
    if match is None:
        raise RuntimeError(f"Project not found: {PROJECT_TITLE}")
    project_number = int(match["number"])
    pdata = gql(Q_FIELDS, login=OWNER, number=project_number)["data"]["user"]["projectV2"]
    fields = {x.get("name"): x for x in pdata["fields"]["nodes"] if x.get("name")}
    for required in ["Status", "Work Package", "Item Type", "Target Release", "Blocked", "Human Review", "Outcome summary", "Dependency"]:
        if required not in fields:
            raise RuntimeError(f"Required Project field missing: {required}")
    return project_number, pdata["id"], fields


def reconcile_project(details, project_number, project_id, fields, repairs):
    items = project_issue_map(project_number)
    for number, wp in EXPECTED.items():
        data = details[number]
        item = items.get(number)
        added = False
        if item is None:
            item_id = add_project_item(project_id, data)
            current = {}
            added = True
            repairs.append({"issue": number, "action": "ADD_PROJECT_ITEM"})
        else:
            item_id = item["id"]
            current = project_values(item)

        if current.get("Item Type") != "Change Request":
            set_select(project_id, fields, item_id, "Item Type", "Change Request")
            repairs.append({"issue": number, "action": "SET_ITEM_TYPE", "value": "Change Request"})
        if current.get("Work Package") != wp:
            set_select(project_id, fields, item_id, "Work Package", wp)
            repairs.append({"issue": number, "action": "SET_WORK_PACKAGE", "value": wp})

        status = current.get("Status")
        if data["state"] == "closed":
            desired = "Cancelled" if data.get("state_reason") in ("not_planned", "duplicate") else "Done"
            if status != desired:
                set_select(project_id, fields, item_id, "Status", desired)
                repairs.append({"issue": number, "action": "SET_STATUS", "value": desired})
        elif status in (None, "Done", "Cancelled"):
            set_select(project_id, fields, item_id, "Status", "Backlog")
            repairs.append({"issue": number, "action": "SET_STATUS", "value": "Backlog"})

        milestone = (data.get("milestone") or {}).get("title")
        target_release = current.get("Target Release")
        if milestone and target_release != milestone:
            set_text(project_id, fields, item_id, "Target Release", milestone)
            repairs.append({"issue": number, "action": "SET_TARGET_RELEASE_FROM_MILESTONE", "value": milestone})
        elif not milestone and (added or number in NEW_WP08) and not target_release:
            set_text(project_id, fields, item_id, "Target Release", "TBD")
            repairs.append({"issue": number, "action": "SET_TARGET_RELEASE", "value": "TBD"})

        if number in NEW_WP08:
            if current.get("Blocked") != "Yes":
                set_select(project_id, fields, item_id, "Blocked", "Yes")
                repairs.append({"issue": number, "action": "SET_BLOCKED", "value": "Yes"})
            if not current.get("Human Review"):
                set_select(project_id, fields, item_id, "Human Review", "Not required")
                repairs.append({"issue": number, "action": "SET_HUMAN_REVIEW", "value": "Not required"})
            if not current.get("Outcome summary"):
                set_text(project_id, fields, item_id, "Outcome summary", NEW_WP08[number])
                repairs.append({"issue": number, "action": "SET_OUTCOME_SUMMARY"})
        if number == 57 and not current.get("Dependency"):
            set_text(project_id, fields, item_id, "Dependency", "blocked by #53, #54, #55")
            repairs.append({"issue": 57, "action": "SET_DEPENDENCY_PROJECTION", "value": "blocked by #53, #54, #55"})


def poll_project_map(project_number):
    latest = {}
    for _ in range(20):
        latest = project_issue_map(project_number)
        if set(EXPECTED).issubset(latest):
            return latest
        time.sleep(2)
    return latest


def update_versioned_contracts():
    cfg_path = Path("config/governance/github-bootstrap.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))

    rel = next(x for x in cfg["hierarchy"] if int(x["parent"]) == 17)
    children = [int(x) for x in rel.get("children", [])]
    for number in NEW_WP08:
        if number not in children:
            children.append(number)
    rel["children"] = children

    defaults = {
        number: {
            "Status": "Backlog",
            "Work Package": "WP-08",
            "Item Type": "Change Request",
            "Target Release": "TBD",
            "Blocked": "Yes",
            "Human Review": "Not required",
            "Outcome summary": summary,
        }
        for number, summary in NEW_WP08.items()
    }
    for number, metadata in defaults.items():
        matches = [g for g in cfg.get("item_groups", []) if g.get("kind") == "issue" and number in [int(x) for x in g.get("numbers", [])]]
        if not matches:
            cfg.setdefault("item_groups", []).append({"kind": "issue", "numbers": [number], "metadata": metadata})
        else:
            matches[0].setdefault("metadata", {}).update(metadata)

    dep = next((x for x in cfg.get("dependencies", []) if int(x.get("blocked", -1)) == 57), None)
    if dep is None:
        cfg.setdefault("dependencies", []).append({"blocked": 57, "blocked_by": [53, 54, 55]})
    else:
        blockers = [int(x) for x in dep.get("blocked_by", [])]
        for number in [53, 54, 55]:
            if number not in blockers:
                blockers.append(number)
        dep["blocked_by"] = blockers
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    policy_path = Path("config/governance/backlog-policy.yaml")
    policy = policy_path.read_text(encoding="utf-8-sig")
    policy = policy.replace(
        "children: [9, 10, 11, 12, 13, 14, 15, 45, 53]",
        "children: [9, 10, 11, 12, 13, 14, 15, 45, 53, 54, 55, 56, 57]",
    )
    policy = policy.replace(
        "future_children: [45, 53]",
        "future_children: [45, 53, 54, 55, 56, 57]",
    )
    wp08_marker = "    - blocking: 10\n      blocked: 9\n      rationale: release contract consistency precedes final HRDR\n"
    dep57 = (
        "    - blocking: 53\n      blocked: 57\n      rationale: persistent Platform Lab precedes removal of legacy generic credential fallback\n"
        "    - blocking: 54\n      blocked: 57\n      rationale: Example Project profile must use explicit credentials before fallback removal\n"
        "    - blocking: 55\n      blocked: 57\n      rationale: per-project credential UX must be stable before fallback removal\n"
    )
    if "      blocked: 57\n" not in policy:
        policy = policy.replace(wp08_marker, wp08_marker + dep57)
    policy_path.write_text(policy, encoding="utf-8")

    roadmap_path = Path("docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md")
    roadmap = roadmap_path.read_text(encoding="utf-8-sig")
    if "persistent DDDA Example Project board lifecycle — #54" not in roadmap:
        roadmap = roadmap.replace(
            "- persistent DDDA Platform Lab / board taxonomy / reference-adoption lifecycle — #53.\n",
            "- persistent DDDA Platform Lab / board taxonomy / reference-adoption lifecycle — #53.\n"
            "- persistent DDDA Example Project board lifecycle — #54.\n"
            "- per-project Miro identity/team/Space/token UX — #55.\n"
            "- corporate Miro execution-profile rebinding — #56.\n"
            "- explicit profile credentials and legacy generic-token fallback removal — #57.\n",
        )
    if "- #54 — persistent Example Project board lifecycle" not in roadmap:
        roadmap = roadmap.replace(
            "- #53 — persistent Platform Lab, board taxonomy and reference/adoption lifecycle; `Target Release: TBD`, partial docs slice in Draft PR #58, explicitly outside Milestone `DDDA 0.1.0`.\n",
            "- #53 — persistent Platform Lab, board taxonomy and reference/adoption lifecycle; `Target Release: TBD`, partial docs slice in Draft PR #58, explicitly outside Milestone `DDDA 0.1.0`.\n"
            "- #54 — persistent Example Project board lifecycle; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.\n"
            "- #55 — per-project Miro identity/team/Space/token UX; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.\n"
            "- #56 — corporate Miro execution-profile rebinding; `Target Release: TBD`, outside Milestone `DDDA 0.1.0`.\n"
            "- #57 — explicit profile credentials and legacy generic-token fallback removal; `Target Release: TBD`, blocked by #53/#54/#55, outside Milestone `DDDA 0.1.0`.\n",
        )
    roadmap = roadmap.replace("#45 and #53 do not enter release 0.1.0 implicitly.", "#45 and #53–#57 do not enter release 0.1.0 implicitly.")
    roadmap = roadmap.replace("future #45/#53 remain independently planned.", "future #45/#53–#57 remain independently planned.")
    roadmap_path.write_text(roadmap, encoding="utf-8")


def verify(details, project_number, blockers57):
    items = poll_project_map(project_number)
    remaining = []
    rows = []
    for number, wp in EXPECTED.items():
        data = issue(number)
        parent = native_parent_number(data)
        item = items.get(number)
        problems = []
        if wp != "Other" and parent != WP_PARENT[wp]:
            problems.append("NATIVE_PARENT_MISMATCH")
        if wp == "Other" and parent in PARENT_WP:
            problems.append("UNEXPECTED_WP_PARENT")
        if item is None:
            problems.append("MISSING_PROJECT_ITEM")
            values = {}
        else:
            values = project_values(item)
            if values.get("Item Type") != "Change Request":
                problems.append("ITEM_TYPE_MISMATCH")
            if values.get("Work Package") != wp:
                problems.append("WORK_PACKAGE_MISMATCH")
            status = values.get("Status")
            if data["state"] == "closed" and status not in ("Done", "Cancelled"):
                problems.append("CLOSED_STATUS_MISMATCH")
            if data["state"] == "open" and status in (None, "Done", "Cancelled"):
                problems.append("OPEN_STATUS_MISMATCH")
            milestone = (data.get("milestone") or {}).get("title")
            if milestone and values.get("Target Release") != milestone:
                problems.append("TARGET_RELEASE_MILESTONE_MISMATCH")
            if number in NEW_WP08:
                if values.get("Blocked") != "Yes":
                    problems.append("BLOCKED_FIELD_MISMATCH")
                if not values.get("Human Review"):
                    problems.append("HUMAN_REVIEW_FIELD_MISSING")
                if not values.get("Target Release"):
                    problems.append("TARGET_RELEASE_MISSING")
        if number == 57 and not {53, 54, 55}.issubset(set(blockers57)):
            problems.append("DEPENDENCY_MISMATCH")
        row = {
            "issue": number,
            "expected_wp": wp,
            "parent": parent,
            "project_member": item is not None,
            "fields": {k: values.get(k) for k in ["Status", "Work Package", "Item Type", "Target Release", "Blocked", "Human Review"]},
            "result": "PASS" if not problems else "+".join(problems),
        }
        rows.append(row)
        if problems:
            remaining.append(row)
    return rows, remaining


def main():
    repairs = []
    discovered = discover_cr_numbers()
    unknown = sorted(discovered - set(EXPECTED))
    if unknown:
        raise RuntimeError(f"Discovered CR/CHR not present in explicit audit mapping: {unknown}")

    details = {number: issue(number) for number in EXPECTED}
    ensure_native_hierarchy(details, repairs)
    blockers57 = ensure_issue57_dependencies(details, repairs)

    project_number, project_id, fields = resolve_project()
    reconcile_project(details, project_number, project_id, fields, repairs)
    blockers57 = ensure_issue57_dependencies(details, repairs)
    rows, remaining = verify(details, project_number, blockers57)
    if remaining:
        raise RuntimeError("Project read-back still contains mismatches: " + json.dumps(remaining, ensure_ascii=False))

    update_versioned_contracts()

    source_sha = cmd("git", "rev-parse", "HEAD")
    report = {
        "schema_version": 4,
        "repository": REPO,
        "project": {"title": PROJECT_TITLE, "number": project_number},
        "source_sha": source_sha,
        "mapped_cr_count": len(EXPECTED),
        "discovered_cr_count": len(discovered),
        "repair_count": len(repairs),
        "remaining_count": 0,
        "repairs": repairs,
        "issue57_blocked_by": blockers57,
        "final": rows,
    }
    out = Path(".reports/cr-backlog-audit-v4")
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# DDDA CR ↔ Project Backlog consistency audit v4",
        "",
        f"- Source SHA: `{source_sha}`",
        f"- Explicit mapped CRs: **{len(EXPECTED)}**",
        f"- Discovered CR/CHR signatures: **{len(discovered)}**",
        f"- Deterministic repairs: **{len(repairs)}**",
        "- Remaining mismatches: **0**",
        "",
        "| CR | WP | Parent | Project | Status | Item Type | Result |",
        "|---:|---|---:|---|---|---|---|",
    ]
    for row in rows:
        f = row["fields"]
        md.append(f"| #{row['issue']} | {row['expected_wp']} | {row['parent'] or '-'} | {'yes' if row['project_member'] else 'no'} | {f.get('Status') or '-'} | {f.get('Item Type') or '-'} | {row['result']} |")
    md += ["", "## Repairs", ""] + ([f"- `{json.dumps(x, ensure_ascii=False)}`" for x in repairs] or ["- none"])
    (out / "audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"mapped": len(EXPECTED), "discovered": len(discovered), "repairs": len(repairs), "remaining": 0}))


if __name__ == "__main__":
    main()
