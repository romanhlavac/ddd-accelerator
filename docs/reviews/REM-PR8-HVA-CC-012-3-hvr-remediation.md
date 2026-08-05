# REM-PR8-HVA-CC-012.3 — HVR usability remediation

## Trigger

Human visual review of product SHA `5a9cd256a75c2dea44cc67ceb101fd7afc91eb29` and transport SHA `562787796b7a60a1988f4b10247396900ce59bc4` concluded `CHANGES_REQUIRED`.

The prior technical evidence remained valid for lineage, image provenance, idempotence, collision checks, and protected-frame integrity. It did not demonstrate first-user usability.

## Findings

- Frame `00` was unreadable at normal review zoom and overemphasized context-free legends.
- Gate-state semantics belong with the journey in frame `01`.
- Lifecycle and attention semantics require explanatory text.
- Project Artifact Registry data must be project-owned, not shared global data in platform documentation.
- Phase references in frame `01` were displayed as thumbnails.
- Frame `10` omitted the filled, editable Scootoo BMC example from the reference board.

## Target

Frame `00` explains project purpose, current decision, decision owner, next action, ATTENTION, and explicit blockers. Frame `01` contains readable phase references and the gate-state legend. Frame `10` deterministically transfers eight onboarding reference elements from source frame `3458764567890733009`: seven supported native items plus the separately pinned `align-bmc` image from source item `3458764567890733049`. It also clones all 121 supported native items from filled-example frame `3458764567890733010`.

Project registry data are stored under:

```text
examples/minimal/projects/acceptance-claims-modernization/
├── artifacts/registry.yaml
└── docs/artifacts/index.md
```

All fifteen frames `20+` remain protected by canonical snapshot digest. The work does not change `main`, merge the pull request, publish a release, or approve G1.

A successful technical run yields:

```text
technical_status: PASS
human_review_status: PENDING
overall_status: READY_FOR_HUMAN_REVIEW
```

## HVR-1 checkpoint — frame 00

Review of PR head `68bf109c8e4d393be10e669414686e33511e8a6b` concluded `CHANGES_REQUIRED`.

The previous layout rendered `MATURITY` and `ATTENTION / BLOCKING` as two oversized square-like panels with small text, while the actual Artifact Health status was visually detached and subordinate.

REM-PR8-HVA-CC-012.3.1 therefore requires one integrated bottom health area:

- a wide panel occupying most of the `7000 px` frame width;
- a highlighted status strip with font size at least `64`;
- explanatory maturity and attention/blocking text with font size at least `48`;
- status and metrics before secondary explanatory content;
- geometric containment of status and detail elements inside the health panel;
- remote read-back of content, font sizes, geometry, and frame ownership;
- zero-mutation second reconcile;
- no changes to frames `01`, `10`, or `20+`.

Numeric tests are regression guardrails, not a substitute for visual review at normal working zoom.

## HVR-1 repeat checkpoint — frame 00

Review of transport SHA `f471f83e4b178c8fec239bb51c0188c2c7a4e304` again concluded `CHANGES_REQUIRED`.

The integrated health area was technically readable but still lacked an obvious project-scoped title, duplicated status in a redundant highlighted block, and rendered the actual artifact counts without enough visual weight. Maturity, attention, and blocking also lacked a reusable visual code.

REM-PR8-HVA-CC-012.3.2 therefore requires:

- the complete lower panel to be explicitly titled `ARTIFACT HEALTH — acceptance-claims-modernization`;
- removal of the redundant `HEALTH: ATTENTION` wording;
- one dominant status row containing actual values only;
- no explanatory legend text in the status row;
- a consistent visual code in both status and legend:
  - `🟦` maturity;
  - `🟧` attention;
  - `🟩` no active blocker;
  - `🟥` one or more active blockers;
- status font size at least `80` and legend font size at least `48`;
- explicit remote read-back of title, status values, color markers, style, geometry, and frame ownership;
- zero-mutation second reconcile;
- no changes to frames `01`, `10`, or `20+`.

The numeric and color-token tests are mandatory regression controls, while normal-zoom human review remains the acceptance gate.

## Sequential HVR operating rule

Human visual review proceeds one section at a time:

```text
show exactly one review target
→ PASS | PASS_WITH_NOTES | CHANGES_REQUIRED
→ if CHANGES_REQUIRED, remediate and repeat the same target
→ open the next target only after PASS
```

Current sequence:

```text
HVR-1 frame 00: CHANGES_REQUIRED — REM-012.3.2 pending
HVR-2 frame 01: NOT STARTED
HVR-3 frame 10: NOT STARTED
Cross-frame review: NOT STARTED
```
