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

Frame `00` explains project purpose, current decision, decision owner, next action, ATTENTION, and explicit blockers. Frame `01` contains readable phase references and the gate-state legend. Frame `10` deterministically clones the eight supported onboarding items from source frame `3458764567890733009` and all 121 supported native items from filled-example frame `3458764567890733010`.

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
