"""Pure Candidate Context v1 governance decisions.

Collectors normalize live evidence into Candidate Context.  This module does
not read files, call GitHub, mutate Project state, or execute side effects.
Human authorization remains an adapter responsibility and is never inferred
from a technical PASS.
"""

from __future__ import annotations

from dataclasses import dataclass
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


def _check_failures(context: dict[str, Any]) -> list[str]:
    checks = _mapping(context.get("authoritative_check_summary"))
    if not checks:
        return ["AUTHORITATIVE_CHECK_SUMMARY_MISSING"]
    if checks.get("status") != "PASS":
        return ["AUTHORITATIVE_CHECKS_NOT_PASS"]
    required = checks.get("required_checks")
    results = checks.get("latest_results")
    if not isinstance(required, list) or not required:
        return ["AUTHORITATIVE_REQUIRED_CHECKS_MISSING"]
    if not isinstance(results, list):
        return ["AUTHORITATIVE_CHECK_RESULTS_MISSING"]
    latest = {
        str(row.get("name")): row
        for row in results
        if isinstance(row, dict) and str(row.get("name") or "")
    }
    failures: list[str] = []
    for name in required:
        row = latest.get(str(name))
        if not row:
            failures.append(f"AUTHORITATIVE_CHECK_MISSING:{name}")
        elif row.get("status") != "COMPLETED" or row.get("conclusion") != "SUCCESS":
            failures.append(f"AUTHORITATIVE_CHECK_NOT_SUCCESS:{name}")
    return failures


def _human_review_failures(context: dict[str, Any]) -> list[str]:
    review = _mapping(context.get("human_review_reference"))
    if not review:
        return ["HUMAN_REVIEW_REQUIRED"]
    failures: list[str] = []
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
        failures.extend(
            _referenced_evidence_failure(
                context,
                "project_evidence_reference",
                "PROJECT_EVIDENCE_NOT_PASS",
            )
        )

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
