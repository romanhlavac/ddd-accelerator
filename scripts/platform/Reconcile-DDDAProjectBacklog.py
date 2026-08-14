import json
import re
import subprocess
import time
from pathlib import Path

OWNER = "romanhlavac"
REPO = "romanhlavac/ddd-accelerator"
PROJECT_TITLE = "DDDA Platform Backlog & Delivery"
LEGACY_PROJECT_TITLE = "DDDA Platform Backlog"
PLANNING_VIEW = "Plánování a Backlog"
DELIVERY_VIEW = "Implementace a Delivery"
CFG_PATH = Path("config/governance/github-bootstrap.json")
REPORT_DIR = Path(".reports/cr-delivery-audit-v6")
LEGACY_PR_WP = {8: "WP-08"}


def cmd(program, *args, json_out=False, stdin=None):
    p = subprocess.run([program, *args], input=stdin, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{program} {' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}})
    result = cmd("gh", "api", "graphql", "--input", "-", json_out=True, stdin=payload)
    if result.get("errors"):
        raise RuntimeError("GraphQL failed: " + json.dumps(result["errors"], ensure_ascii=False))
    return result


def issue(number):
    return gh("api", f"repos/{REPO}/issues/{number}", json_out=True)


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
    rows = []
    for page in pages or []:
        rows.extend(page)
    return {int(x["number"]) for x in rows if is_cr(x)}


def discover_open_prs():
    pages = gh("api", "--paginate", "--slurp", f"repos/{REPO}/pulls?state=open&per_page=100", json_out=True)
    rows = []
    for page in pages or []:
        rows.extend(page)
    return sorted(rows, key=lambda x: int(x["number"]))


def native_parent_number(data):
    url = data.get("parent_issue_url")
    return int(url.rstrip("/").split("/")[-1]) if url else None


def remove_child(parent, data):
    gh("api", "--method", "DELETE", f"repos/{REPO}/issues/{parent}/sub_issue", "-F", f"sub_issue_id={data['id']}")


def add_child(parent, data):
    gh("api", "--method", "POST", f"repos/{REPO}/issues/{parent}/sub_issues", "-F", f"sub_issue_id={data['id']}")


def load_contract():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    wp_parent = {}
    item_meta = {}
    for group in cfg.get("item_groups", []):
        if group.get("kind") != "issue":
            continue
        meta = dict(group.get("metadata") or {})
        for raw in group.get("numbers", []):
            n = int(raw)
            item_meta.setdefault(n, {}).update(meta)
            if meta.get("Item Type") == "Work Package" and meta.get("Work Package"):
                wp_parent[meta["Work Package"]] = n

    hierarchy = {}
    for rel in cfg.get("hierarchy", []):
        parent = int(rel["parent"])
        wp = next((k for k, v in wp_parent.items() if v == parent), None)
        if not wp:
            raise RuntimeError(f"Hierarchy parent #{parent} has no Work Package item metadata")
        for child in rel.get("children", []):
            c = int(child)
            if c in hierarchy and hierarchy[c] != wp:
                raise RuntimeError(f"Issue #{c} appears under multiple Work Packages")
            hierarchy[c] = wp

    expected = dict(hierarchy)
    for n, meta in item_meta.items():
        if meta.get("Item Type") == "Change Request" and meta.get("Work Package") == "Other":
            expected[n] = "Other"

    dependencies = {int(x["blocked"]): {int(v) for v in x.get("blocked_by", [])} for x in cfg.get("dependencies", [])}
    return cfg, wp_parent, item_meta, expected, dependencies


def reconcile_hierarchy(wp_parent, expected, details, repairs):
    parent_set = set(wp_parent.values())
    for n, wp in sorted(expected.items()):
        data = details[n]
        current = native_parent_number(data)
        if wp == "Other":
            if current in parent_set:
                remove_child(current, data)
                repairs.append({"issue": n, "action": "REMOVE_NATIVE_PARENT", "value": current})
            continue
        target = wp_parent[wp]
        if current == target:
            continue
        if current in parent_set:
            remove_child(current, data)
            repairs.append({"issue": n, "action": "REMOVE_NATIVE_PARENT", "value": current})
        add_child(target, data)
        repairs.append({"issue": n, "action": "ADD_NATIVE_PARENT", "value": target})


def current_blockers(n):
    rows = gh("api", f"repos/{REPO}/issues/{n}/dependencies/blocked_by?per_page=100", json_out=True) or []
    return {int(x["number"]): x for x in rows}


def reconcile_dependencies(dependencies, repairs):
    for blocked, wanted in sorted(dependencies.items()):
        current = current_blockers(blocked)
        for extra in sorted(set(current) - wanted):
            gh("api", "--method", "DELETE", f"repos/{REPO}/issues/{blocked}/dependencies/blocked_by/{current[extra]['id']}")
            repairs.append({"issue": blocked, "action": "REMOVE_BLOCKED_BY", "value": extra})
        for missing in sorted(wanted - set(current)):
            b = issue(missing)
            gh("api", "--method", "POST", f"repos/{REPO}/issues/{blocked}/dependencies/blocked_by", "-F", f"issue_id={b['id']}")
            repairs.append({"issue": blocked, "action": "ADD_BLOCKED_BY", "value": missing})


Q_PROJECT = """
query($login:String!,$number:Int!){
  user(login:$login){projectV2(number:$number){
    id number title
    views(first:20){nodes{id number name layout filter}}
    fields(first:100){nodes{
      __typename
      ... on ProjectV2FieldCommon{id name dataType}
      ... on ProjectV2SingleSelectField{options{id name color description}}
    }}
  }}
}
"""

Q_ITEMS = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){projectV2(number:$number){items(first:100,after:$after){
    pageInfo{hasNextPage endCursor}
    nodes{id content{
      __typename
      ... on Issue{id number url state title}
      ... on PullRequest{id number url state title isDraft merged}
    }
    fieldValues(first:50){nodes{
      __typename
      ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2FieldCommon{name}}}
      ... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{name}}}
    }}}
  }}}
}
"""


def update_project_title(project_id):
    q = """mutation($projectId:ID!,$title:String!){updateProjectV2(input:{projectId:$projectId,title:$title}){projectV2{id title}}}"""
    gql(q, {"projectId": project_id, "title": PROJECT_TITLE})


def update_view(view_id, name, filter_value):
    q = """mutation($viewId:ID!,$name:String!,$filter:String!){updateProjectV2View(input:{viewId:$viewId,name:$name,layout:TABLE_LAYOUT,filter:$filter}){projectV2View{id number name layout filter}}}"""
    return gql(q, {"viewId": view_id, "name": name, "filter": filter_value})["data"]["updateProjectV2View"]["projectV2View"]


def create_view(project_id, name, filter_value):
    q = """mutation($projectId:ID!,$name:String!,$filter:String!){createProjectV2View(input:{projectId:$projectId,name:$name,layout:TABLE_LAYOUT,filter:$filter}){projectV2View{id number name layout filter}}}"""
    return gql(q, {"projectId": project_id, "name": name, "filter": filter_value})["data"]["createProjectV2View"]["projectV2View"]


def resolve_project(repairs):
    projects = gh("project", "list", "--owner", OWNER, "--limit", "100", "--format", "json", json_out=True)
    match = next(
        (
            x
            for x in projects.get("projects", [])
            if x.get("title") in (PROJECT_TITLE, LEGACY_PROJECT_TITLE) and not x.get("closed")
        ),
        None,
    )
    if not match:
        raise RuntimeError(f"Project not found: {PROJECT_TITLE} (or legacy {LEGACY_PROJECT_TITLE})")
    number = int(match["number"])
    p = gql(Q_PROJECT, {"login": OWNER, "number": number})["data"]["user"]["projectV2"]
    if p["title"] != PROJECT_TITLE:
        update_project_title(p["id"])
        repairs.append({"project": number, "action": "RENAME_PROJECT", "value": PROJECT_TITLE})
        p = gql(Q_PROJECT, {"login": OWNER, "number": number})["data"]["user"]["projectV2"]
    fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    return number, p["id"], fields, p["views"]["nodes"]


def reconcile_views(project_number, project_id, views, repairs):
    by_name = {v["name"]: v for v in views}
    planning = by_name.get(PLANNING_VIEW)
    if not planning:
        legacy = next((v for v in views if int(v["number"]) == 1), None)
        if not legacy:
            raise RuntimeError("Project View 1 is missing; cannot deterministically establish planning view")
        planning = update_view(legacy["id"], PLANNING_VIEW, "is:issue")
        repairs.append({"project": project_number, "action": "RENAME_FILTER_PLANNING_VIEW", "value": PLANNING_VIEW})
    elif planning.get("layout") != "TABLE_LAYOUT" or (planning.get("filter") or "") != "is:issue":
        planning = update_view(planning["id"], PLANNING_VIEW, "is:issue")
        repairs.append({"project": project_number, "action": "ALIGN_PLANNING_VIEW", "value": PLANNING_VIEW})

    views = gql(Q_PROJECT, {"login": OWNER, "number": project_number})["data"]["user"]["projectV2"]["views"]["nodes"]
    by_name = {v["name"]: v for v in views}
    delivery = by_name.get(DELIVERY_VIEW)
    if not delivery:
        delivery = create_view(project_id, DELIVERY_VIEW, "is:pr is:open")
        repairs.append({"project": project_number, "action": "CREATE_DELIVERY_VIEW", "value": DELIVERY_VIEW})
    elif delivery.get("layout") != "TABLE_LAYOUT" or (delivery.get("filter") or "") != "is:pr is:open":
        delivery = update_view(delivery["id"], DELIVERY_VIEW, "is:pr is:open")
        repairs.append({"project": project_number, "action": "ALIGN_DELIVERY_VIEW", "value": DELIVERY_VIEW})
    return planning, delivery


def project_items(project_number):
    out, after = [], None
    while True:
        block = gql(Q_ITEMS, {"login": OWNER, "number": project_number, "after": after})["data"]["user"]["projectV2"]["items"]
        out.extend(block["nodes"])
        if not block["pageInfo"]["hasNextPage"]:
            return out
        after = block["pageInfo"]["endCursor"]


def content_item_map(project_number, typename):
    return {
        int(x["content"]["number"]): x
        for x in project_items(project_number)
        if (x.get("content") or {}).get("__typename") == typename
    }


def values(item):
    out = {}
    for x in item.get("fieldValues", {}).get("nodes", []):
        name = (x.get("field") or {}).get("name")
        if name:
            out[name] = x.get("name") if x.get("name") is not None else x.get("text")
    return out


def add_project_item(project_id, data):
    q = """mutation($projectId:ID!,$contentId:ID!){addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){item{id}}}"""
    return gql(q, {"projectId": project_id, "contentId": data["node_id"]})["data"]["addProjectV2ItemById"]["item"]["id"]


def set_select(project_id, fields, item_id, field_name, option_name):
    field = fields[field_name]
    opt = next((x for x in field.get("options", []) if x["name"] == option_name), None)
    if not opt:
        raise RuntimeError(f"Missing Project option {field_name}={option_name}")
    q = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{singleSelectOptionId:$optionId}}){projectV2Item{id}}}"""
    gql(q, {"projectId": project_id, "itemId": item_id, "fieldId": field["id"], "optionId": opt["id"]})


def set_text(project_id, fields, item_id, field_name, text):
    q = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$text:String!){updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{text:$text}}){projectV2Item{id}}}"""
    gql(q, {"projectId": project_id, "itemId": item_id, "fieldId": fields[field_name]["id"], "text": str(text)})


def clear_field(project_id, fields, item_id, field_name):
    if field_name not in fields:
        return
    q = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!){clearProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId}){projectV2Item{id}}}"""
    gql(q, {"projectId": project_id, "itemId": item_id, "fieldId": fields[field_name]["id"]})


def reconcile_planning(wp_parent, item_meta, expected, details, project_number, project_id, fields, repairs):
    items = content_item_map(project_number, "Issue")
    all_structural = dict(expected)
    for wp, parent in wp_parent.items():
        all_structural[parent] = wp

    for n, wp in sorted(all_structural.items()):
        data = details.get(n) or issue(n)
        item = items.get(n)
        current = {}
        if item is None:
            item_id = add_project_item(project_id, data)
            repairs.append({"issue": n, "action": "ADD_PROJECT_ITEM"})
        else:
            item_id = item["id"]
            current = values(item)
        item_type = "Work Package" if n in wp_parent.values() else "Change Request"
        desired_wp = wp if wp != "Other" else "Other"
        if current.get("Item Type") != item_type:
            set_select(project_id, fields, item_id, "Item Type", item_type)
            repairs.append({"issue": n, "action": "SET_ITEM_TYPE", "value": item_type})
        if current.get("Work Package") != desired_wp:
            set_select(project_id, fields, item_id, "Work Package", desired_wp)
            repairs.append({"issue": n, "action": "SET_WORK_PACKAGE", "value": desired_wp})

        if item_type == "Change Request":
            status = current.get("Status")
            if data["state"] == "closed":
                wanted = "Cancelled" if data.get("state_reason") in ("not_planned", "duplicate") else "Done"
                if status != wanted:
                    set_select(project_id, fields, item_id, "Status", wanted)
                    repairs.append({"issue": n, "action": "SET_STATUS", "value": wanted})
            elif status in (None, "Done", "Cancelled"):
                set_select(project_id, fields, item_id, "Status", "Backlog")
                repairs.append({"issue": n, "action": "SET_STATUS", "value": "Backlog"})

        milestone = (data.get("milestone") or {}).get("title")
        meta = item_meta.get(n, {})
        target = milestone or meta.get("Target Release")
        if target and not current.get("Target Release"):
            set_text(project_id, fields, item_id, "Target Release", target)
            repairs.append({"issue": n, "action": "SET_TARGET_RELEASE", "value": target})


def primary_cr_number(pr):
    number = int(pr["number"])
    if number in LEGACY_PR_WP:
        return None
    body = pr.get("body") or ""
    matches = {
        int(x)
        for x in re.findall(
            r"(?im)^\s*(?:[-*]\s*)?(?:Implements|Closes)\s+#(\d+)\s*$",
            body,
        )
    }
    if len(matches) != 1:
        raise RuntimeError(f"Open PR #{number} must have exactly one primary 'Implements #CR' or 'Closes #CR' relationship; found {sorted(matches)}")
    return next(iter(matches))


def validate_wp_title_prefix(pr, wp):
    title = pr.get("title") or ""
    prefixes = {f"WP-{x}" for x in re.findall(r"\[WP-(\d{2})\]", title, re.I)}
    if not prefixes:
        return
    if wp == "Other" or prefixes != {wp}:
        raise RuntimeError(f"PRESENTATION_WP_MISMATCH on PR #{pr['number']}: title prefixes={sorted(prefixes)} authoritative={wp}")


def delivery_authority(open_prs, expected):
    result = {}
    for pr in open_prs:
        n = int(pr["number"])
        cr = primary_cr_number(pr)
        if cr is None:
            wp = LEGACY_PR_WP[n]
        else:
            if cr not in expected:
                raise RuntimeError(f"Open PR #{n} primary CR #{cr} is outside governed backlog")
            wp = expected[cr]
        validate_wp_title_prefix(pr, wp)
        result[n] = {"pr": pr, "primary_cr": cr, "wp": wp}
    return result


def reconcile_delivery(authority, project_number, project_id, fields, repairs):
    items = content_item_map(project_number, "PullRequest")
    for n, rel in sorted(authority.items()):
        pr = rel["pr"]
        item = items.get(n)
        current = {}
        if item is None:
            item_id = add_project_item(project_id, pr)
            repairs.append({"pr": n, "action": "ADD_DELIVERY_PROJECT_ITEM"})
        else:
            item_id = item["id"]
            current = values(item)

        wp = rel["wp"]
        if current.get("Work Package") != wp:
            set_select(project_id, fields, item_id, "Work Package", wp)
            repairs.append({"pr": n, "action": "SET_DELIVERY_WORK_PACKAGE", "value": wp})

        blocked = current.get("Blocked") == "Yes"
        wanted_status = "Blocked" if blocked else ("In progress" if pr.get("draft") else "In review")
        if current.get("Status") != wanted_status:
            set_select(project_id, fields, item_id, "Status", wanted_status)
            repairs.append({"pr": n, "action": "SET_DELIVERY_STATUS", "value": wanted_status})

        if current.get("Item Type") is not None:
            clear_field(project_id, fields, item_id, "Item Type")
            repairs.append({"pr": n, "action": "CLEAR_PLANNING_ITEM_TYPE"})


def verify_planning(wp_parent, expected, dependencies, project_number):
    items = content_item_map(project_number, "Issue")
    parent_set = set(wp_parent.values())
    rows, problems = [], []
    for n, wp in sorted(expected.items()):
        d = issue(n)
        parent = native_parent_number(d)
        rowprobs = []
        if wp == "Other":
            if parent in parent_set:
                rowprobs.append("UNEXPECTED_WP_PARENT")
        elif parent != wp_parent[wp]:
            rowprobs.append("NATIVE_PARENT_MISMATCH")
        item = items.get(n)
        if not item:
            rowprobs.append("MISSING_PROJECT_ITEM")
            v = {}
        else:
            v = values(item)
            if v.get("Work Package") != wp:
                rowprobs.append("WORK_PACKAGE_MISMATCH")
            if v.get("Item Type") != "Change Request":
                rowprobs.append("ITEM_TYPE_MISMATCH")
        rows.append({"issue": n, "wp": wp, "parent": parent, "fields": v, "result": "PASS" if not rowprobs else "+".join(rowprobs)})
        if rowprobs:
            problems.append(rows[-1])
    for blocked, wanted in dependencies.items():
        got = set(current_blockers(blocked))
        if got != wanted:
            problems.append({"issue": blocked, "result": "DEPENDENCY_MISMATCH", "expected": sorted(wanted), "actual": sorted(got)})
    return rows, problems


def verify_delivery(authority, project_number):
    items = content_item_map(project_number, "PullRequest")
    rows, problems = [], []
    for n, rel in sorted(authority.items()):
        item = items.get(n)
        rowprobs = []
        if not item:
            rowprobs.append("MISSING_DELIVERY_PROJECT_ITEM")
            v = {}
        else:
            v = values(item)
            if v.get("Work Package") != rel["wp"]:
                rowprobs.append("DELIVERY_WORK_PACKAGE_MISMATCH")
            blocked = v.get("Blocked") == "Yes"
            wanted_status = "Blocked" if blocked else ("In progress" if rel["pr"].get("draft") else "In review")
            if v.get("Status") != wanted_status:
                rowprobs.append("DELIVERY_STATUS_MISMATCH")
            if v.get("Item Type") is not None:
                rowprobs.append("DELIVERY_HAS_PLANNING_ITEM_TYPE")
        row = {
            "pr": n,
            "primary_cr": rel["primary_cr"],
            "wp": rel["wp"],
            "fields": v,
            "result": "PASS" if not rowprobs else "+".join(rowprobs),
        }
        rows.append(row)
        if rowprobs:
            problems.append(row)
    return rows, problems


def verify_project_contract(project_number):
    p = gql(Q_PROJECT, {"login": OWNER, "number": project_number})["data"]["user"]["projectV2"]
    problems = []
    if p["title"] != PROJECT_TITLE:
        problems.append({"result": "PROJECT_TITLE_MISMATCH", "actual": p["title"], "expected": PROJECT_TITLE})
    by_name = {v["name"]: v for v in p["views"]["nodes"]}
    expected_views = {PLANNING_VIEW: "is:issue", DELIVERY_VIEW: "is:pr is:open"}
    for name, filter_value in expected_views.items():
        v = by_name.get(name)
        if not v:
            problems.append({"result": "MISSING_PROJECT_VIEW", "view": name})
        elif v.get("layout") != "TABLE_LAYOUT" or (v.get("filter") or "") != filter_value:
            problems.append({"result": "PROJECT_VIEW_MISMATCH", "view": name, "actual": v, "expected_filter": filter_value})
    return p, problems


def main():
    cfg, wp_parent, item_meta, expected, dependencies = load_contract()
    discovered = discover_cr_numbers()
    unknown = sorted(discovered - set(expected))
    if unknown:
        raise RuntimeError(f"Discovered CR/CHR absent from versioned governance mapping: {unknown}")

    open_prs = discover_open_prs()
    authority = delivery_authority(open_prs, expected)
    details = {n: issue(n) for n in expected}
    repairs = []

    reconcile_hierarchy(wp_parent, expected, details, repairs)
    reconcile_dependencies(dependencies, repairs)
    project_number, project_id, fields, views = resolve_project(repairs)
    for required in ["Status", "Work Package", "Item Type", "Target Release", "Blocked"]:
        if required not in fields:
            raise RuntimeError(f"Required Project field missing: {required}")
    reconcile_views(project_number, project_id, views, repairs)
    reconcile_planning(wp_parent, item_meta, expected, details, project_number, project_id, fields, repairs)
    reconcile_delivery(authority, project_number, project_id, fields, repairs)

    time.sleep(2)
    planning_rows, planning_problems = verify_planning(wp_parent, expected, dependencies, project_number)
    delivery_rows, delivery_problems = verify_delivery(authority, project_number)
    project_state, project_problems = verify_project_contract(project_number)
    problems = planning_problems + delivery_problems + project_problems
    if problems:
        raise RuntimeError("Read-back mismatches: " + json.dumps(problems, ensure_ascii=False))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    source_sha = cmd("git", "rev-parse", "HEAD")
    report = {
        "schema_version": 6,
        "source_sha": source_sha,
        "project": {
            "title": PROJECT_TITLE,
            "number": project_number,
            "views": project_state["views"]["nodes"],
        },
        "work_packages": wp_parent,
        "mapped_cr_count": len(expected),
        "discovered_cr_count": len(discovered),
        "open_pr_count": len(open_prs),
        "mapped_pr_count": len(authority),
        "repair_count": len(repairs),
        "remaining_count": 0,
        "repairs": repairs,
        "planning_final": planning_rows,
        "delivery_final": delivery_rows,
    }
    (REPORT_DIR / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# DDDA Planning ↔ Delivery consistency audit v6",
        "",
        f"- Source SHA: `{source_sha}`",
        f"- Project: **{PROJECT_TITLE}** (#{project_number})",
        f"- Planning view: **{PLANNING_VIEW}** (`is:issue`)",
        f"- Delivery view: **{DELIVERY_VIEW}** (`is:pr is:open`)",
        f"- Work Packages: **{len(wp_parent)}**",
        f"- Mapped CRs: **{len(expected)}**",
        f"- Open PRs: **{len(open_prs)}**",
        f"- Mapped delivery PRs: **{len(authority)}**",
        f"- Repairs: **{len(repairs)}**",
        "- Remaining mismatches: **0**",
        "",
        "## Planning",
        "",
        "| CR | WP | Parent | Result |",
        "|---:|---|---:|---|",
    ]
    for r in planning_rows:
        md.append(f"| #{r['issue']} | {r['wp']} | {r['parent'] or '-'} | {r['result']} |")
    md += ["", "## Delivery", "", "| PR | Primary CR | WP | Result |", "|---:|---:|---|---|"]
    for r in delivery_rows:
        primary = f"#{r['primary_cr']}" if r["primary_cr"] else "legacy"
        md.append(f"| #{r['pr']} | {primary} | {r['wp']} | {r['result']} |")
    (REPORT_DIR / "audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "work_packages": len(wp_parent),
                "mapped_cr": len(expected),
                "open_pr": len(open_prs),
                "mapped_pr": len(authority),
                "repairs": len(repairs),
                "remaining": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
