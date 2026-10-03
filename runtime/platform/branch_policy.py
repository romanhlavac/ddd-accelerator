"""Prospective DDDA branch taxonomy and conservative automation cleanup decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence


_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_IMPLEMENTATION = re.compile(rf"^(feature|fix|docs)/([1-9][0-9]*)-({_SLUG})$")
_RELEASE = re.compile(r"^release/[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
_AUTOMATION = re.compile(rf"^automation/({_SLUG})-([1-9][0-9]*)$")
LEGACY_PREFIXES = frozenset({"feat", "chore", "gov", "governance", "agent"})
PROVENANCE_PATH = ".ddda/automation-provenance.json"
STAGING_PREFIX = ".ddda/automation-staging/"


@dataclass(frozen=True)
class BranchDecision:
    classification: str
    allowed_implementation_pr: bool
    reason: str


def parse_automation_name(name: str) -> tuple[str, int] | None:
    match = _AUTOMATION.fullmatch(name)
    return (match.group(1), int(match.group(2))) if match else None


def evaluate_branch(
    name: str,
    *,
    head_sha: str,
    pr_number: int | None,
    policy: Mapping[str, object],
) -> BranchDecision:
    """Only a versioned exact-head active-PR exception can admit legacy work."""
    if policy.get("schema_version") != 1:
        return BranchDecision("INVALID", False, "Unknown branch-policy version")
    if name == "main" and pr_number is None:
        return BranchDecision("INTEGRATION", True, "Protected default branch push")
    exceptions = policy.get("legacy_exceptions", [])
    if not isinstance(exceptions, list):
        return BranchDecision("INVALID", False, "Malformed exception registry")
    for exception in exceptions:
        if not isinstance(exception, dict) or exception.get("branch") != name:
            continue
        if (
            pr_number is not None
            and exception.get("pr") == pr_number
            and exception.get("head_sha") == head_sha
            and exception.get("expiry") == "PR_TERMINAL_OR_HEAD_CHANGE"
            and exception.get("reason")
        ):
            return BranchDecision("LEGACY_COMPATIBILITY", True, "Versioned exact-head PR exception")
        return BranchDecision("INVALID", False, "Legacy exception does not bind this PR and SHA")
    if _IMPLEMENTATION.fullmatch(name) or _RELEASE.fullmatch(name):
        return BranchDecision("PERSISTENT_IMPLEMENTATION", True, "Canonical prospective branch")
    if parse_automation_name(name) is not None:
        return BranchDecision("EPHEMERAL_AUTOMATION", False, "Automation cannot host an implementation PR")
    prefix = name.split("/", 1)[0]
    if prefix in LEGACY_PREFIXES:
        return BranchDecision("INVALID", False, "Legacy prefix forbidden for new work")
    return BranchDecision("INVALID", False, "Unknown or malformed branch name")


def evaluate_automation_cleanup(
    name: str,
    *,
    head_sha: str,
    provenance: Mapping[str, object] | None,
    open_pr_numbers: Sequence[int],
    changed_paths: Sequence[str],
    source_ancestor: bool,
    run_id: int | None,
    run_terminal: bool,
    same_owner_run: bool,
    referenced_by_release_or_audit: bool,
) -> BranchDecision:
    """Return SAFE_TO_DELETE only after every independent proof is affirmative."""
    identity = parse_automation_name(name)
    if identity is None:
        return BranchDecision("AMBIGUOUS", False, "Not a canonical automation branch")
    if not provenance or provenance.get("schema_version") != 1:
        return BranchDecision("AMBIGUOUS", False, "Missing versioned provenance")
    purpose, branch_run_id = identity
    if (
        provenance.get("kind") != "ddda_automation_branch"
        or provenance.get("branch") != name
        or provenance.get("purpose") != purpose
        or provenance.get("run_id") != branch_run_id
        or not re.fullmatch(r"[0-9a-f]{40}", str(provenance.get("source_sha", "")))
        or not provenance.get("owner")
    ):
        return BranchDecision("AMBIGUOUS", False, "Provenance identity mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        return BranchDecision("AMBIGUOUS", False, "Invalid observed HEAD identity")
    if open_pr_numbers or referenced_by_release_or_audit:
        return BranchDecision("ACTIVE", False, "Open PR or release/audit reference")
    if not source_ancestor or not changed_paths or any(
        path != PROVENANCE_PATH and not path.startswith(STAGING_PREFIX)
        for path in changed_paths
    ):
        return BranchDecision("AMBIGUOUS", False, "Unverified unique commit or unexpected path")
    if run_id != branch_run_id or (not run_terminal and not same_owner_run):
        return BranchDecision("ACTIVE", False, "Owning workflow may still be active")
    return BranchDecision("SAFE_TO_DELETE", False, "Exact owner/run, isolated paths and no references")
