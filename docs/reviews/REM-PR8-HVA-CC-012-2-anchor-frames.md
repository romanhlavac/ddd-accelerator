# REM-PR8-HVA-CC-012.2 — anchor-frame visual remediation

## Authorization and boundary

- Authorized exact base: `7badffb6ef6f3364569e68926eb511600eed38d3`.
- Target branch: `feat/project-steering-and-documentation`.
- Target review board: `uXjVH1phki0=`.
- Writable scope: frames `00`, `01`, and `10`, their existing children, managed images, and the compact Artifact Registry projection in frame `00`.
- Protected scope: all fifteen frames `20+`; their frame, child-item, and connector snapshot digest must remain byte-equivalent after canonical removal of Miro audit timestamps.
- Explicitly excluded: merge, promotion, release, tag, force-push, and any write to `main`.

## Human-review finding addressed

The prior human review failed because the board was technically traceable but visually unusable: frame overlap, unreadable journey typography, zero real image items, dominant legends in frame `00`, and a synthetic BMC in frame `10`. REM-012.2 repairs only the three anchor frames and stops before propagating the pattern to frames `20+`.

A proposed native Miro table was removed from the target design after the first exact-code run proved that it did not exist remotely and would not scale to a larger artifact catalog. The target architecture is now:

```text
Git/YAML source of truth
→ GitHub-rendered Markdown Artifact Registry
→ compact Miro health/attention projection + link
```

GitHub Pages is deliberately deferred to backlog issue `#45`; it is not part of this remediation or the current PR #8 merge decision.

## Deterministic target

### Frame 00 — Control Center

- Redline-aligned compact geometry: `7000 × 4914.42`.
- Compact summary, usage guide, five gate-state cards, lifecycle and provenance semantics.
- Existing authorized text item `3458764679756523220` becomes a compact `ARTIFACT HEALTH` projection containing:
  - total managed artifact count;
  - lifecycle counts;
  - current attention count and review warning;
  - explicit `Git/YAML is source of truth` statement;
  - direct link to `docs/artifacts/index.md` rendered by GitHub.
- The full registry remains outside Miro and can scale independently of the frame.
- The former 45-shape simulated table and temporary table `3458764679853742787` are removed only after all reversible checks pass.

### Frame 01 — DDD Starter journey

- Redline-aligned geometry and zero overlap with frame `00` or frames `20+`.
- Stage and gate typography `144`; semantic elements `80`; zone headings `144`.
- Eight actual phase visuals, each composed from the pinned redline process image plus its phase pin.
- Eight synthetic `INSPIRACE PRO …` cards are removed after image and geometry verification.

### Frame 10 — Align / Intake

- Existing frame ID and `6000 × 4800` geometry retained at the redline-aligned board position.
- Two-column workshop guide/reference layout.
- Actual Business Model Canvas source image from `Restored Strategic DDD - 2023-10`.
- Four compact concepts: `PROBLÉM`, `ROZHODNUTÍ`, `OWNER`, and `SCOPE`.
- Five surplus synthetic BMC shapes are removed.

## GitHub Markdown Artifact Registry

Authoritative projection file:

```text
docs/artifacts/index.md
```

Registry contract overlay:

```text
scaffolds/miro/rem-012-2-artifact-registry-gh-md.yaml
```

The overlay pins:

- the existing Miro text item and target geometry;
- exact GitHub Markdown path and URL;
- exact SHA-256 of the Markdown file;
- expected artifact IDs and lifecycle counts;
- attention count;
- source-of-truth wording;
- GitHub Pages backlog issue `#45`.

The technical run verifies both the committed Markdown content and the final Miro projection. A changed registry file changes its SHA-256 and invalidates prior technical evidence.

## Pinned visual provenance

| Asset | Source | SHA-256 |
|---|---|---|
| DDD Starter process image | redline board `uXjVH2vcvRI=` | `4ef989128feb63c579ae9a4edb99a14752c3796ad323ad6b74c38aafb879f940` |
| Phase pin image | redline board `uXjVH2vcvRI=` | `27f5b8a6f60597a9ce41012f721e982ec429746fbfbe7758f5aa7aaa19224132` |
| Business Model Canvas | Starter board `uXjVH27wYU4=` / frame `3458764567890733009` / item `3458764567890733049` | `18d82268341240c56f7f950a99b5064907247e1ef31a91443d59dc298404ee62` |

Every production image is identified by `source board → frame → item`, a pinned digest, target frame, target position, and target width. A second reconcile must produce `created=0`, `updated=0`, and `unchanged=17` with stable target item IDs.

## Transaction and evidence

The broker:

1. validates exact commit lineage and changed-path allowlists;
2. validates the remote board is entirely in either the expected pre-remediation state or the final target state;
3. snapshots all protected frames `20+`, their children, and relevant connectors;
4. verifies the committed GitHub Markdown registry, exact digest, expected rows and authority wording;
5. verifies the existing Miro registry projection item is inside the authorized Control Center frame;
6. applies reversible item and frame updates;
7. imports and verifies 17 managed image items twice;
8. verifies the final Miro Artifact Registry projection, frame geometry, zero overlap, and protected-frame digest;
9. only then removes obsolete shapes and the temporary legacy table;
10. publishes `result.json` as a GitHub Actions artifact.

A failure before irreversible cleanup triggers best-effort rollback of frames, items, and newly created managed images. Mixed/partial remote state is rejected fail-closed.

## Acceptance status semantics

A successful technical run yields:

```text
technical_status: PASS
human_review_status: PENDING
overall_status: READY_FOR_HUMAN_REVIEW
```

Technical acceptance does not convert the prior human-review failure into a pass. The next mandatory action is a human review checkpoint over frames `00`, `01`, and `10`. Frames `20+` remain unchanged until that checkpoint is explicitly accepted.
