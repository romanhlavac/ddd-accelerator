# Governance characterization v1

Status: S4-A characterization baseline for #174. This document and
`tests/fixtures/governance/scenario-matrix-v1.json` describe current behavior
before S1-S3 move authority. They do not authorize merge or release and they
are not a second governance evaluator.

## How to use the matrix

The fixture declares every required scenario axis and an explicit `PASS` or
`FAIL` outcome with expected failure codes. Python parametrized tests arrange
evidence and invoke the current production evaluators. The PowerShell
component test consumes the same fixture for GitHub Actions pagination/latest
run selection and Human Review marker behavior.

When a consumer migrates to Candidate Context and the shared Governance
Kernel, change its expected outcome only in the same bounded PR that proves
parity or intentionally records the new authority rule. A scenario is not an
implementation shortcut: collectors still collect fresh evidence and the
production evaluator remains the only decision owner.

## Semantic-owner refactoring inventory

`Candidate Context v1` and `Governance Kernel v1` below are intended S1
targets, not yet-active authorities. This baseline intentionally changes no
production authority.

| Semantic invariant | Current production implementations | Intended authoritative owner | Duplicate implementation or coupling | Migration target |
|---|---|---|---|---|
| Release candidate identity | `scripts/platform/Test-DDDAControlledReleaseCandidate.py`; `scripts/platform/Invoke-DDDAGovernedMergePr.ps1`; `scripts/platform/Invoke-DDDAGovernedPromotePr.ps1`; controlled candidate workflows | Candidate Context v1 identity plus Governance Kernel v1 decision | PR/repository/state identity is rechecked in Python, PowerShell and YAML orchestration | One fresh collector emits context; merge/release adapters submit it unchanged to the kernel |
| Branch semantics | `Test-DDDAControlledReleaseCandidate.py`; controlled candidate workflow guards; `Invoke-DDDAReleaseRecovery.ps1` branch construction | Governance Kernel v1 candidate classification | Recovery branch pattern and generation meaning appear in selection, workflow and recovery construction | Kernel classifies a collected branch; recovery playbook alone constructs emergency branches |
| Candidate kind and version | controlled candidate marker/branch parser; promotion/recovery switches; workflow operation branches | Candidate Context v1 fields `candidate_kind`, `version`, `release_mode` validated by Governance Kernel v1 | Kind/version are inferred independently from branch, flags and workflow selection | Collector supplies provenance-bound kind/version once; adapters must not reclassify |
| Exact source SHA | candidate validator; governed merge/promotion PowerShell; validation report and workflow checkout guards | Candidate Context v1 `source_sha` and immutable provenance | Exact SHA comparisons recur at selection, checkout, review, dry-run and promotion | Preserve read-back at trust boundaries; centralize semantic identity comparison in kernel |
| Candidate package SHA-256 | `Test-DDDAControlledReleaseCandidate.py`; candidate evidence restore blocks; governed merge/promotion; HRDR/Human Review records | Candidate Context v1 package identity plus kernel binding invariant | Artifact cardinality, report source and package hash checks are split across Python, PowerShell and copied YAML blocks | One reusable evidence-restoration collector produces verified package evidence for context |
| Human Review identity | `DDDAReleaseGovernanceSupport.ps1`; `Invoke-DDDAGovernedMergePr.ps1`; review scaffold/marker contract | Candidate Context v1 `human_review_reference`; Governance Kernel v1 merge-readiness rule | Marker cardinality/provenance parsing and exact SHA/package binding are separate checks | Collector parses one human-authored record; kernel evaluates its identity and verdict |
| HRDR identity | `Read-DDDAHrdr.py`; `DDDAReleaseGovernanceSupport.ps1`; `release_governance.py`; controlled candidate workflows | Candidate Context v1 `hrdr_reference`; Governance Kernel v1 release-readiness rule | Python and PowerShell parse records while workflows repeat selection/restoration logic | One HRDR collector normalizes the authoritative record; kernel owns identity/decision semantics |
| Mandatory checks | `DDDAGitHubSupport.ps1`; governed merge/promotion scripts; workflow required jobs | Candidate Context v1 `authoritative_check_summary`; Governance Kernel v1 readiness rule | Latest-run selection and operation-specific required-check assumptions live in different adapters | One paginated collector returns latest-by-name canonical evidence; kernel evaluates the required set |
| Physical release scope | `scripts/platform/Test-DDDAReleaseScope.py`; `runtime/platform/release_governance.py`; recovery ledger collector/validator | Governance Kernel v1 release-scope invariant over Candidate Context v1 | Collection, normal scope comparison and historical recovery coverage are intertwined | Keep Git/GitHub acquisition in collectors; kernel evaluates normalized physical scope; recovery adapter is explicit |
| Recovery classification | controlled candidate branch validator; recovery transformation module; recovery ledger evaluation; controlled workflows | Governance Kernel v1 explicit `release_mode`; recovery playbook adapter | Standard release evaluation imports recovery transformation and recognizes historical ledger internals | Move legacy recovery evidence behind an emergency-only adapter while retaining readable 0.1.1 evidence |
| Project release evidence | `Test-DDDAReleaseScope.py`; `release_governance.py`; Project reconciliation scripts | Candidate Context v1 evidence taxonomy; kernel owns only safety-relevant authority rules | Project planning/view/presentation details can currently block the same result as release authority mismatch | S3 classifies `SAFETY_BLOCKING`, `GOVERNANCE_PROJECTION`, `PRESENTATION`; reconciler still requires zero mismatches after mutation |
| Promotion readiness | `Invoke-DDDAGovernedPromotePr.ps1`; `Invoke-DDDAPromotePr.ps1`; `release_governance.py`; controlled promotion workflows | Governance Kernel v1 release/recovery readiness decision | Wrapper, workflow and Python gate each encode portions of readiness and side-effect permission | Kernel returns decision/failure codes; thin adapters enforce explicit authorization and execute only after PASS |

## Baseline interpretation

- A newer check run supersedes an older run of the same name; queued,
  in-progress, missing or latest failed evidence blocks.
- Exact SHA and package identity remain fail-closed.
- Current Project presentation mismatch is recorded as blocking. S3 may change
  that expected result only when the authority/projection taxonomy is
  introduced with an explicit remediation path.
- Historical controlled recovery remains characterized, but this baseline
  does not extend it or alter PR #146, release `v0.1.1`, its tag or assets.

## Change control

This v1 baseline is immutable in meaning. Incompatible fixture structure
requires `schema_version: 2`; corrected or intentionally changed outcomes must
cite the primary Change Request and the authority migration that caused them.
