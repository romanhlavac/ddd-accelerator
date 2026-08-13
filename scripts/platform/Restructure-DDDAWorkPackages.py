import json
import re
import subprocess
from pathlib import Path

OWNER = "romanhlavac"
REPO = "romanhlavac/ddd-accelerator"
PROJECT_TITLE = "DDDA Platform Backlog"
WP08 = 17
WP11 = 20
WP12 = 60
WP13 = 61
ES_E2E = 62


def cmd(program, *args, json_out=False, stdin=None):
    p = subprocess.run([program, *args], input=stdin, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{program} {' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def gql(query, variables=None):
    return cmd("gh", "api", "graphql", "--input", "-", json_out=True, stdin=json.dumps({"query": query, "variables": variables or {}}))


def issue(n):
    return gh("api", f"repos/{REPO}/issues/{n}", json_out=True)


def patch_issue(n, *, title=None, body=None):
    args = ["api", "--method", "PATCH", f"repos/{REPO}/issues/{n}"]
    if title is not None:
        args += ["-f", f"title={title}"]
    if body is not None:
        args += ["-f", f"body={body}"]
    gh(*args)


def parent_number(data):
    url = data.get("parent_issue_url")
    return int(url.rstrip("/").split("/")[-1]) if url else None


def remove_parent(parent, data):
    gh("api", "--method", "DELETE", f"repos/{REPO}/issues/{parent}/sub_issue", "-F", f"sub_issue_id={data['id']}")


def add_parent(parent, data):
    gh("api", "--method", "POST", f"repos/{REPO}/issues/{parent}/sub_issues", "-F", f"sub_issue_id={data['id']}")


def set_parent_exact(n, target):
    d = issue(n)
    current = parent_number(d)
    if current == target:
        return
    if current is not None:
        remove_parent(current, d)
    if target is not None:
        add_parent(target, d)
    d2 = issue(n)
    if parent_number(d2) != target:
        raise RuntimeError(f"Parent read-back failed for #{n}: {parent_number(d2)} != {target}")


def blocker_map(n):
    rows = gh("api", f"repos/{REPO}/issues/{n}/dependencies/blocked_by?per_page=100", json_out=True) or []
    return {int(x["number"]): x for x in rows}


def set_blockers_exact(n, wanted):
    current = blocker_map(n)
    wanted = set(wanted)
    for extra in sorted(set(current) - wanted):
        gh("api", "--method", "DELETE", f"repos/{REPO}/issues/{n}/dependencies/blocked_by/{current[extra]['id']}")
    for missing in sorted(wanted - set(current)):
        d = issue(missing)
        gh("api", "--method", "POST", f"repos/{REPO}/issues/{n}/dependencies/blocked_by", "-F", f"issue_id={d['id']}")
    got = set(blocker_map(n))
    if got != wanted:
        raise RuntimeError(f"Dependency read-back failed for #{n}: {sorted(got)} != {sorted(wanted)}")


def replace_parent_text(body, old_wp, old_issue, new_wp, new_issue):
    body = body.replace(f"{old_wp} — #{old_issue}", f"{new_wp} — #{new_issue}")
    body = body.replace(f"{old_wp} - #{old_issue}", f"{new_wp} - #{new_issue}")
    body = body.replace(f"parent {old_wp} #{old_issue}", f"parent {new_wp} #{new_issue}")
    body = body.replace(f"Parent {old_wp} #{old_issue}", f"Parent {new_wp} #{new_issue}")
    return body


WP17_BODY = """# Work Package: WP-08 — DDDA 0.1.0 platform foundation & PR8 closure

## Desired outcome

Uzavřít již implementovaný foundation scope PR #8 jako reprodukovatelný, auditovatelný a bezpečný DDDA 0.1.0 baseline. WP-08 od tohoto splitu není dlouhodobý catch-all pro další platformní evoluci.

## Current state

```text
State: active / blocked
Target release: 0.1.0
Implementation: PR #8
Human Review: IN PROGRESS
Release readiness: NO_GO
Merge/promotion: BLOCKED
```

## Scope boundary after backlog split

WP-08 owns pouze:

- PR #8 current implementation as-is;
- #9–#15 release remediation / Human Review / HRDR closure;
- exact-SHA validation and candidate package evidence;
- current Miro remediation/HVR required to close PR #8;
- promotion dry-run and explicit GO/NO-GO preparation;
- preservation of the already delivered generic baseline contracts for downstream WPs.

No new feature scope may be added to PR #8 through WP-08.

Moved future evolution:

- #53–#57 → WP-12 Miro platform environments & lifecycle (#60);
- #45 → `Work Package: Other` as cross-cutting Artifact Registry projection;
- multi-agent orchestration is not WP-08 scope and is owned by WP-13 (#61).

## Stable baseline contracts consumed downstream

PR #8 remains the foundation for:

- generic platform CLI / validation / package / promotion guards;
- project steering and G1–G8 safety boundaries;
- generic Miro runtime, mapping, sync-state, idempotence and ADR 0007 execution profiles;
- preliminary agent/capability contracts later versioned by WP-13/#36;
- minimal ingestion/package baseline later evolved by WP-10;
- methodology baseline later refined by WP-11/#48/#52.

## Critical path

```text
#13 DONE
→ #14 current Miro board remediation
→ #12 Miro evidence contract
→ deterministic suites PASS
→ freeze PR #8 SHA
→ final Human Visual Review
→ promotion dry-run
→ #9 HRDR finalization
→ explicit GO / GO_WITH_ACCEPTED_RISKS / NO_GO
```

#15 remains the execution/coordination plan and does not replace native dependency relationships.

## Acceptance criteria

- [ ] all unresolved RED findings for the frozen PR8 SHA are closed with evidence;
- [ ] technical Miro PASS remains separate from Human Review PASS;
- [ ] automation cannot create human gate/release approval;
- [ ] deterministic validation is bound to exact SHA and package hash;
- [ ] promotion dry-run performs no merge/tag/release;
- [ ] no future WP-12/WP-13 feature expands PR #8 implicitly;
- [ ] merge/release occurs only after separate explicit human instruction.

## Recommended implementation order

Project priority: **P0** — finish current PR8 closure first.

## Repository roadmap

`docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md`
"""

WP20_BODY = """# Work Package: WP-11 — EventStorming methodology & workshop runtime

## Desired outcome

Dodat samostatný, metodicky konzistentní a package-first ověřitelný EventStorming workflow bez mandatory závislosti na multi-agent orchestration.

```text
WP-10 registered evidence
→ #34 EventStorming session
→ #35 Miro seed
→ human-facilitated workshop
→ #35 governed round-trip
→ consolidated artifacts / Control Center
→ explicit human decision
```

## Capability ownership

- #34 — executable EventStorming session/item contracts and runtime state;
- #52 — canonical detailed human facilitation methodology for Big Picture, Process Modeling and Design-Level;
- #35 — EventStorming-specific Miro realization over generic PR8/WP-12 platform runtime;
- #47 — base evidence→session→workshop integration, without mandatory agent runtime;
- #48 — DDD Starter WHEN/WHY and phase semantics;
- #62 — EventStorming package-first workshop E2E acceptance;
- #46 — first-user target/as-built guide.

Mandatory ownership boundary:

```text
#48 = WHEN / WHY / phase semantics
#52 = HOW to facilitate
#34 = executable session/item model
#35 = Miro realization
#47 = hand-off/composition
#62 = EventStorming E2E acceptance
#46 = user-facing explanation
```

## Explicit split from WP-13

#36–#41 are no longer children or mandatory completion dependencies of WP-11. They belong to WP-13 (#61).

WP-13 may optionally provide analytical hypotheses/candidates to an EventStorming session through a future adapter, but the base WP-11 workflow and its acceptance cannot require WP-13.

## Dependencies

Consumed contracts:

- WP-08 / PR #8 stable validation, Human Review safety and generic Miro baseline;
- WP-10 registered evidence/provenance;
- WP-12 generic Miro environment lifecycle where applicable.

Target direct dependency graph:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46 final as-built
```

## Recommended implementation order

Project priority: **P1** — first capability stream after stable PR8 baseline.

Recommended implementation slices:

```text
#52 + #48
→ shared terminology/non-duplication review
→ #34 compatibility
→ #35
→ #47
→ #62
→ #46
```

## Acceptance criteria

- [ ] exactly three EventStorming formats remain canonical;
- [ ] Big Picture does not require Commands/Policies/Aggregates;
- [ ] #48 and #52 do not duplicate methodology ownership;
- [ ] #47 has no mandatory dependency on #36–#40;
- [ ] #62 passes without multi-agent runtime;
- [ ] EventStorming-specific Miro logic reuses generic platform runtime rather than duplicating it;
- [ ] technical completion never implies human approval;
- [ ] #46 final closure uses #62, not WP-13/#41, as EventStorming E2E acceptance.

## Target release

`TBD`

## Repository roadmap

`docs/roadmap/work-packages/WP-11-eventstorming-methodology-workshop-runtime.md`
"""

WP60_BODY = """# Work Package: WP-12 — Miro platform environments & lifecycle

## Desired outcome

Own the long-term generic Miro platform lifecycle outside PR #8 closure: persistent Platform Lab, reference/adoption lifecycle, deterministic CI/HVR materialization, Example Project, Project X provisioning, environment rebinding and explicit profile credentials.

## Children

- #53 — persistent DDDA Platform Lab + reference/adoption lifecycle;
- #54 — persistent DDDA Example Project lifecycle;
- #55 — per-project Miro identity/team/Space/token UX;
- #56 — corporate team/Space rebinding;
- #57 — legacy generic credential fallback removal.

## Baseline

Consumes stable PR #8 generic Miro runtime and ADR 0007 execution-profile contract. WP-11/#35 owns only EventStorming-specific semantics and must reuse this generic boundary.

## Recommended implementation order

Project priority: **P2**. It follows PR8 closure and is lower default priority than WP-11, but may overlap WP-11 once the relevant PR8 Miro baseline is stable.

```text
#53
→ #54 + #55
→ #56 when external corporate prerequisites exist
→ #57 after #53/#54/#55
```

## Target release

`TBD`

## Repository roadmap

`docs/roadmap/work-packages/WP-12-miro-platform-environments-lifecycle.md`
"""

WP61_BODY = """# Work Package: WP-13 — Multi-agent orchestration & evidence synthesis

## Desired outcome

Own bounded multi-agent execution as an independent capability stream, without making EventStorming dependent on completion of an agent platform.

## Children

- #36 — versioned capability/agent contracts;
- #37 — orchestrator and bounded fan-out;
- #38 — fan-in, alternatives, deduplication and conflicts;
- #39 — human checkpoints, authorization and safety;
- #40 — failure, timeout, retry, replay, resume and observability;
- #41 — synthetic package-first multi-agent acceptance.

## Core flow

```text
registered evidence / bounded task inputs
→ versioned capabilities
→ bounded fan-out
→ fan-in / alternatives / explicit conflicts
→ explicit human checkpoint
→ retry / replay / resume
→ governed artifacts and reports
```

## Boundary to WP-11

WP-11 EventStorming is an independent sibling. WP-13 outputs may later be consumed as optional hypotheses/candidates, but no mandatory reverse dependency from WP-11 to WP-13 is allowed for the base workshop flow.

## Recommended implementation order

Project priority: **P3**.

```text
#36 → #37 → #38 → #39 → #40 → #41
```

## Target release

`TBD`

## Repository roadmap

`docs/roadmap/work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md`
"""

ES62_BODY = """# Change Request: EventStorming package-first workshop E2E acceptance

## Parent Work Package

WP-11 — #20

## Goal

Dodat samostatný EventStorming package-first E2E acceptance scénář, který nevyžaduje WP-13 multi-agent orchestration.

```text
synthetic WP-10 registered evidence
→ #34 EventStorming session
→ #35 Miro seed
→ workshop delta fixture / explicit human-review checkpoint
→ #35 governed round-trip
→ provenance + Control Center projection
→ deterministic exact-SHA validation report
```

## Direct dependencies

- #34 — session/item contract;
- #35 — Miro realization and governed round-trip;
- #47 — evidence-to-workshop base integration;
- #48 — DDD Starter phase semantics;
- #52 — canonical facilitation methodology.

## Acceptance criteria

- [ ] clean candidate/release package + synthetic evidence is the starting point;
- [ ] base PASS requires no #36–#40 runtime;
- [ ] evidence → session → Miro → aftermath provenance is traceable;
- [ ] second reconcile is zero-mutation;
- [ ] human-owned layout survives semantic refresh;
- [ ] technical PASS remains distinct from human methodology/usability acceptance;
- [ ] exact SHA and package hash are recorded;
- [ ] #46 can use this scenario as canonical EventStorming first-user E2E evidence.

## Target release

`TBD`
"""

ISSUE41_BODY = """# Change Request: Synthetic multi-agent package-first acceptance

## Parent Work Package

WP-13 — #61

## Goal

Prokázat bounded multi-agent orchestration jako samostatný package-first workflow bez mandatory EventStorming dependency.

```text
synthetic registered evidence / task inputs
→ #36 versioned capabilities
→ #37 bounded fan-out
→ #38 fan-in with duplicate/complementary/contradictory outputs
→ #39 explicit human checkpoint
→ #40 injected failure + retry/replay/resume
→ governed artifacts and reports
```

## Direct dependencies

#36, #37, #38, #39, #40.

## Acceptance criteria

- [ ] deterministic synthetic inputs only;
- [ ] at least three bounded capabilities are exercised;
- [ ] fan-in preserves duplicate/complementary/contradictory outcomes explicitly;
- [ ] contradiction remains unresolved until explicit human action;
- [ ] automation cannot satisfy the human checkpoint;
- [ ] injected retryable failure resumes without duplicate managed artifacts;
- [ ] reports preserve task/run/provenance/resource signals without secrets;
- [ ] EventStorming is optional integration coverage, not a core prerequisite;
- [ ] exact-SHA package-first validation is reproducible.

## Target release

`TBD`
"""

ISSUE47_BODY = """# Change Request: Evidence → EventStorming workshop → governed round-trip

## Parent Work Package

WP-11 — #20

## Goal

Propojit WP-10 registered evidence se základním EventStorming workshop flow bez mandatory závislosti na WP-13 multi-agent runtime.

```text
WP-10 registered evidence
→ #34 EventStorming session
→ #35 Miro seed
→ human workshop
→ #35 governed round-trip
→ consolidated project artifacts / Control Center
```

## Contract ownership

- WP-10 owns source/evidence inception and provenance;
- #34 owns EventStorming session/items;
- #35 owns EventStorming-specific Miro mapping/layout/sync;
- #47 owns only hand-off/composition and provenance across those contracts;
- WP-13 may optionally supply analytical hypotheses through a later adapter but is not required here.

## Direct dependencies

- #27 — foundational registered evidence contract;
- #31 — security/classification policy;
- #32 — incremental evidence lifecycle/provenance;
- #34 — session/item model;
- #35 — Miro realization.

## In scope

- immutable evidence snapshot selection for one session;
- evidence→session binding and provenance;
- dry-run and explicit workshop seed/apply;
- governed Miro→YAML aftermath using #35;
- Control Center/report composition without a second datastore;
- stable command flow composing existing subsystems.

## Out of scope

- new ingestion/evidence model;
- agent contracts/fan-out/fan-in runtime;
- duplicate EventStorming model;
- duplicate Miro renderer/sync engine;
- automatic business/domain/gate approval;
- implicit Git commit/push/merge/release.

## Acceptance criteria

- [ ] no duplicate source/evidence/session/Miro contracts;
- [ ] source/evidence is traceable to session item and workshop delta;
- [ ] #34 is the only session semantic model;
- [ ] #35 is the only EventStorming Miro sync/layout owner;
- [ ] unchanged rerun is idempotent;
- [ ] technical completion cannot create human `passed`;
- [ ] #62 can consume this flow without WP-13.

## Target release

`TBD`
"""


def edit_issue_contracts():
    patch_issue(17, title="[WP-08] DDDA 0.1.0 platform foundation & PR8 closure", body=WP17_BODY)
    patch_issue(20, title="[WP-11] EventStorming methodology & workshop runtime", body=WP20_BODY)
    patch_issue(60, body=WP60_BODY)
    patch_issue(61, body=WP61_BODY)
    patch_issue(62, body=ES62_BODY)

    d45 = issue(45)
    b45 = d45.get("body") or ""
    b45 = b45.replace("WP-08 — #17", "Other — cross-cutting")
    b45 = b45.replace("Future WP-08 evolution: IN SCOPE", "Cross-cutting future platform evolution: IN SCOPE")
    b45 = b45.replace("Native parent-child membership under #17 does not imply Milestone `DDDA 0.1.0` membership, priority or approval.", "This cross-cutting CR has no native WP parent. It remains outside Milestone `DDDA 0.1.0` unless separately approved.")
    b45 = b45.replace("#45 is planned independently from current PR #8 remediation and release decision.", "#45 is planned as cross-cutting work independently from current PR #8 remediation and release decision.")
    patch_issue(45, title="[CR] Zavést GitHub Pages dashboard pro Artifact Registry", body=b45)

    for n in [53, 54, 55, 56, 57]:
        d = issue(n)
        title = re.sub(r"^\[WP-08\]", "[WP-12]", d["title"])
        body = replace_parent_text(d.get("body") or "", "WP-08", 17, "WP-12", 60)
        body = body.replace("future WP-08 evolution", "WP-12 evolution")
        body = body.replace("Future WP-08 evolution", "WP-12 evolution")
        body = body.replace("parent WP-08 #17", "parent WP-12 #60")
        body = body.replace("parent WP-08 — #17", "parent WP-12 — #60")
        patch_issue(n, title=title, body=body)

    for n in [36, 37, 38, 39, 40]:
        d = issue(n)
        title = re.sub(r"^\[WP-11\]", "[WP-13]", d["title"])
        body = replace_parent_text(d.get("body") or "", "WP-11", 20, "WP-13", 61)
        patch_issue(n, title=title, body=body)

    d41 = issue(41)
    patch_issue(41, title=re.sub(r"^\[WP-11\]", "[WP-13]", d41["title"]), body=ISSUE41_BODY)
    patch_issue(47, body=ISSUE47_BODY)

    d46 = issue(46)
    b46 = d46.get("body") or ""
    b46 = b46.replace("agent/capability contracts, orchestration, fan-in a human checkpoints | #36–#40", "optional multi-agent analytical extension | WP-13 #36–#40")
    b46 = b46.replace("výsledný synthetic package-first E2E | #41", "EventStorming package-first E2E | #62")
    b46 = b46.replace("after stable contracts #27 and #34–#40", "after stable WP-10 evidence and WP-11 #34/#35 contracts")
    b46 = b46.replace("- #41 — resulting package-first acceptance;", "- #62 — EventStorming package-first workshop E2E acceptance;")
    b46 = b46.replace("#47/#41/#48/#52", "#47/#62/#48/#52")
    b46 = b46.replace("#27–#41, #47, #48 and #52", "WP-10 + #34/#35/#47/#48/#52/#62")
    b46 += "\n\n## Backlog split note (2026-08-13)\n\nWP-13/#36–#41 is optional multi-agent evolution and is not a final-closure dependency of this WP-11 first-user guide. EventStorming E2E closure is owned by #62.\n"
    patch_issue(46, body=b46)


def edit_hierarchy_and_dependencies():
    for n in [45, 53, 54, 55, 56, 57]:
        set_parent_exact(n, None if n == 45 else 60)
    for n in [36, 37, 38, 39, 40, 41]:
        set_parent_exact(n, 61)
    set_parent_exact(62, 20)

    exact = {
        35: {34, 52},
        37: {36},
        38: {37},
        39: {36, 37, 38},
        40: {37, 38, 39},
        41: {36, 37, 38, 39, 40},
        47: {27, 31, 32, 34, 35},
        62: {34, 35, 47, 48, 52},
        46: {47, 62, 48, 52},
        49: {16, 46, 48, 53},
        57: {53, 54, 55},
    }
    for n, blockers in exact.items():
        set_blockers_exact(n, blockers)


def upsert_item_group(cfg, n, overrides):
    previous = {}
    kept = []
    for group in cfg.get("item_groups", []):
        if group.get("kind") != "issue":
            kept.append(group)
            continue
        nums = [int(x) for x in group.get("numbers", [])]
        if n in nums:
            previous.update(group.get("metadata") or {})
            nums = [x for x in nums if x != n]
        if nums:
            g = dict(group)
            g["numbers"] = nums
            kept.append(g)
    previous.update(overrides)
    kept.append({"kind": "issue", "numbers": [n], "metadata": previous})
    cfg["item_groups"] = kept


def update_config():
    p = Path("config/governance/github-bootstrap.json")
    cfg = json.loads(p.read_text(encoding="utf-8-sig"))
    hierarchy = [x for x in cfg.get("hierarchy", []) if int(x["parent"]) not in {17, 20, 60, 61}]
    hierarchy += [
        {"parent": 17, "children": [9, 10, 11, 12, 13, 14, 15]},
        {"parent": 20, "children": [34, 52, 35, 47, 48, 46, 62]},
        {"parent": 60, "children": [53, 54, 55, 56, 57]},
        {"parent": 61, "children": [36, 37, 38, 39, 40, 41]},
    ]
    hierarchy.sort(key=lambda x: int(x["parent"]))
    cfg["hierarchy"] = hierarchy

    dep_target = {
        35: [34, 52], 37: [36], 38: [37], 39: [36, 37, 38], 40: [37, 38, 39],
        41: [36, 37, 38, 39, 40], 47: [27, 31, 32, 34, 35], 62: [34, 35, 47, 48, 52],
        46: [47, 62, 48, 52], 49: [16, 46, 48, 53], 57: [53, 54, 55],
    }
    deps = [x for x in cfg.get("dependencies", []) if int(x.get("blocked", -1)) not in dep_target]
    deps += [{"blocked": n, "blocked_by": vals} for n, vals in dep_target.items()]
    deps.sort(key=lambda x: int(x["blocked"]))
    cfg["dependencies"] = deps

    wp_field = next(x for x in cfg["fields"] if x.get("name") == "Work Package")
    existing = {x["name"]: x for x in wp_field.get("options", [])}
    desired = [
        ("WP-08", "BLUE", "DDDA 0.1.0 platform foundation and PR8 closure."),
        ("WP-09", "PURPLE", "Strategy, portfolio and program lifecycle."),
        ("WP-10", "GREEN", "Enterprise ingestion."),
        ("WP-11", "ORANGE", "EventStorming methodology and workshop runtime."),
        ("WP-12", "BLUE", "Miro platform environments and lifecycle."),
        ("WP-13", "PURPLE", "Multi-agent orchestration and evidence synthesis."),
        ("Other", "GRAY", "Cross-cutting governance or uncategorized work."),
    ]
    wp_field["options"] = [{"name": name, "color": color, "description": desc} for name, color, desc in desired]

    upsert_item_group(cfg, 17, {"Status": "Blocked", "Priority": "P0", "Work Package": "WP-08", "Item Type": "Work Package", "Target Release": "0.1.0", "Blocked": "Yes", "Human Review": "Pending", "Outcome summary": "Close the already implemented DDDA 0.1.0 platform foundation and PR8 remediation/release evidence without new feature scope."})
    upsert_item_group(cfg, 20, {"Priority": "P1", "Work Package": "WP-11", "Item Type": "Work Package", "Target Release": "TBD", "Outcome summary": "EventStorming methodology, executable workshop runtime, governed Miro round-trip and package-first acceptance independent of multi-agent runtime."})
    upsert_item_group(cfg, 60, {"Status": "Backlog", "Priority": "P2", "Work Package": "WP-12", "Item Type": "Work Package", "Target Release": "TBD", "Blocked": "Yes", "Human Review": "Not required", "Outcome summary": "Generic Miro Platform Lab/CI/HVR/Example/Project lifecycle, rebinding and explicit profile credentials."})
    upsert_item_group(cfg, 61, {"Status": "Backlog", "Priority": "P3", "Work Package": "WP-13", "Item Type": "Work Package", "Target Release": "TBD", "Blocked": "Yes", "Human Review": "Not required", "Outcome summary": "Bounded multi-agent capability contracts, fan-out/fan-in, human checkpoints, recovery and package-first acceptance."})
    upsert_item_group(cfg, 45, {"Work Package": "Other", "Item Type": "Change Request", "Target Release": "TBD"})
    for n in [53, 54, 55, 56, 57]:
        upsert_item_group(cfg, n, {"Work Package": "WP-12", "Item Type": "Change Request", "Target Release": "TBD"})
    for n in [36, 37, 38, 39, 40, 41]:
        upsert_item_group(cfg, n, {"Work Package": "WP-13", "Item Type": "Change Request", "Target Release": "TBD"})
    upsert_item_group(cfg, 62, {"Status": "Backlog", "Work Package": "WP-11", "Item Type": "Change Request", "Target Release": "TBD", "Blocked": "Yes", "Human Review": "Pending", "Outcome summary": "Package-first EventStorming E2E acceptance without mandatory multi-agent runtime."})

    cfg["implementation_order"] = [
        {"rank": 1, "work_package": "WP-08", "issue": 17, "priority": "P0", "note": "finish current PR8 closure"},
        {"rank": 2, "work_package": "WP-11", "issue": 20, "priority": "P1", "note": "EventStorming methodology/runtime after stable PR8 baseline"},
        {"rank": 3, "work_package": "WP-12", "issue": 60, "priority": "P2", "note": "Miro platform lifecycle; may overlap WP-11 after stable Miro baseline"},
        {"rank": 4, "work_package": "WP-13", "issue": 61, "priority": "P3", "note": "multi-agent orchestration as independent later stream"},
    ]
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_policy():
    p = Path("config/governance/backlog-policy.yaml")
    text = p.read_text(encoding="utf-8-sig")
    text = text.replace("values: [WP-08, WP-09, WP-10, WP-11, Other]", "values: [WP-08, WP-09, WP-10, WP-11, WP-12, WP-13, Other]")

    mapping = """native_sub_issue_mapping:
  WP-08:
    parent_issue: 17
    children: [9, 10, 11, 12, 13, 14, 15]
    release_0_1_0_children: [9, 10, 11, 12, 13, 14, 15]
    future_children: []
  WP-09:
    parent_issue: 18
    children: [21, 22, 23, 24, 25, 50, 26, 51]
  WP-10:
    parent_issue: 19
    children: [27, 28, 29, 30, 31, 32, 33]
  WP-11:
    parent_issue: 20
    children: [34, 52, 35, 47, 48, 46, 62]
  WP-12:
    parent_issue: 60
    children: [53, 54, 55, 56, 57]
  WP-13:
    parent_issue: 61
    children: [36, 37, 38, 39, 40, 41]
  Other:
    unparented_items: [16, 42, 43, 44, 45, 49]

"""
    text, count = re.subn(r"native_sub_issue_mapping:\n.*?\ndependency_edges:\n", mapping + "dependency_edges:\n", text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"native_sub_issue_mapping replacement count={count}")

    edges = """dependency_edges:
  WP-08:
    - blocking: 13
      blocked: 14
      rationale: human-only gate semantics precede final steering-board acceptance
    - blocking: 14
      blocked: 12
      rationale: board redesign precedes final online Miro evidence acceptance
    - blocking: 12
      blocked: 11
    - blocking: 11
      blocked: 10
    - blocking: 10
      blocked: 9
  WP-09:
    - blocking: 21
      blocked: 23
    - blocking: 22
      blocked: 23
    - blocking: 22
      blocked: 24
    - blocking: 23
      blocked: 24
    - blocking: 21
      blocked: 25
    - blocking: 24
      blocked: 25
    - blocking: 25
      blocked: 50
    - blocking: 50
      blocked: 26
    - blocking: 26
      blocked: 51
  WP-10:
    - blocking: 27
      blocked: 31
    - blocking: 27
      blocked: 28
    - blocking: 31
      blocked: 28
    - blocking: 27
      blocked: 29
    - blocking: 31
      blocked: 29
    - blocking: 27
      blocked: 30
    - blocking: 31
      blocked: 30
    - blocking: 27
      blocked: 32
    - blocking: 31
      blocked: 32
    - blocking: 28
      blocked: 33
    - blocking: 29
      blocked: 33
    - blocking: 30
      blocked: 33
    - blocking: 31
      blocked: 33
    - blocking: 32
      blocked: 33
  WP-11:
    - blocking: 34
      blocked: 35
    - blocking: 52
      blocked: 35
    - blocking: 27
      blocked: 47
    - blocking: 31
      blocked: 47
    - blocking: 32
      blocked: 47
    - blocking: 34
      blocked: 47
    - blocking: 35
      blocked: 47
    - blocking: 34
      blocked: 62
    - blocking: 35
      blocked: 62
    - blocking: 47
      blocked: 62
    - blocking: 48
      blocked: 62
    - blocking: 52
      blocked: 62
    - blocking: 47
      blocked: 46
    - blocking: 62
      blocked: 46
    - blocking: 48
      blocked: 46
    - blocking: 52
      blocked: 46
  WP-12:
    - blocking: 53
      blocked: 57
    - blocking: 54
      blocked: 57
    - blocking: 55
      blocked: 57
  WP-13:
    - blocking: 36
      blocked: 37
    - blocking: 37
      blocked: 38
    - blocking: 36
      blocked: 39
    - blocking: 37
      blocked: 39
    - blocking: 38
      blocked: 39
    - blocking: 37
      blocked: 40
    - blocking: 38
      blocked: 40
    - blocking: 39
      blocked: 40
    - blocking: 36
      blocked: 41
    - blocking: 37
      blocked: 41
    - blocking: 38
      blocked: 41
    - blocking: 39
      blocked: 41
    - blocking: 40
      blocked: 41
  Other:
    - blocking: 16
      blocked: 49
    - blocking: 46
      blocked: 49
    - blocking: 48
      blocked: 49
    - blocking: 53
      blocked: 49

"""
    text, count = re.subn(r"dependency_edges:\n.*?\nbaseline_compatibility:\n", edges + "baseline_compatibility:\n", text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"dependency_edges replacement count={count}")

    text = text.replace("owner: WP-11-36", "owner: WP-13-36")
    text = text.replace("eventstorming_extension_owner: WP-11-35", "platform_environment_owner: WP-12\n      eventstorming_extension_owner: WP-11-35")
    text = text.replace("excluded_future_items: [45]", "excluded_future_items: [45, 53, 54, 55, 56, 57]")

    if "implementation_order:" not in text:
        marker = "priority_semantics:\n  P0: release_safety_or_data_integrity_blocker\n  P1: highest_active_product_priority\n  P2: important_planned_increment\n  P3: long_term_or_opportunistic\n"
        addition = marker + "\nimplementation_order:\n  - {rank: 1, work_package: WP-08, issue: 17, priority: P0}\n  - {rank: 2, work_package: WP-11, issue: 20, priority: P1}\n  - {rank: 3, work_package: WP-12, issue: 60, priority: P2, note: may_overlap_WP11_after_stable_miro_baseline}\n  - {rank: 4, work_package: WP-13, issue: 61, priority: P3}\n"
        if marker not in text:
            raise RuntimeError("priority_semantics marker missing")
        text = text.replace(marker, addition)

    wpblock = """work_packages:
  WP-08:
    title: DDDA 0.1.0 platform foundation and PR8 closure
    state: active_blocked
    target_release: 0.1.0
    outcome_summary: Close the already implemented PR8 foundation without new feature scope.
  WP-09:
    title: Strategy, portfolio and program lifecycle
    state: backlog
    target_release: TBD
    outcome_summary: Strategy, Wardley, portfolio, traceability, roadmap, benefits and P0-P10 governance.
  WP-10:
    title: Enterprise ingestion
    state: backlog
    target_release: TBD
    outcome_summary: Secure auditable ingestion with normalized evidence, Markdown materialization, YAML registration and provenance.
  WP-11:
    title: EventStorming methodology and workshop runtime
    state: backlog
    target_release: TBD
    outcome_summary: EventStorming facilitation, executable sessions, Miro round-trip, evidence integration and package-first acceptance.
  WP-12:
    title: Miro platform environments and lifecycle
    state: backlog
    target_release: TBD
    outcome_summary: Platform Lab, CI/HVR/Example/Project board lifecycle, environment rebinding and profile credential isolation.
  WP-13:
    title: Multi-agent orchestration and evidence synthesis
    state: backlog
    target_release: TBD
    outcome_summary: Bounded capabilities, fan-out/fan-in, human checkpoints, recovery and package-first multi-agent acceptance.
"""
    text, count = re.subn(r"work_packages:\n.*\Z", wpblock, text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"work_packages replacement count={count}")
    p.write_text(text, encoding="utf-8")


ROADMAP_README = """# DDDA platform product roadmap

## Purpose

Versioned long-term product roadmap. GitHub Issues remain authoritative for detailed requirements; GitHub Project is authoritative for operational priority/order; Milestones define release scope, not approval.

## Work Packages

| Order | Priority | WP | Outcome | State | Target |
|---:|---|---|---|---|---|
| 1 | P0 | WP-08 | DDDA 0.1.0 platform foundation & PR8 closure | active / blocked | 0.1.0 |
| 2 | P1 | WP-11 | EventStorming methodology & workshop runtime | backlog | TBD |
| 3 | P2 | WP-12 | Miro platform environments & lifecycle | backlog | TBD |
| 4 | P3 | WP-13 | Multi-agent orchestration & evidence synthesis | backlog | TBD |
| — | existing project priority | WP-09 | Strategy, portfolio & program lifecycle | backlog | TBD |
| — | existing project priority | WP-10 | Enterprise ingestion | backlog | TBD |

The numbered order above is the recommended default sequence requested for the newly restructured streams. WP-12 may overlap WP-11 after the relevant PR8 Miro baseline is stable. This ordering is represented by Project `Priority`; it is not an artificial native blocked-by chain between sibling Work Packages.

## Capability boundaries

```text
WP-08  close current PR8 foundation only

WP-10 registered evidence ───────┬────→ WP-11 EventStorming
                                └────→ WP-13 multi-agent

PR8 generic Miro baseline ───────────→ WP-12 Miro platform lifecycle
                                      └→ WP-11/#35 reuses generic boundary
```

WP-11 does not require WP-13 for its base workshop flow. WP-13 may later provide optional analytical hypotheses/candidates to WP-11.

## Scope rules

- Parent/sub-issue = capability ownership, not release scope.
- Milestone = release scope, not release approval.
- Project Priority = operational implementation order.
- Human Review PASS / HRDR / GO-NO-GO remain explicit human decisions.
- No new feature scope is added to PR #8 through WP-08.

## Detail

- [WP-08 — DDDA 0.1.0 platform foundation & PR8 closure](work-packages/WP-08-platform-lifecycle-and-steering.md)
- [WP-09 — Strategy, portfolio & program lifecycle](work-packages/WP-09-strategy-portfolio-program-lifecycle.md)
- [WP-10 — Enterprise ingestion](work-packages/WP-10-enterprise-ingestion.md)
- [WP-11 — EventStorming methodology & workshop runtime](work-packages/WP-11-eventstorming-methodology-workshop-runtime.md)
- [WP-12 — Miro platform environments & lifecycle](work-packages/WP-12-miro-platform-environments-lifecycle.md)
- [WP-13 — Multi-agent orchestration & evidence synthesis](work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md)
- [GitHub backlog index](backlog-index.md)
"""

BACKLOG_INDEX = """# Roadmap Work Package and GitHub backlog index

Parent/sub-issue represents capability ownership. Native `blocked by` represents direct completion dependency. Priority/order is authoritative in GitHub Project.

## Recommended implementation order

1. **WP-08 / #17 — P0**: close current PR #8 / DDDA 0.1.0 foundation.
2. **WP-11 / #20 — P1**: EventStorming methodology & workshop runtime.
3. **WP-12 / #60 — P2**: Miro platform environments & lifecycle; may overlap WP-11 after stable PR8 Miro baseline.
4. **WP-13 / #61 — P3**: multi-agent orchestration & evidence synthesis.

## WP-08 — #17

Children: #9–#15 only. PR #8 remains the implementation under closure. No new feature scope.

#45 is now cross-cutting `Work Package: Other`.

## WP-09 — #18

Children: #21, #22, #23, #24, #25, #50, #26, #51.

## WP-10 — #19

Children: #27–#33.

## WP-11 — #20 EventStorming

Children: #34, #52, #35, #47, #48, #46, #62.

Dependency model:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46
```

## WP-12 — #60 Miro platform environments

Children: #53, #54, #55, #56, #57.

```text
#53 → #57
#54 → #57
#55 → #57
```

## WP-13 — #61 Multi-agent

Children: #36, #37, #38, #39, #40, #41.

```text
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#36 + #37 + #38 + #39 + #40 → #41
```

## Cross-cutting

- #16 — GitHub-native backlog governance;
- #45 — GitHub Pages Artifact Registry dashboard (`Other`);
- #49 — role-based documentation IA (`Other`), blocked by #16, #46, #48 and #53.

## Boundary invariant

WP-11 base EventStorming does not have a mandatory dependency on WP-13. WP-13 output can be an optional analytical input only.
"""

WP08_ROADMAP = """# WP-08 — DDDA 0.1.0 platform foundation & PR8 closure

Parent: #17. Target: 0.1.0. Priority: P0.

WP-08 is intentionally narrowed to closing the already implemented PR #8 foundation. Children are #9–#15 only.

Critical path: `#13 DONE → #14 → #12 → deterministic PASS → frozen SHA → final HVR → promotion dry-run → #9 HRDR → explicit release decision`.

Moved future work: #53–#57 to WP-12/#60; #45 to Other; multi-agent is WP-13/#61.

No new feature scope may be added to PR #8 through this WP.
"""

WP11_ROADMAP = """# WP-11 — EventStorming methodology & workshop runtime

Parent: #20. Target: TBD. Priority: P1.

Children: #34, #52, #35, #47, #48, #46, #62.

Ownership: #48 WHEN/WHY; #52 HOW; #34 session model; #35 Miro realization; #47 composition; #62 E2E acceptance; #46 first-user explanation.

Dependency model:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46
```

WP-13 is not a mandatory prerequisite for the base EventStorming flow.
"""

WP12_ROADMAP = """# WP-12 — Miro platform environments & lifecycle

Parent: #60. Target: TBD. Priority: P2.

Children: #53–#57.

Owns persistent Platform Lab/reference adoption, Example Project, Project X credential UX, corporate rebinding and explicit profile credential lifecycle. Reuses PR8 generic Miro runtime; WP-11/#35 adds only EventStorming-specific semantics.

Default order: `#53 → #54 + #55 → #56 when prerequisites exist → #57 after #53/#54/#55`.

May overlap WP-11 once the relevant PR8 Miro baseline is stable.
"""

WP13_ROADMAP = """# WP-13 — Multi-agent orchestration & evidence synthesis

Parent: #61. Target: TBD. Priority: P3.

Children: #36–#41.

Owns versioned capabilities, bounded fan-out, fan-in/alternatives/conflicts, human checkpoints, recovery/observability and package-first multi-agent acceptance.

Default order: `#36 → #37 → #38 → #39 → #40 → #41`.

EventStorming is an optional integration consumer, not a core prerequisite.
"""


def update_roadmaps():
    Path("docs/roadmap/README.md").write_text(ROADMAP_README, encoding="utf-8")
    Path("docs/roadmap/backlog-index.md").write_text(BACKLOG_INDEX, encoding="utf-8")
    Path("docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md").write_text(WP08_ROADMAP, encoding="utf-8")
    Path("docs/roadmap/work-packages/WP-11-eventstorming-methodology-workshop-runtime.md").write_text(WP11_ROADMAP, encoding="utf-8")
    Path("docs/roadmap/work-packages/WP-12-miro-platform-environments-lifecycle.md").write_text(WP12_ROADMAP, encoding="utf-8")
    Path("docs/roadmap/work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md").write_text(WP13_ROADMAP, encoding="utf-8")
    Path("docs/roadmap/work-packages/WP-11-eventstorming-multi-agent-orchestration.md").write_text("# Superseded roadmap path\n\nWP-11 was split on 2026-08-13. Canonical EventStorming roadmap: [WP-11 EventStorming methodology & workshop runtime](WP-11-eventstorming-methodology-workshop-runtime.md). Multi-agent orchestration moved to [WP-13](WP-13-multi-agent-orchestration-evidence-synthesis.md).\n", encoding="utf-8")


Q_FIELDS = """
query($login:String!,$number:Int!){user(login:$login){projectV2(number:$number){id number title fields(first:100){nodes{
  __typename
  ... on ProjectV2FieldCommon{id name dataType}
  ... on ProjectV2SingleSelectField{options{id name color description}}
}}}}}
"""

Q_ITEMS = """
query($login:String!,$number:Int!,$after:String){user(login:$login){projectV2(number:$number){items(first:100,after:$after){pageInfo{hasNextPage endCursor}nodes{id content{__typename ... on Issue{id number}} fieldValues(first:50){nodes{__typename ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2FieldCommon{name}}} ... on ProjectV2ItemFieldTextValue{text field{... on ProjectV2FieldCommon{name}}}}}}}}}}
"""


def resolve_project():
    projects = gh("project", "list", "--owner", OWNER, "--limit", "100", "--format", "json", json_out=True)
    match = next(x for x in projects["projects"] if x["title"] == PROJECT_TITLE and not x.get("closed"))
    number = int(match["number"])
    p = gql(Q_FIELDS, {"login": OWNER, "number": number})["data"]["user"]["projectV2"]
    fields = {x.get("name"): x for x in p["fields"]["nodes"] if x.get("name")}
    return number, p["id"], fields


def project_items(number):
    out, after = [], None
    while True:
        b = gql(Q_ITEMS, {"login": OWNER, "number": number, "after": after})["data"]["user"]["projectV2"]["items"]
        out.extend(b["nodes"])
        if not b["pageInfo"]["hasNextPage"]:
            return out
        after = b["pageInfo"]["endCursor"]


def project_values(item):
    out = {}
    for n in item.get("fieldValues", {}).get("nodes", []):
        f = (n.get("field") or {}).get("name")
        if f:
            out[f] = n.get("name") if n.get("name") is not None else n.get("text")
    return out


def ensure_wp_options(fields):
    field = fields["Work Package"]
    existing = field.get("options", [])
    wanted = {
        "WP-08": ("BLUE", "DDDA 0.1.0 platform foundation and PR8 closure."),
        "WP-09": ("PURPLE", "Strategy, portfolio and program lifecycle."),
        "WP-10": ("GREEN", "Enterprise ingestion."),
        "WP-11": ("ORANGE", "EventStorming methodology and workshop runtime."),
        "WP-12": ("BLUE", "Miro platform environments and lifecycle."),
        "WP-13": ("PURPLE", "Multi-agent orchestration and evidence synthesis."),
        "Other": ("GRAY", "Cross-cutting governance or uncategorized work."),
    }
    current_by_name = {o["name"]: o for o in existing}
    options = []
    for name in ["WP-08", "WP-09", "WP-10", "WP-11", "WP-12", "WP-13", "Other"]:
        color, desc = wanted[name]
        row = {"name": name, "color": color, "description": desc}
        if name in current_by_name:
            row["id"] = current_by_name[name]["id"]
        options.append(row)
    if [x["name"] for x in existing] == [x["name"] for x in options] and all(name in current_by_name for name in wanted):
        return
    q = """mutation($fieldId:ID!,$options:[ProjectV2SingleSelectFieldOptionInput!]){updateProjectV2Field(input:{fieldId:$fieldId,singleSelectOptions:$options}){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}"""
    gql(q, {"fieldId": field["id"], "options": options})


def add_project_item(project_id, n):
    d = issue(n)
    q = """mutation($projectId:ID!,$contentId:ID!){addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){item{id}}}"""
    return gql(q, {"projectId": project_id, "contentId": d["node_id"]})["data"]["addProjectV2ItemById"]["item"]["id"]


def set_select(project_id, field, item_id, value):
    opt = next((o for o in field.get("options", []) if o["name"] == value), None)
    if not opt:
        raise RuntimeError(f"Missing option {field['name']}={value}")
    q = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{singleSelectOptionId:$optionId}}){projectV2Item{id}}}"""
    gql(q, {"projectId": project_id, "itemId": item_id, "fieldId": field["id"], "optionId": opt["id"]})


def set_text(project_id, field, item_id, value):
    q = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$text:String!){updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,fieldId:$fieldId,value:{text:$text}}){projectV2Item{id}}}"""
    gql(q, {"projectId": project_id, "itemId": item_id, "fieldId": field["id"], "text": value})


def set_project_planning():
    number, project_id, fields = resolve_project()
    ensure_wp_options(fields)
    number, project_id, fields = resolve_project()
    items = {int(x["content"]["number"]): x for x in project_items(number) if (x.get("content") or {}).get("__typename") == "Issue"}

    desired = {
        17: {"Work Package": "WP-08", "Item Type": "Work Package", "Priority": "P0", "Dependency": "1/4 — finish current PR8 closure first"},
        20: {"Work Package": "WP-11", "Item Type": "Work Package", "Priority": "P1", "Dependency": "2/4 — EventStorming after stable PR8 baseline"},
        60: {"Work Package": "WP-12", "Item Type": "Work Package", "Priority": "P2", "Status": "Backlog", "Blocked": "Yes", "Target Release": "TBD", "Dependency": "3/4 — may overlap WP-11 after stable PR8 Miro baseline"},
        61: {"Work Package": "WP-13", "Item Type": "Work Package", "Priority": "P3", "Status": "Backlog", "Blocked": "Yes", "Target Release": "TBD", "Dependency": "4/4 — independent later multi-agent stream"},
        45: {"Work Package": "Other", "Item Type": "Change Request", "Target Release": "TBD"},
        62: {"Work Package": "WP-11", "Item Type": "Change Request", "Status": "Backlog", "Blocked": "Yes", "Human Review": "Pending", "Target Release": "TBD"},
    }
    for n in [53, 54, 55, 56, 57]:
        desired[n] = {"Work Package": "WP-12", "Item Type": "Change Request", "Target Release": "TBD"}
    for n in [36, 37, 38, 39, 40, 41]:
        desired[n] = {"Work Package": "WP-13", "Item Type": "Change Request", "Target Release": "TBD"}

    for n, vals in desired.items():
        item = items.get(n)
        if not item:
            item_id = add_project_item(project_id, n)
            current = {}
        else:
            item_id = item["id"]
            current = project_values(item)
        for field_name, value in vals.items():
            if current.get(field_name) == value:
                continue
            field = fields[field_name]
            if field.get("dataType") == "SINGLE_SELECT":
                set_select(project_id, field, item_id, value)
            else:
                set_text(project_id, field, item_id, value)


def validate_target_graph():
    target = {
        35: {34, 52}, 37: {36}, 38: {37}, 39: {36, 37, 38}, 40: {37, 38, 39},
        41: {36, 37, 38, 39, 40}, 47: {27, 31, 32, 34, 35}, 62: {34, 35, 47, 48, 52},
        46: {47, 62, 48, 52}, 49: {16, 46, 48, 53}, 57: {53, 54, 55},
    }
    nodes = set(target)
    for x in target.values(): nodes |= x
    visiting, done = set(), set()
    def dfs(n):
        if n in done: return
        if n in visiting: raise RuntimeError(f"Dependency cycle at #{n}")
        visiting.add(n)
        for b in target.get(n, set()): dfs(b)
        visiting.remove(n); done.add(n)
    for n in nodes: dfs(n)


def main():
    for n in [17, 20, 36, 37, 38, 39, 40, 41, 45, 46, 47, 49, 53, 54, 55, 56, 57, 60, 61, 62]:
        issue(n)
    validate_target_graph()
    edit_issue_contracts()
    edit_hierarchy_and_dependencies()
    update_config()
    update_policy()
    update_roadmaps()
    set_project_planning()
    Path(".reports/wp-scope-split").mkdir(parents=True, exist_ok=True)
    Path(".reports/wp-scope-split/summary.json").write_text(json.dumps({
        "wp08": {"issue": 17, "priority": "P0", "children": [9,10,11,12,13,14,15]},
        "wp11": {"issue": 20, "priority": "P1", "children": [34,52,35,47,48,46,62]},
        "wp12": {"issue": 60, "priority": "P2", "children": [53,54,55,56,57]},
        "wp13": {"issue": 61, "priority": "P3", "children": [36,37,38,39,40,41]},
        "other": [16,45,49],
        "eventstorming_e2e": 62,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WP_SCOPE_SPLIT_APPLIED")


if __name__ == "__main__":
    main()
