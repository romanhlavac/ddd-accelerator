# ADR 0012: Candidate Context v1 and pure Governance Kernel

Status: Accepted for staged activation by #171

Date: 2026-09-28

## Context

Release and governance entry points currently repeat candidate classification,
exact-SHA/package binding and readiness decisions across Python, PowerShell and
workflow YAML. The characterization gate from #174 records existing outcomes,
but consolidation requires one versioned input contract and one deterministic
decision component before adapters can be migrated safely.

## Decision

DDDA introduces:

- `schemas/candidate-context.schema.json` as Candidate Context v1;
- `runtime/platform/governance_kernel.py` as the pure decision component;
- `scripts/platform/Evaluate-DDDAGovernanceContext.py` as a side-effect-free
  process adapter for non-Python consumers.

Collectors remain responsible for fresh GitHub, package, physical-scope and
Project evidence. They emit normalized context and provenance references. The
kernel validates semantic identity and operation readiness only. It performs
no network/filesystem collection and no mutation.

Technical readiness never implies Human Review, merge, promotion, release or
tag authorization. Consequently kernel decisions always return
`side_effects_allowed=false`; an execution adapter must separately prove the
explicit authorization required by the requested side effect.

## Staged activation and compatibility

This first #171 slice introduces an inactive foundation. Existing production
entry points remain authoritative until a bounded migration replaces their
local decision code with Candidate Context collection plus kernel evaluation.
Each migration must prove parity against the #174 scenario matrix. The old
decision copy is removed in the same slice that activates its replacement, so
no two active semantic authorities remain.

The first activation slice routes controlled release-candidate kind, version,
branch generation and Draft/Ready selection semantics through the kernel.
The next activation slice routes validation-report repository/PR/SHA identity
and declared-versus-observed candidate-package binding through the same kernel.
GitHub response-shape collection, package presence and physical SHA-256
calculation remain adapter responsibilities; they are evidence acquisition,
not alternative decisions. Legacy reports without artifact/run metadata are
normalized by the compatibility adapter without rewriting historical evidence.

The shared `runtime/platform/candidate_evidence.py` collector and
`Restore-DDDACandidateEvidence.py` process adapter define the reusable restore
contract. They enforce report/package cardinality, calculate physical hashes
and submit normalized binding evidence to the kernel. Workflow migrations may
therefore remove copied report/package decision blocks without moving file or
network access into the kernel.

Controlled promotion and controlled release recovery are the first workflow
consumers of this restore adapter. They retain GitHub artifact download and
explicit human-authorization comparison, while report/package cardinality,
source binding and physical package verification are no longer reimplemented
in workflow YAML.

Controlled validation's HRDR-scaffold and release-scope/promotion dry-run
consumers use the same restore adapter. Canonical candidate filename identity
is enforced in the shared collector so the YAML migration preserves the
existing fail-closed artifact contract.

The governed merge, human-review scaffold and governed promotion entry points
also submit explicit or locally discovered report/package pairs through that
process adapter. PowerShell remains responsible for state-directory discovery
and consumer-specific return shaping, but no longer decides report source
identity, canonical package identity or declared-versus-observed hash binding.
The canonical release executor reuses that same resolver at its execution
boundary, preserving defense-in-depth revalidation without reintroducing a
second semantic implementation.

Implementation Human Review now follows the same ownership rule. The shared
`runtime/platform/human_review_evidence.py` collector owns authoritative marker
cardinality, fenced-record parsing and human GitHub provenance normalization.
`Evaluate-DDDAHumanPrReview.py` is the process adapter for PowerShell. Governed
merge submits the normalized reference plus the exact source/package identity
to the Governance Kernel and no longer reimplements review contract, verdict,
SHA, package or reviewer/author binding decisions.

Human Release Decision Records use the same boundary. The shared
`runtime/platform/hrdr_evidence.py` collector owns authoritative marker
cardinality, fenced-record parsing and human GitHub provenance normalization.
`Evaluate-DDDAHrdr.py` is the PowerShell process adapter. Governed promotion
submits the exact source/package/version identity to the Governance Kernel and
no longer reimplements HRDR parsing, positive-decision, identity or
decision-owner/author binding decisions. Pending automation scaffolds remain
readable but cannot satisfy a promotion decision.

Mandatory GitHub checks are normalized through
`runtime/platform/check_evidence.py` and the
`Evaluate-DDDACheckRuns.py` process adapter. That adapter is the single owner
of pagination, latest-run selection and Check Run/legacy Commit Status
normalization. Operation adapters declare only their required names and
accepted conclusions; the Governance Kernel evaluates presence and terminal
outcomes. Governed merge preserves its characterized acceptance of success,
neutral and skipped latest results, while secret-bearing workflows explicitly
require success for their named checks.

Standard physical release scope now follows the same authority boundary. Git
and GitHub collectors still inventory the previous release tag, exact source,
shipping commits and PR-to-primary-CR mappings. The Governance Kernel alone
evaluates ancestry, unmapped commits and equality between declared and
physical CR scope. Historical controlled-recovery ledger validation remains a
separate compatibility adapter for the subsequent #172 isolation slice.

Candidate Context v1 does not rewrite historical 0.1.1 evidence. Legacy
controlled-recovery evidence remains readable through its existing adapter;
the later #172 slice will isolate that adapter behind explicit
`candidate_kind=RECOVERY` and `release_mode=CONTROLLED_RECOVERY`.

## Consequences

- Normal and recovery mode cannot be inferred independently after migration.
- Exact source SHA, package identity, checks and human-decision references have
  one normalized transport shape.
- Cross-field identity remains kernel logic; JSON Schema owns structural
  validity and rejects unversioned extensions.
- S1 migration PRs can be small and parity-tested without changing the
  collection or execution planes simultaneously.
- #173 may refine Project evidence categories without making Project a second
  release authority.
