"""Pure release-governance invariants used by DDDA promotion preflight.

The module intentionally has no network or filesystem side effects. Live GitHub
and Project V2 state is collected by Test-DDDAReleaseScope.py and converted to
the snapshot contract evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

POSITIVE_DECISIONS = {"go", "go_with_accepted_risks"}
DECISIONS = POSITIVE_DECISIONS | {"pending", "no_go"}
SEVERITIES = {"green", "amber", "red"}


@dataclass(frozen=True)
class GovernanceResult:
    status: str
    failures: tuple[str, ...]
    scope_issues: tuple[int, ...]
    accepted_risk_issues: tuple[int, ...]
    side_effects_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_scope_gate_status": self.status,
            "failing_invariants": list(self.failures),
            "scope_issues": list(self.scope_issues),
            "accepted_risk_issues": list(self.accepted_risk_issues),
            "side_effects_allowed": self.side_effects_allowed,
        }


def _ints(values: Iterable[Any]) -> set[int]:
    return {int(v) for v in values}


def _keyed(mapping: dict[Any, Any], key: int, default: Any = None) -> Any:
    if key in mapping:
        return mapping[key]
    if str(key) in mapping:
        return mapping[str(key)]
    return default


def _release_value(value: Any) -> str:
    """Normalize Project's planning projection without making it authority."""
    return str(value or "").strip().removeprefix("DDDA ")


def evaluate_physical_release_scope(
    snapshot: dict[str, Any],
    *,
    expected_source_sha: str,
    expected_version: str,
    declared_scope: Iterable[int],
) -> list[str]:
    """Return fail-closed defects between declared and physical shipping scope.

    ``physical_scope`` is collected from the last canonical SemVer tag through
    the exact candidate source.  This function intentionally does not select a
    recovery path or enlarge a Milestone: those are human governance decisions.
    """
    failures: list[str] = []
    physical = snapshot.get("physical_scope")
    if not isinstance(physical, dict):
        return ["PHYSICAL_SCOPE_EVIDENCE_MISSING"]

    if physical.get("release_source_sha") != expected_source_sha:
        failures.append("PHYSICAL_SCOPE_SOURCE_SHA_MISMATCH")
    if not str(physical.get("previous_release_tag") or "").strip():
        failures.append("PHYSICAL_SCOPE_PREVIOUS_TAG_MISSING")
    if not SHA40.fullmatch(str(physical.get("previous_release_sha") or "")):
        failures.append("PHYSICAL_SCOPE_PREVIOUS_TAG_SHA_INVALID")
    if physical.get("compare_status") not in {"ahead", "identical"}:
        failures.append("PHYSICAL_SCOPE_ANCESTRY_INVALID")

    for sha in sorted({str(x) for x in physical.get("unmapped_commit_shas", []) if str(x)}):
        failures.append(f"PHYSICAL_SCOPE_UNMAPPED_COMMIT:{sha}")

    scope = _ints(declared_scope)
    shipping = physical.get("shipping_prs")
    if not isinstance(shipping, list):
        return sorted(set(failures + ["PHYSICAL_SCOPE_SHIPPING_PR_EVIDENCE_MISSING"]))

    seen_prs: set[int] = set()
    shipping_crs: set[int] = set()
    for row in shipping:
        if not isinstance(row, dict):
            failures.append("PHYSICAL_SCOPE_SHIPPING_PR_SHAPE")
            continue
        try:
            number = int(row.get("number", 0))
        except (TypeError, ValueError):
            number = 0
        if number <= 0 or number in seen_prs:
            failures.append("PHYSICAL_SCOPE_SHIPPING_PR_IDENTITY")
            continue
        seen_prs.add(number)
        if row.get("merged") is not True:
            failures.append(f"PHYSICAL_SCOPE_PR_NOT_MERGED:PR#{number}")
        primary = row.get("primary_crs")
        if not isinstance(primary, list) or len(primary) != 1:
            failures.append(f"PHYSICAL_SCOPE_PRIMARY_CR_AMBIGUOUS:PR#{number}")
            continue
        try:
            cr = int(primary[0])
        except (TypeError, ValueError):
            failures.append(f"PHYSICAL_SCOPE_PRIMARY_CR_AMBIGUOUS:PR#{number}")
            continue
        shipping_crs.add(cr)
        if cr not in scope:
            failures.append(f"PHYSICAL_SCOPE_OUT_OF_SCOPE_PRIMARY_CR:PR#{number}:#{cr}")
            # This marker makes the mandatory human recovery decision visible
            # without allowing automation to choose scope expansion/recovery.
            failures.append("RECOVERY_DECISION_REQUIRED")
        if _release_value(row.get("target_release")) != expected_version:
            failures.append(f"PHYSICAL_SCOPE_TARGET_RELEASE_MISMATCH:PR#{number}:#{cr}")
        if row.get("milestone") != f"DDDA {expected_version}":
            failures.append(f"PHYSICAL_SCOPE_MILESTONE_MISMATCH:PR#{number}:#{cr}")

    for cr in sorted(scope - shipping_crs):
        failures.append(f"PHYSICAL_SCOPE_DECLARED_CR_NOT_SHIPPED:#{cr}")

    return sorted(set(failures))


def evaluate_merge_release_eligibility(snapshot: dict[str, Any]) -> list[str]:
    """Enforce releasable-main while an active release train is open.

    The Milestone is the release authority.  Project Target Release is checked
    as its planning projection, never used to permit an otherwise out-of-scope
    merge.  Missing/ambiguous evidence is deliberately blocking.
    """
    active = snapshot.get("active_release")
    if active is None:
        return []
    if not isinstance(active, dict):
        return ["MERGE_ELIGIBILITY_ACTIVE_RELEASE_EVIDENCE_INVALID"]
    version = _release_value(active.get("version"))
    if not SEMVER.fullmatch(version):
        return ["MERGE_ELIGIBILITY_ACTIVE_RELEASE_EVIDENCE_INVALID"]
    primary = snapshot.get("primary_crs")
    if not isinstance(primary, list) or len(primary) != 1:
        return ["MERGE_ELIGIBILITY_PRIMARY_CR_AMBIGUOUS"]
    try:
        cr = int(primary[0])
    except (TypeError, ValueError):
        return ["MERGE_ELIGIBILITY_PRIMARY_CR_AMBIGUOUS"]
    authority = snapshot.get("primary_cr")
    if not isinstance(authority, dict):
        return ["MERGE_ELIGIBILITY_PRIMARY_CR_EVIDENCE_MISSING"]
    failures: list[str] = []
    if authority.get("milestone") != f"DDDA {version}":
        failures.append(f"MERGE_ELIGIBILITY_OUTSIDE_ACTIVE_RELEASE:#{cr}")
    target = _release_value(authority.get("target_release"))
    if target and target != version:
        failures.append(f"MERGE_ELIGIBILITY_TARGET_RELEASE_MISMATCH:#{cr}")
    return sorted(set(failures))


def validate_hrdr_shape(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if record.get("schema_version") != 1:
        failures.append("HRDR_SCHEMA_VERSION")
    if not isinstance(record.get("repository"), str) or "/" not in record.get("repository", ""):
        failures.append("HRDR_REPOSITORY")
    try:
        if int(record.get("pr", 0)) <= 0:
            failures.append("HRDR_PR")
    except (TypeError, ValueError):
        failures.append("HRDR_PR")
    if not SHA40.fullmatch(str(record.get("source_sha", ""))):
        failures.append("HRDR_SOURCE_SHA")
    if not SHA256.fullmatch(str(record.get("candidate_package_sha256", ""))):
        failures.append("HRDR_PACKAGE_SHA256")
    if not SEMVER.fullmatch(str(record.get("version", ""))):
        failures.append("HRDR_VERSION")

    decision = str(record.get("decision", "")).lower()
    if decision not in DECISIONS:
        failures.append("HRDR_DECISION")
    if decision != "pending":
        if not str(record.get("reviewer", "")).strip():
            failures.append("HRDR_REVIEWER")
        if not str(record.get("decision_owner", "")).strip():
            failures.append("HRDR_DECISION_OWNER")
        if not str(record.get("decided_at", "")).strip():
            failures.append("HRDR_DECIDED_AT")

    findings = record.get("findings", [])
    if not isinstance(findings, list):
        failures.append("HRDR_FINDINGS")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict) or str(finding.get("severity", "")).lower() not in SEVERITIES:
            failures.append("HRDR_FINDING_SEVERITY")

    risks = record.get("accepted_risks", [])
    if not isinstance(risks, list):
        failures.append("HRDR_ACCEPTED_RISKS")
        risks = []
    risk_issues: set[int] = set()
    risk_ids: set[str] = set()
    for risk in risks:
        if not isinstance(risk, dict):
            failures.append("HRDR_RISK_SHAPE")
            continue
        rid = str(risk.get("risk_id", "")).strip()
        owner = str(risk.get("owner", "")).strip()
        rationale = str(risk.get("rationale", "")).strip()
        horizon = str(risk.get("target_horizon", "")).strip()
        try:
            issue = int(risk.get("issue", 0))
        except (TypeError, ValueError):
            issue = 0
        if not rid or rid in risk_ids:
            failures.append("HRDR_RISK_ID")
        if issue <= 0 or issue in risk_issues:
            failures.append("HRDR_RISK_ISSUE")
        if not owner:
            failures.append("HRDR_RISK_OWNER")
        if not rationale:
            failures.append("HRDR_RISK_RATIONALE")
        if not horizon:
            failures.append("HRDR_RISK_HORIZON")
        risk_ids.add(rid)
        if issue > 0:
            risk_issues.add(issue)

    if decision == "go" and risks:
        failures.append("HRDR_GO_HAS_ACCEPTED_RISKS")
    if decision == "go_with_accepted_risks" and not risks:
        failures.append("HRDR_GO_WITHOUT_ACCEPTED_RISKS")

    scope = record.get("scope_issues", [])
    if not isinstance(scope, list) or not scope:
        failures.append("HRDR_SCOPE_ISSUES")
    else:
        try:
            values = [int(v) for v in scope]
            if any(v <= 0 for v in values) or len(set(values)) != len(values):
                failures.append("HRDR_SCOPE_ISSUES")
        except (TypeError, ValueError):
            failures.append("HRDR_SCOPE_ISSUES")

    return sorted(set(failures))


def evaluate_release_scope(
    record: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    expected_repository: str,
    expected_pr: int,
    expected_source_sha: str,
    expected_package_sha256: str,
    expected_version: str,
) -> GovernanceResult:
    failures = validate_hrdr_shape(record)

    if record.get("repository") != expected_repository:
        failures.append("IDENTITY_REPOSITORY_MISMATCH")
    if int(record.get("pr", 0) or 0) != int(expected_pr):
        failures.append("IDENTITY_PR_MISMATCH")
    if record.get("source_sha") != expected_source_sha:
        failures.append("IDENTITY_SOURCE_SHA_MISMATCH")
    if record.get("candidate_package_sha256") != expected_package_sha256:
        failures.append("IDENTITY_PACKAGE_SHA256_MISMATCH")
    if record.get("version") != expected_version:
        failures.append("IDENTITY_VERSION_MISMATCH")
    if snapshot.get("current_pr_head") != expected_source_sha:
        failures.append("LIVE_PR_HEAD_MISMATCH")

    decision = str(record.get("decision", "")).lower()
    if decision not in POSITIVE_DECISIONS:
        failures.append("HUMAN_RELEASE_DECISION_NOT_POSITIVE")

    if any(str(x.get("severity", "")).lower() == "red" for x in record.get("findings", []) if isinstance(x, dict)):
        failures.append("RED_FINDING_PRESENT")

    scope_issues = _ints(record.get("scope_issues", [])) if isinstance(record.get("scope_issues"), list) else set()
    milestone_issues = _ints(snapshot.get("milestone_issues", []))
    if snapshot.get("milestone_title") != f"DDDA {expected_version}":
        failures.append("MILESTONE_IDENTITY_MISMATCH")
    if scope_issues != milestone_issues:
        failures.append("MILESTONE_SCOPE_MISMATCH")

    issue_states = snapshot.get("issue_states", {})
    blockers = snapshot.get("blockers", {})
    project_rows = snapshot.get("project_rows", {})

    for issue in sorted(scope_issues):
        if _keyed(issue_states, issue) != "closed":
            failures.append(f"SCOPE_ITEM_NOT_TERMINAL:#{issue}")
        active = _keyed(blockers, issue, []) or []
        if active:
            failures.append(f"SCOPE_ITEM_ACTIVE_BLOCKER:#{issue}")
        row = _keyed(project_rows, issue)
        if not isinstance(row, dict):
            failures.append(f"SCOPE_ITEM_MISSING_PROJECT_ROW:#{issue}")
        else:
            if row.get("Status") != "Done":
                failures.append(f"SCOPE_ITEM_PROJECT_STATUS:#{issue}")
            if row.get("Blocked") != "No":
                failures.append(f"SCOPE_ITEM_PROJECT_BLOCKED:#{issue}")

    accepted_risks = record.get("accepted_risks", []) if isinstance(record.get("accepted_risks"), list) else []
    risk_issues = {
        int(risk.get("issue"))
        for risk in accepted_risks
        if isinstance(risk, dict) and str(risk.get("issue", "")).isdigit() and int(risk.get("issue")) > 0
    }
    risk_states = snapshot.get("risk_issue_states", {})
    risk_assignees = snapshot.get("risk_issue_assignees", {})
    risk_horizons = snapshot.get("risk_issue_horizons", {})
    for risk in accepted_risks:
        if not isinstance(risk, dict):
            continue
        try:
            issue = int(risk.get("issue", 0))
        except (TypeError, ValueError):
            continue
        owner = str(risk.get("owner", ""))
        if issue in milestone_issues:
            failures.append(f"DEFERRED_RISK_STILL_IN_MILESTONE:#{issue}")
        if _keyed(risk_states, issue) != "open":
            failures.append(f"DEFERRED_RISK_NOT_OPEN:#{issue}")
        assignees = set(_keyed(risk_assignees, issue, []) or [])
        if owner and owner not in assignees:
            failures.append(f"DEFERRED_RISK_OWNER_MISMATCH:#{issue}")
        if not str(_keyed(risk_horizons, issue, "") or "").strip():
            failures.append(f"DEFERRED_RISK_HORIZON_MISSING:#{issue}")

    if decision == "go" and risk_issues:
        failures.append("GO_WITH_RESIDUAL_RISKS")
    if decision == "go_with_accepted_risks" and not risk_issues:
        failures.append("GO_WITH_ACCEPTED_RISKS_EMPTY")

    project_meta = snapshot.get("project", {})
    if project_meta.get("title") != "DDDA Platform Backlog & Delivery":
        failures.append("PROJECT_TITLE_MISMATCH")
    if project_meta.get("planning_view_filter") != "is:issue":
        failures.append("PROJECT_PLANNING_VIEW_MISMATCH")
    if project_meta.get("delivery_view_filter") != "is:pr is:open":
        failures.append("PROJECT_DELIVERY_VIEW_MISMATCH")

    failures.extend(
        evaluate_physical_release_scope(
            snapshot,
            expected_source_sha=expected_source_sha,
            expected_version=expected_version,
            declared_scope=scope_issues,
        )
    )

    failures = sorted(set(failures))
    return GovernanceResult(
        status="PASS" if not failures else "FAIL",
        failures=tuple(failures),
        scope_issues=tuple(sorted(scope_issues)),
        accepted_risk_issues=tuple(sorted(risk_issues)),
        side_effects_allowed=not failures,
    )
