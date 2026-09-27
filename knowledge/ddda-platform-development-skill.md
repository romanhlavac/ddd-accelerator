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
- the ChatGPT Project Instructions / equivalent Work bootstrap instructions.

Registration is not optional. Keeping the file only in Git provides versioning, but does not guarantee that Chat or Work loads it. At the beginning of DDDA platform-development work, verify that the active runtime has loaded this skill and the developer lifecycle documentation referenced below.

Canonical supporting documentation:

- `docs/developer-guide/chat-work-operating-model.md`
- `docs/developer-guide/platform-development-lifecycle.md`
- `docs/developer-guide/testing-strategy.md`
- `docs/developer-guide/remote-validation-broker.md`
- `docs/user-guide/validate-and-promote-pr.md`
- `docs/adr/0001-platform-development-lifecycle.md`
- `docs/adr/0005-chat-work-only-development-operating-model.md`

If this skill and a supporting document conflict, fail closed and resolve the inconsistency in Git before relying on either rule.

### 1.1 Chat/Work-only execution policy

```text
DDDA-EXECUTION-MODE: CHAT-WORK-ONLY
```

Only these ChatGPT interfaces are supported for DDDA platform development:

```text
Chat
Work
```

These interfaces and modes are prohibited:

```text
Codex
legacy /agent mode
any other cloud coding agent without separate security approval
```

Responsibility boundary:

```text
Chat
  consultation, scope, design, authorization, evidence review and human decisions;
  when Work is unavailable, one exact-SHA-bound atomic Git tree commit through the approved GitHub connector.

Work
  preferred implementation mode; multi-step orchestration over approved GitHub, Miro and document Apps;
  bounded writes to an explicitly declared PR branch.

GitHub Actions
  authoritative execution plane for shell, build, tests, candidate packages,
  package-first validation and secret-bearing online acceptance.
```

Work is not a local developer workstation. It must not claim a local build or test unless the operation was actually executed by GitHub Actions or another explicitly approved execution plane.

Work must disclose connector, permission and visual-access limitations immediately. It must not silently substitute structural metadata for visual analysis or state that a reference board was reviewed when the relevant board/frame was not actually loaded.

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
14. Implementation merge, release promotion and tag creation are distinct governance side effects and each requires its own explicit human authorization when applicable.
15. Validation evidence must identify the exact commit SHA and candidate-package hash.
16. Chat and Work are the only supported ChatGPT interfaces for DDDA platform development.
17. Codex and `/agent` are prohibited by the active development policy.
18. Work writes only to an explicitly declared PR branch and only within authorized paths.
19. GitHub Actions is the authoritative execution plane for build and test evidence.
20. Secrets never enter Chat or Work context; secret-bearing operations stay in GitHub Actions or source-system secret stores.
21. A Work or Chat-atomic write must be followed by standard CI against the resulting exact SHA.
22. Chat direct multi-file Contents API writes are prohibited; Chat implementation must use one atomic Git tree commit with exact-base and fast-forward guards.
23. If a required connector or resource is unavailable, check for an approved alternative execution plane first. Stop and report a blocker only when the capability is mandatory and no approved alternative can fulfill it. Never claim a read-back or review that did not occur.
24. Structural Miro validation cannot satisfy human visual acceptance.
25. For every bounded DDDA platform-development assignment, unless the human explicitly requests analysis or planning only, Chat/Work owns mechanical execution and orchestration end to end through the next genuine human boundary. Autonomous-by-default applies to implementation, governance, validation, remediation, FAST-LOOP, release preparation and other bounded platform-development work inside authorized scope.
26. Chat/Work must not ask whether to perform a mechanically required or resolvable next step inside authorized scope: fresh read-back, branch/PR preparation, CI polling, log inspection, bounded diagnosis and correction, regression coverage, reruns, Project reconciliation, evidence materialization and continuation to READY FOR HUMAN REVIEW are orchestration responsibilities.
27. Request human interaction only for Human Review/HVR, legitimate architecture/product/methodology/risk choices, explicit merge or release/promotion/tag authorization, material scope expansion, an unavailable mandatory capability without an approved alternative, or unresolved authoritative ambiguity that changes meaning. Human judgment and authorization are never inferred from a technical PASS or an earlier gate.
28. A technical failure, quota or outage in one optional/local channel is not a human stop boundary. Inspect evidence, diagnose the cause, try an approved alternative plane, make a bounded corrective commit instead of rewriting shared history when justified, rerun exact-SHA validation, read back and continue. Escalate only for judgment, scope expansion or a mandatory capability without an approved alternative.
29. A governed implementation PR may be merged after exact-SHA technical evidence, Human Review and explicit merge authorization without evaluating release-scope completeness and without creating a release or tag.
30. HRDR and Release Scope Gate apply to the actual release candidate boundary, after included implementation work has been integrated/terminal; `promote-pr` is a release command, not the general implementation-PR merge command.
31. Merge, promotion, release and tag are never inferred from technical PASS, Human Review, FAST-LOOP completion or one another.
32. One exact-SHA validation decision uses one canonical candidate package identity: the package is built once, every validation consumer receives that physical artifact, and report, Human Review and merge preflight must agree on its recalculated SHA-256. A consumer must never rebuild the package to manufacture equivalent evidence.

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

DDDA separates implementation integration from release promotion.

### 5.1 Governed implementation PR

```text
change request in Chat or Work
→ impact analysis
→ feature/fix branch
→ Work implementation through approved Apps (preferred) or Chat-atomic implementation when Work is unavailable
→ one scoped commit
→ GitHub Actions exact-SHA validation
→ push/PR CI
→ validate-pr
→ Human Review for the same exact SHA/candidate package
→ merge-pr dry-run
→ explicit human merge authorization
→ governed merge into main
→ NO release package
→ NO release validation
→ NO tag
```

The Human Review and merge authorization are distinct boundaries. A technical PASS cannot create either one. `merge-pr` must not require HRDR or Release Scope Gate and must not call release/tag execution paths.

### 5.2 Release candidate

After all work intended for a release has been integrated and the release-scope Issues are terminal or explicitly deferred outside the release:

```text
release candidate preparation (typically release/<version> PR or equivalent governed candidate)
→ exact-SHA candidate validation
→ release cut / changelog consistency
→ Human Release Decision Record for the exact release candidate
→ Release Scope Gate
→ promotion dry-run
→ explicit Human Release Decision
→ separate explicit release/promotion authorization
→ canonical promotion
→ release-candidate merge when applicable
→ release package
→ generated release-validation workspace
→ ingestion
→ smoke + acceptance
→ release report
→ tag
→ GitHub Release publication of the validated canonical package and portable release evidence
```

Release Scope Gate stays strict: incomplete current-release scope is a release failure. It is not evaluated as a prerequisite for merging the individual implementation PRs whose integration is required to make that scope terminal.

Never recommend an implementation merge or release when its mandatory technical or human gate is not satisfied.

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

A “remediation test” is not a separate test type. The correct term is **remediation validation run**: an orchestration that composes existing tests and guards.

Tests that mutate repository state must run in an isolated clone, worktree or fixture. Do not assert that the developer working tree is clean while intentionally using it as the mutable test subject.

On the Chat/Work-only path, commands are executed by standard GitHub Actions workflows. Documentation may show local PowerShell commands as the stable platform contract, but Work must not pretend it executed those commands locally.

## 7.1 Chat atomic implementation fallback

Work remains the preferred implementation mode. When Work is unavailable, Chat may write the platform PR branch only by constructing one complete Git tree from an exact-SHA source snapshot, creating one commit whose parent is the authorized SHA, and moving the same PR branch by a non-force fast-forward update.

Required controls:

- exact PR head SHA captured before preparation;
- immutable source snapshot matching that SHA;
- declared paths and reviewable full-file content;
- one atomic commit, never sequential multi-file Contents API commits;
- no `main` write and no force update;
- standard PR CI on the resulting exact SHA;
- corrective commit or revert after failure, never automatic history rewrite;
- no secrets or secret-bearing operations in Chat.

A control-plane bootstrap requires explicit human authorization and a self-removing staging artefact.

## 8. Stable command flow

Prefer the stable entry point:

```powershell
.\ddda.ps1 doctor
.\ddda.ps1 test -Suite <suite>
.\ddda.ps1 validate-pr -Pr <PR_NUMBER>
.\ddda.ps1 merge-pr -Pr <PR_NUMBER> -DryRun
.\ddda.ps1 review-pr -Pr <RELEASE_PR_NUMBER> -Version <VERSION> ...
.\ddda.ps1 promote-pr -Pr <RELEASE_PR_NUMBER> -Version <VERSION> -DryRun
```

Actual implementation merge requires explicit `merge-pr ... -ConfirmMerge` authorization. It performs merge only.

Actual release promotion requires its own explicit authorization and all release-candidate HRDR/Release Scope Gate evidence for the same SHA. A prior implementation merge authorization never implies release or tag authorization.

In Chat/Work-only operation, standard GitHub Actions workflows invoke these contracts. One-off bootstrap workflows are not a normal implementation mechanism and must not be introduced when an existing self-service workflow can be extended.

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
   return to normal PR CI, review, acceptance and the appropriate governed merge/release boundary.
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

For Miro visual review, Work must actually load the relevant reference and target frames. Human review covers images, font size, geometry, hierarchy, overlap, information density, first-viewer usability and fidelity to the approved redline/template.

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
- connector/access limitations were disclosed;
- no prohibited execution interface was used;
- implementation merge was not performed without explicit merge authorization;
- release promotion/tag was not performed without its separate explicit authorization.

## 15. Runtime registration rule

Repository versioning and runtime activation are separate controls.

For every ChatGPT project, Chat or Work runtime used to change DDDA:

1. register this skill in the knowledge index or Project/Work instructions as **mandatory for DDDA platform development**;
2. ensure the runtime can read the current repository version;
3. load it before proposing or applying platform changes;
4. record the skill path/version or source SHA in substantial implementation evidence when practical;
5. treat a missing or stale registration as a governance defect and stop before high-impact changes;
6. verify that `config/platform/development-policy.yaml` allows only `chat` and `work` and forbids `codex` and `agent`.

Target operating principle:

```text
Chat for understanding and decisions.
Work for approved multi-step orchestration.
GitHub Actions for authoritative execution.
Secrets stay outside Chat and Work.
Automated first.
Manual only for judgment.
Autonomous by default inside bounded authorized scope.
The human is a decision/authorization boundary, not the workflow engine.
Technical failure triggers autonomous diagnosis and bounded remediation.
PR is the unit of change.
Remediation is controlled transport, not approval.
Release package is the unit of distribution.
Example workspace proves usability.
Exact-SHA evidence proves what was validated.
```

## 16. Autonomous-by-default platform-development orchestration and truthful execution state

For every bounded DDDA platform-development assignment, unless the human explicitly requested analysis or planning only, autonomous orchestration is the default inside the authorized scope. This covers standard implementation, governance and backlog work, validation, remediation, FAST-LOOP and release preparation. The human is a decision/authorization boundary, not the workflow engine.

Normal mechanical flow:

```text
fresh authoritative read-back
→ exact-SHA skill/policy preflight
→ branch / PR / governance preparation
→ implementation
→ exact-SHA CI and package-first validation
→ failure/evidence inspection and bounded correction when justified
→ rerun and reconciliation
→ fresh server-side read-back
→ READY FOR HUMAN REVIEW or the next genuine human boundary
```

Work does not ask the human to schedule a workflow, poll CI, read logs, run tests, fix a scoped technical failure, create a corrective commit, rerun validation, perform fresh read-back, reconcile Project state or trigger routine continuation. These are mechanical orchestration responsibilities.

**TECHNICAL FAILURE != HUMAN STOP BOUNDARY.** On failure, inspect authoritative evidence, find the root cause, make a bounded correction with regression coverage and a corrective commit when justified, rerun exact-SHA validation, read back and continue. Try an approved alternative execution plane when an optional channel fails; Miro MCP quota does not stop an approved REST/GitHub-Actions path. Never claim an unavailable review or read-back occurred. The normal implementation stop point is READY FOR HUMAN REVIEW, or another explicit lifecycle human boundary, not the first CI/test failure.

Avoid endless narrow patching: after the first defect in a capability, use bounded remediation; after a second related defect, review root cause and scenario/contract; at a third related remediation signal, stop narrow patching and assess simplification or redesign. Continue autonomously if one design follows mechanically from current authority. Ask the human when legitimate architecture or risk alternatives require judgment. This heuristic is not a new CI gate.

Genuine human boundaries are Human Review/HVR; architecture, product, methodology or risk judgment; explicit merge authorization; separate release/promotion/tag authorization; material scope expansion; an unavailable mandatory capability without an approved alternate; and unresolved semantic authority conflict. Technical PASS cannot imply Human Review PASS; Human Review cannot imply merge authorization; merge cannot imply release; release cannot imply tag; FAST-LOOP cannot authorize irreversible side effects. Keep exact-SHA and single canonical candidate-package identity across evidence and gates.

### 16.1 Truthful execution-state reporting

Chat/Work must distinguish an **active external execution** from an **intention to continue**.

- It may say that work is running only when a real workflow, automation or connector operation has actually been started and is still running; identify the concrete execution or evidence when practical.
- It must not say or imply “I am continuing”, “I am working on it in the background”, “I will return when it is ready”, or equivalent after sending a response if no real external execution will continue without another user turn.
- If the current Chat turn must end while work remains and no external execution continues autonomously, state the exact checkpoint and provide one ready-to-copy continuation prompt. That prompt must preserve the repository, branch/SHA or checkpoint, remaining FAST-LOOP steps, governance guardrails and the rule that the human is contacted only at a genuine human boundary or hard blocker.
- If an external workflow is still running when the response is sent, say exactly that; do not represent future analysis, fixes or retries as already running unless they are actually scheduled or executing.

The intent is operationally strict: **autonomous orchestration while execution is active, truthful stop-state reporting when it is not.**

## Backlog / Project transactional completion

Pro DDDA platform backlog/delivery governance je GitHub Issue/PR mutation a její `DDDA Platform Backlog & Delivery` projection jedna fail-closed transakce. CR/Defect/Enabler/PR creation, state/relationship change nebo implementation authority change není `Ready`/`Done`/governance `PASS`, dokud canonical Project/Milestone reconciliation a repository-wide read-back nevrátí `remaining_mismatches = 0`. Nedostupná Project mutation surface je blocker k dokončení governance transakce, ne důvod projekci odložit nebo ji přenést na člověka k ruční kontrole.
