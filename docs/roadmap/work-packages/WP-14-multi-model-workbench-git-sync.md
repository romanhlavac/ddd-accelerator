# WP-14 — Multi-Model Workbench & Git-backed Model Synchronization

**Authority:** #148. **Children:** #149–#154. **Proposed target:** 0.2.0; no Milestone membership is authorized by #155. **Priority/order:** unset pending a human Project decision.

## Outcome
One provider-neutral Git-backed synchronization contract across workshop, DDD and architecture providers. Git/DDDA owns cross-tool identity, lifecycle/provenance, traceability, sync state, conflicts/tombstones and decisions; provider-native semantics remain provider-owned.

## Dependency topology
```text
#149 → #150
#149 → #151
#149 → #152
#149 + #150 + #151 + #152 → #153
#150 + #153 → #154
```

#155 materializes planning governance only. It does not authorize implementation of #149–#154, assign priority, or approve DDDA 0.2.0 release scope.
