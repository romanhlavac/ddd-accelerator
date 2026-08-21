"""Lifecycle-aware entrypoint for DDDA Project backlog reconciliation.

The stable v6 reconciler core lives in Reconcile-DDDAProjectBacklogCore.py.
This entrypoint overlays one governance invariant that the original reconciler
did not model: native ``blocked_by`` is an *active unresolved dependency
projection*, not immutable history.

The versioned ``dependencies`` list remains prerequisite/history authority.
A live native edge exists only while both the blocked issue and blocker are
open. Closed planning items are terminal and cannot remain operationally
blocked.
"""

import importlib.util
from pathlib import Path

CORE_PATH = Path(__file__).with_name("Reconcile-DDDAProjectBacklogCore.py")

_spec = importlib.util.spec_from_file_location("ddda_project_backlog_core", CORE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load backlog reconciler core: {CORE_PATH}")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

_base_reconcile_planning = core.reconcile_planning
_base_verify_planning = core.verify_planning


def active_dependency_projection(expected, dependencies, details):
    """Return unresolved live blockers for every governed Change Request.

    ``dependencies`` is the versioned prerequisite topology. Native GitHub
    blocked-by relations are operational state and therefore materialize only
    when both endpoints are still open. This keeps historical prerequisite
    traceability in Git while preventing completed work from looking blocked.
    """
    governed = {int(n) for n in expected}
    endpoints = set()
    for blocked, blockers in dependencies.items():
        endpoints.add(int(blocked))
        endpoints.update(int(x) for x in blockers)
    unknown = sorted(endpoints - governed)
    if unknown:
        raise RuntimeError(
            "Dependency endpoint outside governed Change Request set: "
            + ", ".join(f"#{n}" for n in unknown)
        )

    missing_details = sorted(governed - set(details))
    if missing_details:
        raise RuntimeError(
            "Missing live Issue state for governed Change Requests: "
            + ", ".join(f"#{n}" for n in missing_details)
        )

    active = {}
    for blocked in sorted(governed):
        if details[blocked].get("state") == "closed":
            active[blocked] = set()
            continue
        active[blocked] = {
            blocker
            for blocker in dependencies.get(blocked, set())
            if details[blocker].get("state") != "closed"
        }
    return active


def _live_details(expected):
    return {int(n): core.issue(int(n)) for n in expected}


def reconcile_dependencies(dependencies, repairs):
    """Reconcile the complete governed graph to unresolved native blockers."""
    _, _, _, expected, _ = core.load_contract()
    details = _live_details(expected)
    active = active_dependency_projection(expected, dependencies, details)

    for blocked, wanted in sorted(active.items()):
        current = core.current_blockers(blocked)
        for extra in sorted(set(current) - wanted):
            core.gh(
                "api",
                "--method",
                "DELETE",
                f"repos/{core.REPO}/issues/{blocked}/dependencies/blocked_by/{current[extra]['id']}",
            )
            repairs.append(
                {
                    "issue": blocked,
                    "action": "REMOVE_RESOLVED_OR_UNDECLARED_BLOCKED_BY",
                    "value": extra,
                }
            )
        for missing in sorted(wanted - set(current)):
            blocker = details[missing]
            core.gh(
                "api",
                "--method",
                "POST",
                f"repos/{core.REPO}/issues/{blocked}/dependencies/blocked_by",
                "-F",
                f"issue_id={blocker['id']}",
            )
            repairs.append(
                {
                    "issue": blocked,
                    "action": "ADD_ACTIVE_BLOCKED_BY",
                    "value": missing,
                }
            )


def _terminal_status(data):
    if data.get("state") != "closed":
        return None
    return (
        "Cancelled"
        if data.get("state_reason") in ("not_planned", "duplicate")
        else "Done"
    )


def _unblocked_fallback_status(meta):
    candidate = (meta or {}).get("Status")
    if candidate in (None, "Blocked", "Done", "Cancelled"):
        return "Backlog"
    return candidate




def derive_delivery_projection(authority, active_blockers):
    """Derive PR Blocked/Status only from primary-CR unresolved blockers."""
    projection = {}
    for n, rel in sorted(authority.items()):
        primary_cr = rel.get("primary_cr")
        if primary_cr is None:
            if int(n) not in core.LEGACY_PR_WP:
                raise RuntimeError(
                    f"Open PR #{n} has no authoritative primary Change Request"
                )
            blockers = set()
        else:
            if primary_cr not in active_blockers:
                raise RuntimeError(
                    f"Open PR #{n} primary CR #{primary_cr} has no governed blocker state"
                )
            blockers = set(active_blockers[primary_cr])

        blocked = bool(blockers)
        projection[int(n)] = {
            "Blocked": "Yes" if blocked else "No",
            "Status": (
                "Blocked"
                if blocked
                else ("In progress" if rel["pr"].get("draft") else "In review")
            ),
            "authoritative_blockers": sorted(blockers),
        }
    return projection


def delivery_projection_repairs(current, wanted):
    """Return semantic Project field repairs without treating fields as authority."""
    repairs = []
    if current.get("Blocked") != wanted["Blocked"]:
        repairs.append(("Blocked", "SET_DELIVERY_BLOCKED", wanted["Blocked"]))
    if current.get("Status") != wanted["Status"]:
        repairs.append(("Status", "SET_DELIVERY_STATUS", wanted["Status"]))
    return repairs


def delivery_projection_mismatches(current, wanted):
    """Compare Project projection against authoritative blocker-derived state."""
    problems = []
    if current.get("Blocked") != wanted["Blocked"]:
        problems.append("DELIVERY_BLOCKED_FLAG_MISMATCH")
    if current.get("Status") != wanted["Status"]:
        problems.append("DELIVERY_STATUS_MISMATCH")
    return problems


def delivery_authority_signature(authority):
    """Capture identity/state inputs that must stay stable through reconciliation."""
    signature = {}
    for n, rel in sorted(authority.items()):
        pr = rel["pr"]
        head = pr.get("head")
        head_sha = head.get("sha") if isinstance(head, dict) else pr.get("head_sha")
        signature[int(n)] = {
            "primary_cr": rel.get("primary_cr"),
            "wp": rel.get("wp"),
            "draft": bool(pr.get("draft")),
            "head_sha": head_sha,
        }
    return signature


def _fresh_delivery_authority(expected):
    return core.delivery_authority(core.discover_open_prs(), expected)


def reconcile_delivery(authority, project_number, project_id, fields, repairs):
    """Project delivery fields are projections of fresh governance authority."""
    _, _, _, expected, dependencies = core.load_contract()
    details = _live_details(expected)
    active = active_dependency_projection(expected, dependencies, details)
    wanted_by_pr = derive_delivery_projection(authority, active)
    items = core.content_item_map(project_number, "PullRequest")

    for n, rel in sorted(authority.items()):
        pr = rel["pr"]
        item = items.get(n)
        current = {}
        if item is None:
            item_id = core.add_project_item(project_id, pr)
            repairs.append({"pr": n, "action": "ADD_DELIVERY_PROJECT_ITEM"})
        else:
            item_id = item["id"]
            current = core.values(item)

        wp = rel["wp"]
        if current.get("Work Package") != wp:
            core.set_select(project_id, fields, item_id, "Work Package", wp)
            repairs.append(
                {"pr": n, "action": "SET_DELIVERY_WORK_PACKAGE", "value": wp}
            )

        for field, action, value in delivery_projection_repairs(
            current, wanted_by_pr[n]
        ):
            core.set_select(project_id, fields, item_id, field, value)
            repairs.append({"pr": n, "action": action, "value": value})

        if current.get("Item Type") is not None:
            core.clear_field(project_id, fields, item_id, "Item Type")
            repairs.append({"pr": n, "action": "CLEAR_PLANNING_ITEM_TYPE"})


def _verify_delivery_snapshot(authority, project_number, active):
    wanted_by_pr = derive_delivery_projection(authority, active)
    items = core.content_item_map(project_number, "PullRequest")
    rows, problems = [], []

    for n, rel in sorted(authority.items()):
        item = items.get(n)
        rowprobs = []
        if not item:
            rowprobs.append("MISSING_DELIVERY_PROJECT_ITEM")
            current = {}
        else:
            current = core.values(item)
            if current.get("Work Package") != rel["wp"]:
                rowprobs.append("DELIVERY_WORK_PACKAGE_MISMATCH")
            rowprobs.extend(
                delivery_projection_mismatches(current, wanted_by_pr[n])
            )
            if current.get("Item Type") is not None:
                rowprobs.append("DELIVERY_HAS_PLANNING_ITEM_TYPE")

        row = {
            "pr": n,
            "primary_cr": rel["primary_cr"],
            "wp": rel["wp"],
            "authoritative_blockers": wanted_by_pr[n]["authoritative_blockers"],
            "fields": current,
            "result": "PASS" if not rowprobs else "+".join(rowprobs),
        }
        rows.append(row)
        if rowprobs:
            problems.append(row)

    return rows, problems


def _delivery_authority_drift(expected, actual):
    return {
        "result": "DELIVERY_AUTHORITY_CHANGED_DURING_RECONCILIATION",
        "expected": expected,
        "actual": actual,
    }


def verify_delivery(
    authority,
    project_number,
    max_attempts=3,
    delay_seconds=2,
    sleep_fn=None,
):
    """Fresh, bounded read-back; authority drift invalidates technical PASS."""
    if sleep_fn is None:
        sleep_fn = core.time.sleep

    expected_signature = delivery_authority_signature(authority)
    last_rows, last_problems = [], []

    for attempt in range(1, max_attempts + 1):
        _, _, _, expected, dependencies = core.load_contract()
        fresh_authority = _fresh_delivery_authority(expected)
        fresh_signature = delivery_authority_signature(fresh_authority)
        if fresh_signature != expected_signature:
            return [], [_delivery_authority_drift(expected_signature, fresh_signature)]

        details = _live_details(expected)
        active = active_dependency_projection(expected, dependencies, details)
        rows, problems = _verify_delivery_snapshot(
            fresh_authority, project_number, active
        )

        if not problems:
            confirm_authority = _fresh_delivery_authority(expected)
            confirm_signature = delivery_authority_signature(confirm_authority)
            if confirm_signature != fresh_signature:
                return rows, [
                    _delivery_authority_drift(fresh_signature, confirm_signature)
                ]

            confirm_details = _live_details(expected)
            confirm_active = active_dependency_projection(
                expected, dependencies, confirm_details
            )
            confirm_rows, confirm_problems = _verify_delivery_snapshot(
                confirm_authority, project_number, confirm_active
            )
            if not confirm_problems:
                return confirm_rows, []
            rows, problems = confirm_rows, confirm_problems

        last_rows, last_problems = rows, problems
        if attempt < max_attempts:
            sleep_fn(delay_seconds)

    return last_rows, last_problems


def reconcile_planning(
    wp_parent,
    item_meta,
    expected,
    details,
    project_number,
    project_id,
    fields,
    repairs,
):
    """Run base planning reconcile, then align operational blocker lifecycle."""
    _base_reconcile_planning(
        wp_parent,
        item_meta,
        expected,
        details,
        project_number,
        project_id,
        fields,
        repairs,
    )

    _, _, _, _, dependencies = core.load_contract()
    active = active_dependency_projection(expected, dependencies, details)
    items = core.content_item_map(project_number, "Issue")

    for n in sorted(expected):
        item = items.get(n)
        if not item:
            continue
        current = core.values(item)
        item_id = item["id"]
        terminal = _terminal_status(details[n])

        if terminal is not None:
            wanted_blocked = "No"
            wanted_status = terminal
        elif active[n]:
            wanted_blocked = "Yes"
            wanted_status = "Blocked"
        else:
            wanted_blocked = "No"
            wanted_status = (
                _unblocked_fallback_status(item_meta.get(n))
                if current.get("Status") in (None, "Done", "Cancelled", "Blocked")
                else current.get("Status")
            )

        if current.get("Blocked") != wanted_blocked:
            core.set_select(
                project_id, fields, item_id, "Blocked", wanted_blocked
            )
            repairs.append(
                {
                    "issue": n,
                    "action": "SET_PLANNING_BLOCKED",
                    "value": wanted_blocked,
                }
            )

        if wanted_status and current.get("Status") != wanted_status:
            core.set_select(project_id, fields, item_id, "Status", wanted_status)
            repairs.append(
                {
                    "issue": n,
                    "action": "SET_PLANNING_STATUS",
                    "value": wanted_status,
                }
            )


def verify_planning(wp_parent, expected, dependencies, project_number):
    """Fail closed on dependency, terminal-status and blocked-flag drift."""
    details = _live_details(expected)
    active = active_dependency_projection(expected, dependencies, details)

    # Reuse the stable structural/project checks, but compare live dependencies
    # against the unresolved projection rather than immutable prerequisite history.
    rows, problems = _base_verify_planning(
        wp_parent, expected, active, project_number
    )
    items = core.content_item_map(project_number, "Issue")
    problem_issues = {
        int(p["issue"])
        for p in problems
        if isinstance(p, dict) and p.get("issue") is not None
    }

    for row in rows:
        n = int(row["issue"])
        item = items.get(n)
        values = core.values(item) if item else {}
        live_blockers = set(core.current_blockers(n))
        rowprobs = []

        terminal = _terminal_status(details[n])
        if terminal is not None:
            if live_blockers:
                rowprobs.append("CLOSED_ITEM_ACTIVE_BLOCKER")
            if values.get("Blocked") != "No":
                rowprobs.append("CLOSED_ITEM_BLOCKED_FLAG")
            if values.get("Status") != terminal:
                rowprobs.append("TERMINAL_STATUS_MISMATCH")
        else:
            wanted_blocked = "Yes" if active[n] else "No"
            if values.get("Blocked") != wanted_blocked:
                rowprobs.append("PLANNING_BLOCKED_FLAG_MISMATCH")
            if active[n] and values.get("Status") != "Blocked":
                rowprobs.append("PLANNING_BLOCKED_STATUS_MISMATCH")
            if not active[n] and values.get("Status") == "Blocked":
                rowprobs.append("PLANNING_STALE_BLOCKED_STATUS")

        row["active_blockers"] = sorted(live_blockers)
        if rowprobs:
            prior = [] if row["result"] == "PASS" else row["result"].split("+")
            row["result"] = "+".join(prior + rowprobs)
            if n not in problem_issues:
                problems.append(row)
                problem_issues.add(n)

    return rows, problems


core.reconcile_dependencies = reconcile_dependencies
core.reconcile_planning = reconcile_planning
core.verify_planning = verify_planning
core.reconcile_delivery = reconcile_delivery
core.verify_delivery = verify_delivery
main = core.main


if __name__ == "__main__":
    main()
