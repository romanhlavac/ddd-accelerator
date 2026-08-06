# REM-PR8-HVA-CC-012.4 — Frame 00 Control Center

Status: Authorized for implementation

Date: 2026-08-06

## Trigger

Human visual review repeatedly showed that frame `00` devoted too much visual weight to Artifact Health while the project decision, decision owner and next action remained subordinate. REM-012.4 replaces the frame-00 information hierarchy without changing the DDD Starter journey, frame `01`, frame `10` or any workshop frame `20+`.

The authorized predecessor is commit `6d34b008d5b6c32bdc6c555649f1047de3f1f66c`. The target remains PR `#8` on branch `feat/project-steering-and-documentation`.

## Decision

Frame `00` is a project decision cockpit, not a methodology guide or a global legend catalogue. It presents four zones in this order:

1. project identity and purpose;
2. the current decision, phase/gate, decision owner and next action;
3. explicit ATTENTION and BLOCKERS;
4. a secondary Artifact Health projection linked to the project-owned registry.

Gate state, artifact lifecycle and artifact provenance remain separate concepts. Frame `00` does not carry the full gate-state legend or provenance legend. Gate guidance remains with the journey in frame `01`.

## Project-owned source data

The example projection is tied to:

```text
examples/minimal/projects/acceptance-claims-modernization/
├── artifacts/registry.yaml
└── docs/artifacts/index.md
```

The registry contains three artifacts: one `SCAFFOLD`, two `WORKING`, one ATTENTION and zero blockers. `Acceptance Business Owner` is the project-charter owner and therefore the displayed decision-owner role. Miro is a working projection; Git/YAML remains authoritative.

## Frame-00 content contract

The frame must make the following information readable at normal working zoom:

- project: `acceptance-claims-modernization`;
- phase/gate: `ALIGN / G1`;
- gate state: `NOT_READY`;
- decision question: whether the first bounded modernization slice and evidence needed for Discover are sufficiently defined;
- decision owner: `Acceptance Business Owner`;
- next action: complete scope boundaries and success measures, then prepare G1 for human review;
- ATTENTION: `1`;
- BLOCKERS: `0`;
- Artifact Health: `1 SCAFFOLD · 2 WORKING`;
- direct link to the project Artifact Registry.

`SUPERSEDED` is explained as a replacement state, not a maturity level above `ACCEPTED`.

## Technical scope

Allowed Miro mutation:

```text
board: uXjVH1phki0=
frame: 3458764679756478046  # 00 only
```

The implementation reuses eight existing frame-00 items. Cleanup is limited to explicit IDs and exact geometry/text signatures of previously generated REM-012.3.x helper items. Unknown or manually authored content is not eligible for broad deletion.

Protected scope:

- frame `01`;
- frame `10`;
- all fifteen frames `20+`.

Their combined canonical snapshot digest must remain unchanged.

## Validation contract

The exact candidate SHA must pass:

- repository CI;
- REM-012.4 source-level tests;
- candidate package build and provenance check;
- remote Miro parent/content/style/geometry read-back;
- first reconcile followed by a zero-mutation second reconcile;
- protected-frame digest comparison;
- forbidden legacy-guidance check;
- machine-readable evidence upload.

A successful technical execution yields:

```text
technical_status: PASS
human_review_status: PENDING
overall_status: READY_FOR_HUMAN_REVIEW
```

Technical PASS does not approve G1 and does not complete HVR-1.

## Governance constraints

The workflow must not:

- merge PR `#8`;
- promote or release the platform;
- create a tag;
- write to `main`;
- approve G1;
- open HVR-2 before HVR-1 is accepted.

## Human review sequence

```text
HVR-1 frame 00: REM-012.4 authorized; technical validation pending
HVR-2 frame 01: NOT STARTED
HVR-3 frame 10: NOT STARTED
Cross-frame review: NOT STARTED
```
