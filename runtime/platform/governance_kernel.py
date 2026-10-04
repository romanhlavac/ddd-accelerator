"""Pure Candidate Context v1 governance decisions.

Collectors normalize live evidence into Candidate Context.  This module does
not read files, call GitHub, mutate Project state, or execute side effects.
Human authorization remains an adapter responsibility and is never inferred
from a technical PASS.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
STABLE_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

OPERATIONS = {
    "validate",
    "publish_hrdr_scaffold",
    "merge_dry_run",
    "merge",
    "release_scope_validation",
    "promotion_dry_run",
    "release",
}
RECOVERY_DRAFT_OPERATIONS = {"validate", "publish_hrdr_scaffold"}
RECOVERY_READY_OPERATIONS = {
    "release_scope_validation",
    "promotion_dry_run",
    "release",
}
MERGE_OPERATIONS = {"merge_dry_run", "merge"}
RELEASE_OPERATIONS = {
    "release_scope_validation",
    "promotion_dry_run",
    "release",
}
POSITIVE_HRDR = {"GO", "GO_WITH_ACCEPTED_RISKS"}
CONTEXT_FIELDS = {
    "schema_version",
    "context_kind",
    "candidate_kind",
    "release_mode",
    "operation",
    "repository",
    "pr",
    "base_branch",
    "source_branch",
    "source_sha",
    "version",
    "generation",
    "pr_state",
    "validation_evidence",
    "authoritative_check_summary",
    "human_review_reference",
    "hrdr_reference",
    "physical_scope_reference",
    "project_evidence_reference",
}


@dataclass(frozen=True)
class KernelDecision:
    status: str
    operation: str
    failure_codes: tuple[str, ...]
    authorization_required: bool
    side_effects_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "decision_kind": "ddda_governance_kernel_decision",
            "status": self.status,
            "operation": self.operation,
            "failure_codes": list(self.failure_codes),
            "authorization_required": self.authorization_required,
            "side_effects_allowed": self.side_effects_allowed,
        }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _base_failures(context: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    missing = CONTEXT_FIELDS - set(context)
    unknown = set(context) - CONTEXT_FIELDS
    if missing:
        failures.extend(f"CONTEXT_FIELD_MISSING:{name}" for name in sorted(missing))
    if unknown:
        failures.extend(f"CONTEXT_FIELD_UNKNOWN:{name}" for name in sorted(unknown))
    if context.get("schema_version") != 1:
        failures.append("CONTEXT_SCHEMA_VERSION")
    if context.get("context_kind") != "ddda_candidate_context":
        failures.append("CONTEXT_KIND")

    candidate_kind = context.get("candidate_kind")
    release_mode = context.get("release_mode")
    if candidate_kind not in {"NORMAL", "RECOVERY"}:
        failures.append("CANDIDATE_KIND_INVALID")
    if release_mode not in {"STANDARD", "CONTROLLED_RECOVERY"}:
        failures.append("RELEASE_MODE_INVALID")
    if (
        candidate_kind in {"NORMAL", "RECOVERY"}
        and release_mode in {"STANDARD", "CONTROLLED_RECOVERY"}
        and (candidate_kind == "RECOVERY") != (release_mode == "CONTROLLED_RECOVERY")
    ):
        failures.append("CANDIDATE_KIND_RELEASE_MODE_MISMATCH")

    operation = context.get("operation")
    if operation not in OPERATIONS:
        failures.append("OPERATION_INVALID")
    if not REPOSITORY.fullmatch(str(context.get("repository") or "")):
        failures.append("REPOSITORY_INVALID")
    try:
        if int(context.get("pr", 0)) <= 0:
            failures.append("PR_INVALID")
    except (TypeError, ValueError):
        failures.append("PR_INVALID")
    if str(context.get("base_branch") or "") != "main":
        failures.append("BASE_BRANCH_INVALID")
    if not str(context.get("source_branch") or "").strip():
        failures.append("SOURCE_BRANCH_INVALID")
    if not SHA40.fullmatch(str(context.get("source_sha") or "")):
        failures.append("SOURCE_SHA_INVALID")
    if not SEMVER.fullmatch(str(context.get("version") or "")):
        failures.append("VERSION_INVALID")
    try:
        if int(context.get("generation", 0)) <= 0:
            failures.append("GENERATION_INVALID")
    except (TypeError, ValueError):
        failures.append("GENERATION_INVALID")
    if context.get("pr_state") not in {"DRAFT", "READY", "MERGED_CLOSED"}:
        failures.append("PR_STATE_INVALID")
    return failures


def _candidate_identity_failures(context: dict[str, Any]) -> list[str]:
    failures = _base_failures(context)
    if context.get("candidate_kind") != "RECOVERY":
        return failures

    version = str(context.get("version") or "")
    if not STABLE_VERSION.fullmatch(version):
        failures.append("RECOVERY_VERSION_INVALID")

    try:
        generation = int(context.get("generation", 0))
    except (TypeError, ValueError):
        generation = 0
    suffix = "" if generation == 1 else f"-v{generation}"
    expected_branch = f"release/{version}-controlled-recovery-source{suffix}"
    if generation <= 0 or context.get("source_branch") != expected_branch:
        failures.append("RECOVERY_BRANCH_INVALID")

    operation = context.get("operation")
    pr_state = context.get("pr_state")
    if pr_state == "MERGED_CLOSED":
        failures.append("CANDIDATE_MUST_BE_OPEN")
    elif operation in RECOVERY_DRAFT_OPERATIONS and pr_state != "DRAFT":
        failures.append("RECOVERY_PREPARATION_REQUIRES_DRAFT")
    elif operation in RECOVERY_READY_OPERATIONS and pr_state != "READY":
        failures.append("RECOVERY_DRY_RUN_REQUIRES_READY")
    return failures


def _validation_failures(context: dict[str, Any]) -> list[str]:
    evidence = _mapping(context.get("validation_evidence"))
    failures: list[str] = []
    if not evidence:
        return ["VALIDATION_EVIDENCE_MISSING"]
    if evidence.get("status") != "PASS":
        failures.append("VALIDATION_NOT_PASS")
    if evidence.get("repository") != context.get("repository"):
        failures.append("VALIDATION_REPOSITORY_MISMATCH")
    try:
        if int(evidence.get("pr", 0)) != int(context.get("pr", 0)):
            failures.append("VALIDATION_PR_MISMATCH")
    except (TypeError, ValueError):
        failures.append("VALIDATION_PR_MISMATCH")
    if evidence.get("source_sha") != context.get("source_sha"):
        failures.append("VALIDATION_SOURCE_SHA_MISMATCH")
    expected_package_sha = str(evidence.get("package_sha256") or "")
    observed_package_sha = str(evidence.get("observed_package_sha256") or "")
    if not SHA256.fullmatch(expected_package_sha):
        failures.append("VALIDATION_PACKAGE_SHA256_INVALID")
    if evidence.get("package_present") is not True:
        failures.append("CANDIDATE_PACKAGE_MISSING")
    elif not SHA256.fullmatch(observed_package_sha):
        failures.append("CANDIDATE_PACKAGE_SHA256_INVALID")
    elif expected_package_sha != observed_package_sha:
        failures.append("CANDIDATE_PACKAGE_SHA256_MISMATCH")
    if not str(evidence.get("artifact_name") or "").strip():
        failures.append("VALIDATION_ARTIFACT_INVALID")
    try:
        if int(evidence.get("workflow_run_id", 0)) <= 0:
            failures.append("VALIDATION_WORKFLOW_RUN_INVALID")
    except (TypeError, ValueError):
        failures.append("VALIDATION_WORKFLOW_RUN_INVALID")
    return failures


def evaluate_check_summary(checks: Any, *, source_sha: str) -> dict[str, Any]:
    """Resolve attempts and explicit-success semantics in the singular kernel.

    GitHub allocates a new check-run/status ID for each newly created attempt.
    Highest numeric ID wins within the exact name and producer. Start/completion
    timestamps cannot resurrect an older attempt. Conflicting duplicate IDs or
    multiple producers are ambiguous and cannot satisfy a mandatory check.
    """
    checks = _mapping(checks)
    failures: list[str] = []
    if not checks:
        failures.append("AUTHORITATIVE_CHECK_SUMMARY_MISSING")
    elif checks.get("status") != "PASS":
        failures.append("AUTHORITATIVE_CHECKS_NOT_PASS")
    if not SHA40.fullmatch(str(source_sha or "")):
        failures.append("AUTHORITATIVE_SOURCE_SHA_INVALID")
    if checks.get("source_sha") != source_sha:
        failures.append("AUTHORITATIVE_CHECK_SOURCE_SHA_MISMATCH")
    required = checks.get("required_checks")
    if (not isinstance(required, list) or not required
            or any(not isinstance(name, str) or not name for name in required)):
        failures.append("AUTHORITATIVE_REQUIRED_CHECKS_MISSING")
        required = []
    elif len(required) != len(set(required)):
        failures.append("AUTHORITATIVE_REQUIRED_CHECKS_AMBIGUOUS")
    if checks.get("accepted_conclusions", ["SUCCESS"]) != ["SUCCESS"]:
        failures.append("AUTHORITATIVE_ACCEPTED_CONCLUSION_POLICY_INVALID")
    rows = checks.get("latest_results")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        failures.append("AUTHORITATIVE_CHECK_RESULTS_MISSING")
        rows = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        name = row.get("name")
        if isinstance(name, str) and name:
            by_name.setdefault(name, []).append(row)
    resolved: list[dict[str, Any]] = []
    for name in sorted(set(required) | set(by_name)):
        attempts = by_name.get(name, [])
        mandatory = name in required
        reason = None
        selected: dict[str, Any] = {}
        valid_ids = all(
            isinstance(row.get("run_id"), int) and not isinstance(row["run_id"], bool)
            and row["run_id"] > 0
            and (row.get("app_id") is None or (
                isinstance(row["app_id"], int) and not isinstance(row["app_id"], bool) and row["app_id"] > 0
            ))
            and all(row.get(field) is None or isinstance(row.get(field), str)
                    for field in ("source_sha", "status", "conclusion", "classification"))
            for row in attempts
        )
        if not attempts:
            reason = f"AUTHORITATIVE_CHECK_MISSING:{name}"
        elif not valid_ids:
            reason = f"AUTHORITATIVE_CHECK_ATTEMPT_INVALID:{name}"
        else:
            producers = {row.get("app_id") for row in attempts}
            latest_id = max(row["run_id"] for row in attempts)
            winners = [row for row in attempts if row["run_id"] == latest_id]
            identities = {
                (row.get("source_sha"), row.get("status"), row.get("conclusion"),
                 row.get("app_id"), row.get("classification")) for row in winners
            }
            if len(producers) != 1 or len(identities) != 1:
                reason = f"AUTHORITATIVE_CHECK_ATTEMPT_AMBIGUOUS:{name}"
            else:
                selected = dict(winners[0])
        classification = "MANDATORY" if mandatory else (
            "NOT_APPLICABLE" if selected.get("classification") == "NOT_APPLICABLE" else "OPTIONAL"
        )
        pending = False
        if mandatory and reason is None:
            if selected.get("classification") == "NOT_APPLICABLE":
                reason = f"AUTHORITATIVE_REQUIRED_CHECK_IGNORED:{name}"
            elif selected.get("source_sha") != source_sha:
                reason = f"AUTHORITATIVE_CHECK_SOURCE_SHA_MISMATCH:{name}"
            elif selected.get("status") != "COMPLETED" or selected.get("conclusion") != "SUCCESS":
                reason = f"AUTHORITATIVE_CHECK_NOT_SUCCESS:{name}"
                pending = selected.get("status") in {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED"}
        gate = ("NOT_READY" if pending or not attempts else "FAIL") if reason else "PASS"
        if not mandatory:
            gate = "NOT_APPLICABLE"
        elif reason:
            failures.append(reason)
        resolved.append({
            "name": name,
            "source_sha": selected.get("source_sha"),
            "run_id": selected.get("run_id"),
            "app_id": selected.get("app_id"),
            "status": selected.get("status", "MISSING" if not attempts else "UNKNOWN"),
            "conclusion": selected.get("conclusion"),
            "classification": classification,
            "gate_result": gate,
            "failure_reason": reason,
        })
    failures = sorted(set(failures))
    mandatory_rows = [row for row in resolved if row["classification"] == "MANDATORY"]
    only_pending = bool(failures) and all(
        row["gate_result"] in {"PASS", "NOT_READY"} for row in mandatory_rows
    ) and set(failures) == {row["failure_reason"] for row in mandatory_rows if row["failure_reason"]}
    return {
        "status": "FAIL" if failures else "PASS",
        "gate_result": "NOT_READY" if only_pending else "FAIL" if failures else "PASS",
        "failures": failures,
        "latest_results": resolved,
    }


def _check_failures(context: dict[str, Any]) -> list[str]:
    return evaluate_check_summary(
        context.get("authoritative_check_summary"), source_sha=context.get("source_sha")
    )["failures"]


def _human_review_failures(context: dict[str, Any]) -> list[str]:
    review = _mapping(context.get("human_review_reference"))
    if not review:
        return ["HUMAN_REVIEW_REQUIRED"]
    failures: list[str] = []
    if review.get("repository") != context.get("repository"):
        failures.append("HUMAN_REVIEW_REPOSITORY_MISMATCH")
    try:
        if int(review.get("pr", 0)) != int(context.get("pr", 0)):
            failures.append("HUMAN_REVIEW_PR_MISMATCH")
    except (TypeError, ValueError):
        failures.append("HUMAN_REVIEW_PR_MISMATCH")
    if review.get("verdict") != "PASS":
        failures.append("HUMAN_REVIEW_NOT_PASS")
    if review.get("reviewed_sha") != context.get("source_sha"):
        failures.append("HUMAN_REVIEW_SOURCE_SHA_MISMATCH")
    package_sha = _mapping(context.get("validation_evidence")).get("package_sha256")
    if review.get("candidate_package_sha256") != package_sha:
        failures.append("HUMAN_REVIEW_PACKAGE_SHA256_MISMATCH")
    if review.get("provenance_verified") is not True:
        failures.append("HUMAN_REVIEW_PROVENANCE_INVALID")
    if not str(review.get("reviewer") or "").strip() or not str(review.get("reviewed_at") or "").strip():
        failures.append("HUMAN_REVIEW_IDENTITY_INVALID")
    return failures


def _hrdr_failures(context: dict[str, Any]) -> list[str]:
    hrdr = _mapping(context.get("hrdr_reference"))
    if not hrdr:
        return ["HRDR_REQUIRED"]
    failures: list[str] = []
    if hrdr.get("repository") != context.get("repository"):
        failures.append("HRDR_REPOSITORY_MISMATCH")
    try:
        if int(hrdr.get("pr", 0)) != int(context.get("pr", 0)):
            failures.append("HRDR_PR_MISMATCH")
    except (TypeError, ValueError):
        failures.append("HRDR_PR_MISMATCH")
    if hrdr.get("decision") not in POSITIVE_HRDR:
        failures.append("HRDR_NOT_POSITIVE")
    if hrdr.get("source_sha") != context.get("source_sha"):
        failures.append("HRDR_SOURCE_SHA_MISMATCH")
    package_sha = _mapping(context.get("validation_evidence")).get("package_sha256")
    if hrdr.get("candidate_package_sha256") != package_sha:
        failures.append("HRDR_PACKAGE_SHA256_MISMATCH")
    if hrdr.get("version") != context.get("version"):
        failures.append("HRDR_VERSION_MISMATCH")
    if hrdr.get("provenance_verified") is not True:
        failures.append("HRDR_PROVENANCE_INVALID")
    if not str(hrdr.get("decision_owner") or "").strip() or not str(hrdr.get("decided_at") or "").strip():
        failures.append("HRDR_IDENTITY_INVALID")
    return failures


def _referenced_evidence_failure(context: dict[str, Any], field: str, code: str) -> list[str]:
    reference = _mapping(context.get(field))
    if not reference or reference.get("status") != "PASS" or not str(reference.get("evidence_id") or "").strip():
        return [code]
    return []


def _release_value(value: Any) -> str:
    return str(value or "").strip().removeprefix("DDDA ")


def evaluate_physical_scope_binding(
    physical: Any,
    *,
    expected_source_sha: str,
    expected_version: str,
    declared_scope: list[int] | set[int] | tuple[int, ...],
) -> KernelDecision:
    """Evaluate normalized standard physical scope without recovery internals."""
    failures: list[str] = []
    if not isinstance(physical, dict):
        return KernelDecision(
            status="FAIL",
            operation="release_scope_validation",
            failure_codes=("PHYSICAL_SCOPE_EVIDENCE_MISSING",),
            authorization_required=False,
            side_effects_allowed=False,
        )

    if physical.get("release_source_sha") != expected_source_sha:
        failures.append("PHYSICAL_SCOPE_SOURCE_SHA_MISMATCH")
    if not str(physical.get("previous_release_tag") or "").strip():
        failures.append("PHYSICAL_SCOPE_PREVIOUS_TAG_MISSING")
    if not SHA40.fullmatch(str(physical.get("previous_release_sha") or "")):
        failures.append("PHYSICAL_SCOPE_PREVIOUS_TAG_SHA_INVALID")
    if physical.get("compare_status") not in {"ahead", "identical"}:
        failures.append("PHYSICAL_SCOPE_ANCESTRY_INVALID")

    try:
        scope = {int(value) for value in declared_scope}
    except (TypeError, ValueError):
        scope = set()
        failures.append("PHYSICAL_SCOPE_DECLARED_SCOPE_INVALID")
    for sha in sorted(
        {str(value) for value in physical.get("unmapped_commit_shas", []) if str(value)}
    ):
        failures.append(f"PHYSICAL_SCOPE_UNMAPPED_COMMIT:{sha}")

    shipping = physical.get("shipping_prs")
    if not isinstance(shipping, list):
        failures.append("PHYSICAL_SCOPE_SHIPPING_PR_EVIDENCE_MISSING")
        shipping = []
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
            failures.append("RECOVERY_DECISION_REQUIRED")
        if row.get("milestone") != f"DDDA {expected_version}":
            failures.append(f"PHYSICAL_SCOPE_MILESTONE_MISMATCH:PR#{number}:#{cr}")

    for cr in sorted(scope - shipping_crs):
        failures.append(f"PHYSICAL_SCOPE_DECLARED_CR_NOT_SHIPPED:#{cr}")

    normalized = sorted(set(failures))
    return KernelDecision(
        status="PASS" if not normalized else "FAIL",
        operation="release_scope_validation",
        failure_codes=tuple(normalized),
        authorization_required=False,
        side_effects_allowed=False,
    )


def evaluate_promotion_readiness(
    failure_codes: Any,
    *,
    operation: str = "release_scope_validation",
) -> KernelDecision:
    """Compose normalized release-domain failures into final technical readiness."""
    if not isinstance(failure_codes, (list, tuple, set)):
        normalized = ["PROMOTION_READINESS_EVIDENCE_INVALID"]
    else:
        normalized = sorted(
            {
                str(code).strip()
                for code in failure_codes
                if isinstance(code, str) and str(code).strip()
            }
        )
        if len(normalized) != len(failure_codes):
            normalized.append("PROMOTION_READINESS_EVIDENCE_INVALID")
            normalized = sorted(set(normalized))
    if operation not in {"release_scope_validation", "promotion_dry_run", "release"}:
        normalized.append("PROMOTION_READINESS_OPERATION_INVALID")
        normalized = sorted(set(normalized))
    return KernelDecision(
        status="PASS" if not normalized else "FAIL",
        operation=operation,
        failure_codes=tuple(normalized),
        authorization_required=operation == "release",
        side_effects_allowed=False,
    )


def evaluate_candidate_identity(context: dict[str, Any]) -> KernelDecision:
    """Evaluate normalized candidate identity before evidence restoration."""
    operation = str(context.get("operation") or "")
    failures = sorted(set(_candidate_identity_failures(context)))
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=operation in {"merge", "release"},
        side_effects_allowed=False,
    )


def evaluate_candidate_package_binding(context: dict[str, Any]) -> KernelDecision:
    """Evaluate normalized validation/package identity after physical collection."""
    operation = str(context.get("operation") or "validate")
    failures = sorted(set(_validation_failures(context)))
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=False,
        side_effects_allowed=False,
    )


def evaluate_human_review_binding(context: dict[str, Any]) -> KernelDecision:
    """Evaluate one normalized Human Review against exact candidate identity."""
    operation = str(context.get("operation") or "merge_dry_run")
    failures = sorted(set(_human_review_failures(context)))
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=False,
        side_effects_allowed=False,
    )


def evaluate_authoritative_checks(context: dict[str, Any]) -> KernelDecision:
    """Evaluate the singular exact-SHA mandatory-check contract."""
    operation = str(context.get("operation") or "merge_dry_run")
    failures = sorted(set(_check_failures(context)))
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=False,
        side_effects_allowed=False,
    )


def evaluate_hrdr_binding(context: dict[str, Any]) -> KernelDecision:
    """Evaluate one normalized HRDR against exact release-candidate identity."""
    operation = str(context.get("operation") or "promotion_dry_run")
    failures = sorted(set(_hrdr_failures(context)))
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=False,
        side_effects_allowed=False,
    )


def evaluate_candidate_context(context: dict[str, Any]) -> KernelDecision:
    """Evaluate normalized evidence without collecting it or authorizing effects."""
    operation = str(context.get("operation") or "")
    failures = _candidate_identity_failures(context)

    if operation in OPERATIONS:
        failures.extend(_validation_failures(context))
        failures.extend(_check_failures(context))

    if operation in MERGE_OPERATIONS:
        if context.get("pr_state") != "READY":
            failures.append("MERGE_OPERATION_REQUIRES_READY")
        if context.get("candidate_kind") != "NORMAL" or context.get("release_mode") != "STANDARD":
            failures.append("MERGE_OPERATION_REQUIRES_NORMAL_CANDIDATE")
        failures.extend(_human_review_failures(context))

    if operation in RELEASE_OPERATIONS:
        if context.get("pr_state") != "READY":
            failures.append("RELEASE_OPERATION_REQUIRES_READY")
        failures.extend(_hrdr_failures(context))
        failures.extend(
            _referenced_evidence_failure(
                context,
                "physical_scope_reference",
                "PHYSICAL_SCOPE_EVIDENCE_NOT_PASS",
            )
        )
        # Project is a governance/delivery projection, not release authority.
        # Its health cannot authorize or block release readiness.

    failures = sorted(set(failures))
    authorization_required = operation in {"merge", "release"}
    return KernelDecision(
        status="PASS" if not failures else "FAIL",
        operation=operation,
        failure_codes=tuple(failures),
        authorization_required=authorization_required,
        # The kernel establishes readiness only. An adapter must separately
        # prove explicit human authorization immediately before side effects.
        side_effects_allowed=False,
    )



RELEASE_CANDIDATE_MARKER = "<!-- ddda:release-candidate:v1 -->"


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _release_candidate_record(body: str) -> dict[str, Any] | None:
    """Parse exactly one versioned marker and its adjacent JSON fence."""
    if body.count(RELEASE_CANDIDATE_MARKER) != 1:
        return None
    tail = body.split(RELEASE_CANDIDATE_MARKER, 1)[1]
    match = re.match(r"\s*\x60\x60\x60json[ \t]*\r?\n([^\x60]*?)\r?\n\x60\x60\x60(?:\s|$)", tail)
    if not match:
        return None
    try:
        record = json.loads(match.group(1), object_pairs_hook=_unique_object_pairs)
    except (ValueError, TypeError):
        return None
    return record if isinstance(record, dict) else None


def evaluate_release_candidate_pr_identity(
    context: dict[str, Any], pr: dict[str, Any]
) -> KernelDecision:
    """The sole machine owner of release-candidate PR classification (#131).

    Collectors supply explicit intent and a fresh PR snapshot. No title-word
    heuristic can turn an implementation PR into a release candidate.
    """
    failures = _candidate_identity_failures(context)
    kind = context.get("candidate_kind")
    version = str(context.get("version") or "")
    if not STABLE_VERSION.fullmatch(version):
        failures.append("RELEASE_CANDIDATE_VERSION_INVALID")
    expected_title = (
        f"[RELEASE][{version}][RECOVERY] Controlled release candidate"
        if kind == "RECOVERY"
        else f"[RELEASE][{version}] Release candidate"
    )
    expected_branch = f"release/{version}"
    if kind == "NORMAL" and context.get("source_branch") != expected_branch:
        failures.append("RELEASE_CANDIDATE_BRANCH_INVALID")
    if context.get("pr_state") == "MERGED_CLOSED" or pr.get("state") != "open":
        failures.append("RELEASE_CANDIDATE_MUST_BE_OPEN")
    if pr.get("title") != expected_title:
        failures.append("RELEASE_CANDIDATE_TITLE_MISMATCH")
    if str(pr.get("number") or "") != str(context.get("pr") or ""):
        failures.append("RELEASE_CANDIDATE_PR_MISMATCH")
    head = _mapping(pr.get("head"))
    base = _mapping(pr.get("base"))
    if head.get("ref") != context.get("source_branch"):
        failures.append("RELEASE_CANDIDATE_BRANCH_MISMATCH")
    if head.get("sha") != context.get("source_sha"):
        failures.append("RELEASE_CANDIDATE_SHA_MISMATCH")
    if base.get("ref") != context.get("base_branch"):
        failures.append("RELEASE_CANDIDATE_BASE_MISMATCH")
    if _mapping(head.get("repo")).get("full_name") != context.get("repository"):
        failures.append("RELEASE_CANDIDATE_REPOSITORY_MISMATCH")

    raw_labels = pr.get("labels")
    labels = [
        row.get("name") if isinstance(row, dict) else row
        for row in raw_labels
    ] if isinstance(raw_labels, list) else []
    if len(labels) != len(set(str(label) for label in labels)):
        failures.append("RELEASE_CANDIDATE_LABEL_DUPLICATE")
    if "release-candidate" not in labels:
        failures.append("RELEASE_CANDIDATE_LABEL_MISSING")
    if (kind == "RECOVERY") != ("controlled-recovery" in labels):
        failures.append("RELEASE_CANDIDATE_RECOVERY_LABEL_MISMATCH")

    record = _release_candidate_record(str(pr.get("body") or ""))
    expected_kind = "controlled_recovery" if kind == "RECOVERY" else "normal"
    if record is None:
        failures.append("RELEASE_CANDIDATE_MARKER_INVALID")
    elif (
        set(record) != {"schema_version", "kind", "version"}
        or type(record.get("schema_version")) is not int
        or record.get("schema_version") != 1
        or record.get("kind") != expected_kind
        or record.get("version") != version
    ):
        failures.append("RELEASE_CANDIDATE_MARKER_MISMATCH")
    return KernelDecision(
        status="FAIL" if failures else "PASS",
        operation=str(context.get("operation") or "validate"),
        failure_codes=tuple(sorted(set(failures))),
        authorization_required=context.get("operation") == "release",
    )
