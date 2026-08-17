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
main = core.main


if __name__ == "__main__":
    main()
