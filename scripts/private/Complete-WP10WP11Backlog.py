from pathlib import Path
import json

root = Path('.')
bootstrap_path = root / 'config/governance/github-bootstrap.json'
data = json.loads(bootstrap_path.read_text(encoding='utf-8-sig'))
desired_children = [34, 35, 36, 37, 38, 39, 40, 47, 41, 46]
for rel in data['hierarchy']:
    if rel['parent'] == 20:
        rel['children'] = desired_children
        break
else:
    data['hierarchy'].append({'parent': 20, 'children': desired_children})

desired_deps = {
    47: [27, 31, 32, 34, 35, 36, 37, 38, 39, 40],
    41: [35, 40, 47],
    46: [47, 41],
}
dep_map = {d['blocked']: d for d in data['dependencies']}
for blocked, blockers in desired_deps.items():
    if blocked in dep_map:
        dep_map[blocked]['blocked_by'] = blockers
    else:
        data['dependencies'].append({'blocked': blocked, 'blocked_by': blockers})

covered = {n for group in data['item_groups'] if group.get('kind') == 'issue' for n in group.get('numbers', [])}
if not {46, 47}.issubset(covered):
    data['item_groups'].append({
        'kind': 'issue',
        'numbers': [46, 47],
        'metadata': {
            'Status': 'Backlog',
            'Work Package': 'WP-11',
            'Item Type': 'Change Request',
            'Target Release': 'TBD',
            'Blocked': 'Yes',
            'Human Review': 'Not required',
        },
    })
bootstrap_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

policy_path = root / 'config/governance/backlog-policy.yaml'
policy = policy_path.read_text(encoding='utf-8-sig')
old_children = 'children: [34, 35, 36, 37, 38, 39, 40, 41]'
new_children = 'children: [34, 35, 36, 37, 38, 39, 40, 47, 41, 46]'
policy = policy.replace(old_children, new_children)
if 'rationale: cross-WP integration consumes the canonical ingestion' not in policy:
    marker = '\npriority_semantics:'
    addition = '''
    - blocking: 27
      blocked: 47
      rationale: cross-WP integration consumes the canonical ingestion and evidence materialization contract
    - blocking: 31
      blocked: 47
      rationale: integration preserves security, classification and isolation boundaries
    - blocking: 32
      blocked: 47
      rationale: integration consumes incremental evidence lifecycle and traceability
    - blocking: 34
      blocked: 47
      rationale: integration materializes results through the EventStorming session contract
    - blocking: 35
      blocked: 47
      rationale: integration reuses the Miro seed and governed round-trip contract
    - blocking: 36
      blocked: 47
      rationale: integration invokes versioned analytical capability contracts
    - blocking: 37
      blocked: 47
      rationale: integration composes the bounded orchestration runtime
    - blocking: 38
      blocked: 47
      rationale: integration reuses fan-in, alternatives and conflict records
    - blocking: 39
      blocked: 47
      rationale: integration stops at explicit human checkpoints
    - blocking: 40
      blocked: 47
      rationale: integration preserves failure, retry, resume and observability contracts
    - blocking: 47
      blocked: 41
      rationale: final package-first E2E consumes the evidence-to-workshop integration flow
    - blocking: 47
      blocked: 46
      rationale: final documentation requires the implemented integration flow for as-built validation
    - blocking: 41
      blocked: 46
      rationale: final documentation requires package-first acceptance for as-built closure
'''
    if marker not in policy:
        raise RuntimeError('priority_semantics marker not found')
    policy = policy.replace(marker, '\n' + addition.rstrip() + marker, 1)
policy = policy.replace(
    'Secure and auditable Office, PDF and ArchiMate ingestion with source provenance.',
    'Secure and auditable ingestion with normalized evidence, Markdown materialization, YAML registration and source provenance.',
)
policy = policy.replace(
    'Executable EventStorming and bounded multi-agent workflows with explicit human checkpoints.',
    'Executable EventStorming, evidence-to-workshop integration and bounded multi-agent workflows with explicit human checkpoints.',
)
policy_path.write_text(policy, encoding='utf-8')

wp10 = '''# WP-10 — Enterprise ingestion

## Outcome

```text
source document/model
→ normalized evidence fragments
→ Markdown evidence projection
→ YAML evidence/artifact registration
→ downstream reviewed interpretation
```

Ingestion creates evidence, not an approved domain model, architecture decision or gate approval.

## Ownership

- #27 — manifest, source catalog, normalized evidence, Markdown materialization, YAML registration and common core
- #28 — Office adapters
- #29 — PDF and explicit OCR fallback
- #30 — ArchiMate
- #31 — security, privacy, classification and isolation
- #32 — incremental lifecycle, reconciliation, tombstones, resume and traceability
- #33 — synthetic corpus and package-first acceptance

## Authority boundary

Source, extracted evidence, Markdown evidence, YAML registration, reviewed interpretation, project artifact and human decision are separate authority levels. Markdown is a human-readable evidence projection; YAML registration is the machine-readable catalog, hash binding and traceability record.

## Acceptance

Every evidence fragment retains source/version/location/adapter provenance. Supported evidence units produce Markdown evidence and YAML registration. Registration binds to the Markdown SHA-256 and detects drift. Reruns are idempotent; changed/deleted sources use reconciliation and tombstones. Unsupported content and extraction limitations are explicit. No adapter reads/writes outside allowed boundaries. Evidence never creates automatic DDD or architecture approval. Package-first E2E covers add/change/delete/failure/resume and materialization with synthetic data.

## Dependencies and exit

WP-08 provides validation, packaging and security boundaries. WP-11 #47 consumes registered evidence but does not implement ingestion. Exit requires compatible #27–#33 contracts, passing materialization/idempotence/security/reconciliation tests and current native backlog governance.
'''
(root / 'docs/roadmap/work-packages/WP-10-enterprise-ingestion.md').write_text(wp10, encoding='utf-8')

wp11 = '''# WP-11 — EventStorming & multi-agent orchestration

## Outcome

```text
WP-10 registered evidence
→ analytical capabilities
→ #34 EventStorming session
→ #35 Miro workshop
→ governed round-trip
→ Control Center and artifacts
→ human decision
```

## Ownership

- #34 — EventStorming session/item contracts
- #35 — Miro seeding, mapping, layout ownership and round-trip
- #36 — agent/capability contracts
- #37 — bounded orchestration/fan-out
- #38 — fan-in, alternatives and conflicts
- #39 — human checkpoints and authorization
- #40 — failure/retry/replay/resume and observability
- #47 — integration-only evidence-to-workshop orchestration
- #41 — final synthetic package-first E2E
- #46 — first-user target/as-built documentation

WP-10 #27–#33 remain the sole owners of ingestion, normalized/Markdown evidence and YAML evidence registration. #47 composes existing contracts and creates no parallel model.

## Dependency order

```text
#34 → #35
#36 → #37 → #38
#36/#37/#38 → #39
#37/#38/#39 → #40
#27/#31/#32 + #34–#40 → #47
#35/#40/#47 → #41
#47/#41 → final as-built closure #46
```

## Acceptance and exit

Analytical output materializes only through #34 and Miro round-trip only through #35. Manual layout survives refresh; new Miro items require explicit promotion; semantic conflicts never use last-write-wins. Evidence is traceable through task, session and workshop delta. Automation may create ready-for-review, never human passed. Exit requires #47 integration without duplicate models, #41 package-first and human acceptance, #46 as-built validation, and current native hierarchy/dependencies.
'''
(root / 'docs/roadmap/work-packages/WP-11-eventstorming-multi-agent-orchestration.md').write_text(wp11, encoding='utf-8')

index_path = root / 'docs/roadmap/backlog-index.md'
index = index_path.read_text(encoding='utf-8-sig')
index = index.replace(
    '- #27 — enterprise manifest, provenance and normalized ingestion core',
    '- #27 — enterprise manifest, normalized evidence, Markdown materialization and YAML registration',
)
old = '- #40 — failure/timeout/retry/replay/resume and observability/cost governance\n- #41 — synthetic multi-agent reference workflow and package-first acceptance'
new = '- #40 — failure/timeout/retry/replay/resume and observability/cost governance\n- #47 — evidence-to-workshop integration orchestration\n- #41 — synthetic multi-agent reference workflow and package-first acceptance\n- #46 — end-to-end first-user target/as-built documentation'
if '#47 — evidence-to-workshop integration orchestration' not in index:
    if old not in index:
        raise RuntimeError('WP-11 index marker not found')
    index = index.replace(old, new)
index_path.write_text(index, encoding='utf-8')

assert next(x['children'] for x in data['hierarchy'] if x['parent'] == 20) == desired_children
assert new_children in policy_path.read_text(encoding='utf-8')
assert '#47 — evidence-to-workshop integration orchestration' in index_path.read_text(encoding='utf-8')
