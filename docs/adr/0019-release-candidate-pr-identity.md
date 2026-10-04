# ADR 0019: Release candidate PR identity

Status: Proposed for #131 Human Review

Date: 2026-10-04

## Context

Implementation PRs can change release code while a real release-candidate PR is a separate governed release source. Historical `fix(release):` titles and controlled recovery PRs have no single, unambiguous machine and human identity. #65 owns branch lifecycle and S1/#171 owns Candidate Context and the Governance Kernel.

## Decision

A new candidate carries one versioned body record plus an exact title, branch and labels. The pure S1 Governance Kernel evaluates the four surfaces and exact PR/SHA binding together; collectors only provide a fresh PR snapshot and explicit operation kind. Normal and controlled recovery have distinct titles and labels. Recovery keeps the compatible generation suffix. The machine record uses `<!-- ddda:release-candidate:v1 -->` with a JSON object containing exactly `schema_version`, `kind` and `version`.

New candidate entry points check this identity before HRDR scaffolding or promotion. A missing, duplicated or contradictory surface fails closed. The generic implementation PR lifecycle and #65 branch taxonomy are unchanged. Historical PRs and release evidence are preserved; running a new release operation on legacy metadata requires a separate reviewed compatibility decision or a conforming new candidate.

## Options considered

- Title or branch heuristics: rejected because an implementation PR can match release words and branch names may have compatibility exceptions.
- New standalone classifier in each workflow: rejected because it would duplicate S1 decision ownership.
- One S1 Kernel identity decision consumed by adapters: selected; it centralizes fail-closed semantics and supports exact-SHA regression tests.

## Consequences and validation

The PR creation runbook must emit all four surfaces together. Pre-existing controlled candidate PRs are not silently renamed. Kernel unit, adapter and release entry tests prove normal/recovery acceptance, disagreements, duplicate marker/JSON key rejection and the `fix(release)` regression. Technical PASS grants no Human Release Decision or publication authorization.

See [identity v1](../governance/release-candidate-identity.md) for the exact human-facing contract.
