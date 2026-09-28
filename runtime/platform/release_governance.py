"""Pure release-governance invariants used by DDDA promotion preflight.

The module intentionally has no network or filesystem side effects. Live GitHub
and Project V2 state is collected by Test-DDDAReleaseScope.py and converted to
the snapshot contract evaluated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

try:
    from .governance_kernel import (
        evaluate_hrdr_binding,
        evaluate_physical_scope_binding,
        evaluate_promotion_readiness,
    )
except ImportError:  # direct script/runtime path import
    from governance_kernel import (
        evaluate_hrdr_binding,
        evaluate_physical_scope_binding,
        evaluate_promotion_readiness,
    )

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
    physical = snapshot.get("physical_scope")
    scope = _ints(declared_scope)
    decision = evaluate_physical_scope_binding(
        physical,
        expected_source_sha=expected_source_sha,
        expected_version=expected_version,
        declared_scope=scope,
    )
    failures = list(decision.failure_codes)
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
    # A future-release plan is repository governance metadata, not shipping
    # content for the currently open train.  The collector proves this from
    # the PR's changed paths and a base/head comparison of the active release
    # contract.  Missing or malformed evidence never creates an exception.
    future_plan = snapshot.get("future_release_metadata")
    if isinstance(future_plan, dict) and future_plan.get("status") == "PASS":
        return []

    # This is a one-time prospective transition for the guard that introduces
    # the future-plan exception itself.  It is exact-base-bound so it expires
    # as soon as main advances; it cannot become a reusable bypass.
    transition = snapshot.get("merge_eligibility_transition")
    if isinstance(transition, dict) and transition.get("status") == "PASS":
        return []

    # Guard-only repairs are bounded to three implementation-evidence paths
    # and prove the complete versioned governance contract is unchanged.  The
    # bootstrap that introduces this allowance is itself exact-base-bound.
    governance_repair = snapshot.get("governance_repair")
    if isinstance(governance_repair, dict) and governance_repair.get("status") == "PASS":
        return []
    governance_repair_transition = snapshot.get("governance_repair_transition")
    if isinstance(governance_repair_transition, dict) and governance_repair_transition.get("status") == "PASS":
        return []

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

    hrdr_context = {
        "operation": "release_scope_validation",
        "repository": expected_repository,
        "pr": expected_pr,
        "source_sha": expected_source_sha,
        "version": expected_version,
        "validation_evidence": {"package_sha256": expected_package_sha256},
        "hrdr_reference": {
            "repository": record.get("repository"),
            "pr": record.get("pr"),
            "decision": str(record.get("decision") or "").upper(),
            "source_sha": record.get("source_sha"),
            "candidate_package_sha256": record.get("candidate_package_sha256"),
            "version": record.get("version"),
            "decision_owner": record.get("decision_owner"),
            "decided_at": record.get("decided_at"),
            # The upstream collector verifies comment provenance; this pure
            # compatibility evaluator receives only the parsed record.
            "provenance_verified": True,
        },
    }
    compatibility_codes = {
        "HRDR_REPOSITORY_MISMATCH": "IDENTITY_REPOSITORY_MISMATCH",
        "HRDR_PR_MISMATCH": "IDENTITY_PR_MISMATCH",
        "HRDR_SOURCE_SHA_MISMATCH": "IDENTITY_SOURCE_SHA_MISMATCH",
        "HRDR_PACKAGE_SHA256_MISMATCH": "IDENTITY_PACKAGE_SHA256_MISMATCH",
        "HRDR_VERSION_MISMATCH": "IDENTITY_VERSION_MISMATCH",
        "HRDR_NOT_POSITIVE": "HUMAN_RELEASE_DECISION_NOT_POSITIVE",
    }
    failures.extend(
        compatibility_codes.get(code, code)
        for code in evaluate_hrdr_binding(hrdr_context).failure_codes
    )
    if snapshot.get("current_pr_head") != expected_source_sha:
        failures.append("LIVE_PR_HEAD_MISMATCH")

    decision = str(record.get("decision", "")).lower()
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
    base_result = GovernanceResult(
        status="PASS" if not failures else "FAIL",
        failures=tuple(failures),
        scope_issues=tuple(sorted(scope_issues)),
        accepted_risk_issues=tuple(sorted(risk_issues)),
        side_effects_allowed=not failures,
    )
    readiness = evaluate_promotion_readiness(
        base_result.failures,
        operation="release_scope_validation",
    )
    return GovernanceResult(
        status=readiness.status,
        failures=readiness.failure_codes,
        scope_issues=base_result.scope_issues,
        accepted_risk_issues=base_result.accepted_risk_issues,
        # This is adapter execution eligibility, not authorization. The kernel
        # always returns side_effects_allowed=false; ConfirmMerge or
        # ConfirmPromotion is still proved separately at the executor boundary.
        side_effects_allowed=readiness.status == "PASS",
    )
