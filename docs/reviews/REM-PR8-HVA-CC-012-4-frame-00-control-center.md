# REM-PR8-HVA-CC-012.4 — Frame 00 Control Center

Status: HVR remediation authorized — CHANGES_REQUIRED round 1

Date: 2026-08-07

## Trigger

Human visual review repeatedly showed that frame `00` devoted too much visual weight to Artifact Health while the project decision, decision owner and next action remained subordinate. REM-012.4 replaces the frame-00 information hierarchy without changing the DDD Starter journey, frame `01`, frame `10` or any workshop frame `20+`.

The original authorized predecessor was commit `6d34b008d5b6c32bdc6c555649f1047de3f1f66c`. The current HVR-remediation base is commit `40a64e950b408f7dfce7a2e642eaa0e3bcf1b38f`. The target remains PR `#8` on branch `feat/project-steering-and-documentation`.

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
- Artifact Health current summary: `1 SCAFFOLD · 2 WORKING`;
- lifecycle meanings for `SCAFFOLD`, `WORKING`, `CANDIDATE`, `VALIDATED`, `ACCEPTED` and `SUPERSEDED`;
- direct link to the project Artifact Registry, visually separated from the lifecycle legend.

`SUPERSEDED` is explained as a replacement state, not a maturity level above `ACCEPTED`.

## HVR-1 CHANGES_REQUIRED findings — 2026-08-07

The first human visual review rejected Frame `00` with three findings:

1. The sentence `Rozhodnutí musí být zaznamenáno v Git decision recordu.` is not actionable for a first viewer. It does not explain who records the decision or whether the user should use chat, YAML or another mechanism.
2. `MATURITY` was presented as a numeric summary duplicated from Artifact Health instead of a true legend explaining lifecycle-state meanings.
3. The project Artifact Registry link was visually embedded in the legend although it is a navigation/source action.

The authorized remediation changes only Frame `00` and its exact-SHA validation contract:

- the decision-owner sticky now says that the `Acceptance Business Owner` confirms G1 in the project DDDA chat; DDDA prepares the project decision record and no manual YAML editing is required;
- Artifact Health keeps the numeric current-state summary;
- the lower legend explains lifecycle-state meanings and ATTENTION/BLOCKING semantics without repeating lifecycle counts;
- the Artifact Registry action is moved into the separate current-status/action block and is no longer part of the lifecycle legend;
- existing eight managed Frame-00 items are reused; no new Miro item is created;
- frame `01`, frame `10` and all fifteen frames `20+` remain protected.

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

The HVR-remediation source test additionally enforces:

- `Git decision record` wording is absent;
- `JAK ROZHODNOUT` and the project DDDA chat instruction are present;
- lifecycle counts do not appear in the lifecycle legend;
- lifecycle-state meanings are present;
- the Artifact Registry link and source-of-truth text are outside the lifecycle legend.

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
HVR-1 frame 00: CHANGES_REQUIRED; remediation round 1 authorized
HVR-2 frame 01: NOT STARTED
HVR-3 frame 10: NOT STARTED
Cross-frame review: NOT STARTED
```

## Prior online read-back corrections retained

The first exact-SHA online attempt failed closed on the first managed text item because Miro returned hexadecimal style colors in lowercase while the declarative target used uppercase. The workflow restored the original frame successfully and did not mutate protected frames. The corrective implementation compares hexadecimal color tokens case-insensitively while retaining exact content, parent, geometry, typography, alignment and non-color style checks. A regression test reproduces the Miro normalization behavior.

The live frame-00 inventory later showed that five previously generated helper items had been recreated by rollback-safe remediations and therefore carried new Miro item IDs. REM-012.4 refreshed only those five managed IDs from the authoritative remote inventory. The semantic reuse remained unchanged and no new board item was created.

A subsequent correction preserved native sticky-note geometry because Miro normalizes sticky-note height. That correction is the direct base of this HVR remediation and remains part of the lineage and path allowlist.
