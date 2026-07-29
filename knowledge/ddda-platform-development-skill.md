---
name: ddda-platform-development
description: Mandatory operating instructions for development of the versioned DDDA platform itself, including methodology, architecture, CLI, orchestration, schemas, testing, Git/PR lifecycle, remediation, packaging and release governance.
---

# DDDA Platform Development Skill

## 1. Activation and authority

Use this skill for every task that changes or evaluates the DDDA platform itself. It does not apply to execution of a client DDDA workspace.

This repository file is the canonical versioned source of the skill:

```text
knowledge/ddda-platform-development-skill.md
```

For ChatGPT/project execution, the skill must also be registered as mandatory in at least one runtime routing surface:

- `knowledge/00-knowledge-index.md`, or
- the ChatGPT Project Instructions / equivalent agent bootstrap instructions.

Registration is not optional. Keeping the file only in Git provides versioning, but does not guarantee that a chat or agent loads it. At the beginning of DDDA platform-development work, verify that the active runtime has loaded this skill and the developer lifecycle documentation referenced below.

Canonical supporting documentation:

- `docs/developer-guide/platform-development-lifecycle.md`
- `docs/developer-guide/testing-strategy.md`
- `docs/user-guide/validate-and-promote-pr.md`
- `docs/adr/0001-platform-development-lifecycle.md`

If this skill and a supporting document conflict, fail closed and resolve the inconsistency in Git before relying on either rule.

## 2. Product boundary

Always distinguish:

```text
DDDA platform
  Versioned product/framework source.

DDDA workspace
  Generated instance for a concrete project, example or validation run.

Example workspace
  Generated fixture proving that a package works end to end.

Client workspace
  Real project data. Never use it as a platform-development test fixture.

Candidate package
  Immutable package built from a specific commit SHA for validation.

Release package
  Official distributable artifact after release validation.

PR
  Unit of platform change.

CI/test pipeline
  Technical enforcement mechanism for platform quality.
```

## 3. Non-negotiable rules

1. Git is the source of truth.
2. PR is the unit of change; do not change `main` directly.
3. Every behavioral platform change must be testable.
4. Every contract change requires documentation and an explicit compatibility decision.
5. Significant long-term decisions require an ADR.
6. Breaking changes require migration notes and migration tests.
7. Candidate and release packages must be generated from versioned source state.
8. Package-dependent validation must run from a freshly unpacked package.
9. Example workspaces are generated; they are not manually copied from a developer tree.
10. Ingestion is manifest-driven.
11. Mechanical checks are automated; humans decide only judgment-heavy questions.
12. Client data, credentials and user-specific absolute paths are forbidden in examples and packages.
13. Chat output is advisory; technical guarantees live in Git, CI, schemas, scripts and tests.
14. Merge, tag, release and promotion require a separate explicit governance action.
15. Validation evidence must identify the exact commit SHA and candidate-package hash.

## 4. Change classification

Classify each platform change before implementation:

```text
DOC
METHODOLOGY
TEMPLATE
SCHEMA
ORCHESTRATION
INGESTION
CLI
WORKSPACE-GENERATOR
EXAMPLE
TESTING
RELEASE
SECURITY-GOVERNANCE
```

Impact:

```text
LOW       documentation or non-behavioral local change
MEDIUM    non-breaking user-facing behavior, templates or commands
HIGH      contracts, gates, workspace layout, orchestration or release behavior
BREAKING  existing workspaces or artifacts require migration
```

The classification determines tests, ADR, migration and review obligations.

## 5. Standard lifecycle

```text
change request
→ impact analysis
→ feature/fix branch
→ implementation
→ precommit validation
→ commit
→ exact-SHA validation
→ push
→ PR CI
→ validate-pr
→ human review
→ promotion dry-run
→ explicit promotion decision
→ merge
→ release package
→ generated release-validation workspace
→ ingestion
→ smoke + acceptance
→ release report
→ tag
```

Never recommend merge when a mandatory technical or human gate is not satisfied.

## 6. Required PR content

Depending on scope, a complete PR includes:

- implementation;
- relevant tests;
- documentation;
- examples and expected invariants;
- schemas when contracts change;
- changelog;
- ADR when required;
- migration note when compatibility changes;
- exact-SHA validation evidence;
- remediation manifest/evidence when remediation transport was used.

A behavioral change without a test or explicit test rationale is incomplete.

## 7. Test model

Use the existing DDDA test taxonomy, not ad hoc names:

- lint;
- schema;
- unit;
- component;
- integration;
- smoke;
- regression;
- acceptance;
- end-to-end;
- migration;
- security/isolation.

A “remediation test” is not a separate test type. The correct term is **remediation validation run**: an orchestration that composes existing guards and suites.

Tests that mutate repository state must run in an isolated clone, worktree or fixture. Do not assert that the developer working tree is clean while intentionally using it as the mutable test subject.

## 8. Stable command flow

Prefer the stable entry point:

```powershell
.\ddda.ps1 doctor
.\ddda.ps1 test -Suite <suite>
.\ddda.ps1 validate-pr -Pr <PR_NUMBER>
.\ddda.ps1 promote-pr -Pr <PR_NUMBER> -Version <VERSION> -DryRun
```

A real merge/promotion requires explicit confirmation and all required evidence for the same SHA.

## 9. Remediation terminology

```text
Remediation package
  Deterministic, manifest-driven bundle of source changes for a specific issue or review finding.

Remediation orchestrator
  Script/CLI that verifies preconditions, applies the package transactionally, validates it, commits only after PASS, validates the exact commit and optionally pushes it.

Remediation validation run
  One evidence-producing execution of the orchestrator. It composes existing tests and guards.

Remediation evidence
  Machine-readable result plus human-readable logs proving what was applied and validated.
```

A remediation package is controlled implementation transport. It never replaces a reviewable Git diff, PR, approval or release decision.

## 10. Remediation package contract

Minimum manifest fields:

```json
{
  "schema_version": 1,
  "change_id": "issue-14-example",
  "repository": "romanhlavac/ddd-accelerator",
  "target_branch": "feat/example",
  "base_sha": "<40-character SHA>",
  "change_type": "FIX",
  "impact": "HIGH",
  "expected_paths": [],
  "files": [
    {"path": "path/to/file", "sha256": "<SHA-256>"}
  ],
  "payload_sha256": "<SHA-256>",
  "commit": {"message": "fix: scoped remediation"}
}
```

Required rules:

- immutable `base_sha` and explicit target branch;
- clean working tree before application;
- allowlisted relative paths only;
- no path traversal, symlinks outside the repository, secrets or client data;
- SHA-256 for every file and the entire package;
- complete reviewable source files or a formally defined patch format;
- declarative commit metadata cannot authorize merge, tag, release or promotion;
- embedded Base64 payload may be a transport fallback, but must not be the only review surface.

## 11. Transactional remediation lifecycle

```text
1. Preflight
   verify runtime, repository, branch, exact base SHA and clean tree.

2. Integrity
   validate manifest, hashes, allowlist and expected change count.

3. Application
   apply only declared files; reject any unexpected path.

4. Precommit validation
   run the required change-class test matrix and diff checks.

5. Commit
   create one scoped local commit only after PASS.

6. Exact-SHA validation
   rebuild candidate package and rerun required suites from the committed SHA.

7. Push
   push only the validated SHA; never force-push automatically.

8. Handoff
   return to normal PR CI, review, acceptance and promotion.
```

Rollback requirements:

- before commit: restore original HEAD and working tree on failure;
- after commit but before push: follow explicit recovery policy and preserve diagnostics;
- after push: do not rewrite shared history automatically; use corrective commit or revert;
- `result.json` and logs survive rollback;
- external-resource cleanup/preservation is explicit and recorded.

A successful application followed by a failed test is an overall failure.

## 12. Remediation states and evidence

Recommended terminal states:

```text
PRECONDITION_FAILED
PAYLOAD_INVALID
APPLICATION_FAILED_ROLLED_BACK
VALIDATION_FAILED_ROLLED_BACK
VALIDATED_UNCOMMITTED
COMMITTED_VALIDATION_FAILED
COMMITTED_EXACT_SHA_VALIDATED
PUSH_FAILED
PUSHED
```

Separate technical and human dimensions:

```text
technical_status: PASS | FAIL
human_review_status: NOT_REQUIRED | PENDING | ACCEPTED | REJECTED
overall_status: PASS | FAIL | PENDING_HUMAN_REVIEW
```

Minimum `result.json` must include:

- schema/run/change identity;
- repository and branch;
- base SHA and validated SHA;
- payload hash;
- expected and observed paths;
- step status, exit code and log reference;
- candidate-package reference and hash;
- cleanup state;
- timestamps;
- technical, human and overall status.

CI evidence should be uploaded as workflow artifacts. Local evidence is not automatically available in GitHub and must not be represented as if it were.

## 13. Human versus automated responsibility

Automation verifies syntax, schemas, paths, package contents, generated structures, command behavior, isolation and deterministic acceptance mechanics.

Humans judge methodology, architecture, domain boundaries, gate semantics, visual usability, risk acceptance and release readiness.

Automation must never create a production human decision such as `passed` merely because technical tests passed.

## 14. Definition of Done

A platform change is done only when:

- scope and classification are explicit;
- implementation, tests and docs form one coherent change package;
- required suites and CI pass;
- exact-SHA `validate-pr` evidence exists;
- package-first validation passes;
- example workspace and acceptance are valid where required;
- changelog, ADR and migration note obligations are satisfied;
- no client data, secret or path leakage exists;
- mandatory human review is complete;
- merge/promotion was not performed without explicit authorization.

## 15. Runtime registration rule

Repository versioning and runtime activation are separate controls.

For every ChatGPT project, custom GPT, agent runtime or comparable development environment used to change DDDA:

1. register this skill in the knowledge index or project/agent instructions as **mandatory for DDDA platform development**;
2. ensure the runtime can read the current repository version;
3. load it before proposing or applying platform changes;
4. record the skill path/version or source SHA in substantial implementation evidence when practical;
5. treat a missing or stale registration as a governance defect and stop before high-impact changes.

Target operating principle:

```text
Automated first.
Manual only for judgment.
PR is the unit of change.
Remediation is controlled transport, not approval.
Release package is the unit of distribution.
Example workspace proves usability.
Exact-SHA evidence proves what was validated.
```
