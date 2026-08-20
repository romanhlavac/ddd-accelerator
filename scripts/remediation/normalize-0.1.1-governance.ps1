[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $RepositoryRoot

$expectedBase = '1f66880c30b7bc1814d21200ef6fcc5b08cadfba'
$baseParent = (& git rev-parse HEAD^).Trim()
if ($baseParent -ne $expectedBase) {
    throw "Normalization staging commit is not based on expected main $expectedBase; parent=$baseParent"
}
if ((& git status --porcelain)) {
    throw 'Working tree must be clean before remediation.'
}

$py = @'
import json
import re
from pathlib import Path

ROOT = Path('.')
CFG = ROOT / 'config/governance/github-bootstrap.json'
POLICY = ROOT / 'config/governance/backlog-policy.yaml'
CORE = ROOT / 'scripts/platform/Reconcile-DDDAProjectBacklogCore.py'
INIT = ROOT / 'scripts/platform/Initialize-DDDAGitHubGovernance.ps1'
WORKFLOW = ROOT / '.github/workflows/reconcile-ddda-project-backlog.yml'
TESTS = ROOT / 'runtime/platform/tests/test_project_backlog_delivery_governance.py'
CONSISTENCY = ROOT / 'docs/governance/wp-backlog-consistency.md'
SKILL = ROOT / 'knowledge/ddda-platform-development-skill.md'
ROADMAP = ROOT / 'docs/roadmap/work-packages/WP-08-platform-lifecycle-and-steering.md'
CHANGELOG = ROOT / 'CHANGELOG.md'
RELEASE_PLANNER = ROOT / 'scripts/platform/Reconcile-DDDAReleasePlanning.py'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected one preimage, found {count}')
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Versioned Project / Milestone contract
# ---------------------------------------------------------------------------
cfg = json.loads(CFG.read_text(encoding='utf-8-sig'))
managed = {9, 12, 14, 15, 17, 44, 65, 66, 67, 68, 69, 70, 73, 75, 85}
new_groups = []
for group in cfg.get('item_groups', []):
    nums = [int(n) for n in group.get('numbers', []) if int(n) not in managed]
    if nums:
        clone = dict(group)
        clone['numbers'] = nums
        new_groups.append(clone)

new_groups.extend([
    {'kind':'issue','numbers':[9,12],'metadata':{
        'Status':'Done','Work Package':'WP-08','Item Type':'Change Request','Target Release':'0.1.1','Blocked':'No','Human Review':'PASS'
    }},
    {'kind':'issue','numbers':[14],'metadata':{
        'Status':'Done','Work Package':'WP-08','Item Type':'Change Request','Target Release':'0.1.0','Blocked':'No','Human Review':'Pending'
    }},
    {'kind':'issue','numbers':[15],'metadata':{
        'Status':'Cancelled','Work Package':'WP-08','Item Type':'Change Request','Target Release':'TBD','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Historical PR8 pre-release execution plan; superseded after successful DDDA 0.1.0 release.'
    }},
    {'kind':'issue','numbers':[17],'metadata':{
        'Status':'In progress','Priority':'P0','Work Package':'WP-08','Item Type':'Work Package','Target Release':'0.1.0','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Released DDDA 0.1.0 foundation with finite 0.1.1 stabilization handoff coordinated by #75.'
    }},
    {'kind':'issue','numbers':[44],'metadata':{
        'Status':'Ready','Priority':'P0','Work Package':'Other','Item Type':'Defect','Target Release':'TBD','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Pre-release prerequisite: prove effective main protection/ruleset and required-check enforcement before DDDA 0.1.1 release readiness.'
    }},
    {'kind':'issue','numbers':[65,66,69,73,85],'metadata':{
        'Status':'Backlog','Work Package':'Other','Item Type':'Change Request','Target Release':'TBD','Blocked':'No','Human Review':'Pending'
    }},
    {'kind':'issue','numbers':[67,68],'metadata':{
        'Status':'Done','Work Package':'Other','Item Type':'Defect','Target Release':'0.1.1','Blocked':'No','Human Review':'PASS'
    }},
    {'kind':'issue','numbers':[70],'metadata':{
        'Status':'Done','Work Package':'Other','Item Type':'Change Request','Target Release':'0.1.1','Blocked':'No','Human Review':'PASS'
    }},
    {'kind':'issue','numbers':[75],'metadata':{
        'Status':'In progress','Priority':'P0','Work Package':'Other','Item Type':'Enabler','Target Release':'0.1.1','Blocked':'No','Human Review':'Not required',
        'Outcome summary':'Coordinate approved DDDA 0.1.1 stabilization scope, governance normalization, release prerequisites and release-candidate gates.'
    }},
])
cfg['item_groups'] = new_groups
cfg['milestones'] = [
    {
        'title':'DDDA 0.1.0',
        'state':'closed',
        'description':'Released DDDA 0.1.0 foundation. Historical milestone membership is release scope evidence, not approval.',
        'issues':[10,11,13,14],
        'pulls':[8],
    },
    {
        'title':'DDDA 0.1.1',
        'state':'open',
        'description':'Approved stabilization release scope from #75. Milestone membership is release scope, not release approval.',
        'issues':[9,12,67,68,70],
        'pulls':[],
    },
]
# Keep the legacy singular shape normalized for older bootstrap consumers.
cfg['milestone'] = dict(cfg['milestones'][0])
CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# ---------------------------------------------------------------------------
# backlog-policy.yaml alignment
# ---------------------------------------------------------------------------
policy = POLICY.read_text(encoding='utf-8-sig')
policy = replace_once(
    policy,
    '  dependency_priority_and_business_value_are_distinct: true\n',
    '  dependency_priority_and_business_value_are_distinct: true\n  governance_projection_is_same_transaction: true\n  project_readback_zero_required_before_ready_done_or_merge_recommendation: true\n',
    'backlog policy transaction principles',
)
policy = replace_once(
    policy,
    '  Other:\n    unparented_items: [16, 42, 43, 44, 45, 49]\n',
    '  Other:\n    unparented_items: [16, 42, 44, 45, 49, 65, 66, 67, 68, 69, 70, 73, 75, 85]\n',
    'Other planning mapping',
)
old_milestones = """milestones:\n  naming: 'DDDA <semver>'\n  initial:\n    - name: DDDA 0.1.0\n      issues: [9, 10, 11, 12, 13, 14, 15]\n      pulls: [8]\n      excluded_future_items: [45, 53, 54, 55, 56, 57]\n  parent_work_packages_counted_in_release_progress: false\n  unplanned_work_packages_target_release: TBD\n  membership_is_release_scope_not_approval: true\n"""
new_milestones = """milestones:\n  naming: 'DDDA <semver>'\n  initial:\n    - name: DDDA 0.1.0\n      state: closed\n      issues: [10, 11, 13, 14]\n      pulls: [8]\n      excluded_future_items: [9, 12, 45, 53, 54, 55, 56, 57, 65, 66, 67, 68, 69, 70, 73, 75, 85]\n    - name: DDDA 0.1.1\n      state: open\n      issues: [9, 12, 67, 68, 70]\n      pulls: []\n      pre_release_prerequisites: [44]\n      explicitly_deferred_items: [65, 66, 69, 73, 85]\n  parent_work_packages_counted_in_release_progress: false\n  unplanned_work_packages_target_release: TBD\n  membership_is_release_scope_not_approval: true\n"""
policy = replace_once(policy, old_milestones, new_milestones, 'milestone policy')
policy = replace_once(
    policy,
    '  WP-08:\n    title: DDDA 0.1.0 platform foundation and PR8 closure\n    state: active_blocked\n    target_release: 0.1.0\n    outcome_summary: Close the already implemented PR8 foundation without new feature scope.\n',
    '  WP-08:\n    title: DDDA 0.1.0 platform foundation and PR8 closure\n    state: released_with_stabilization_tail\n    target_release: 0.1.0\n    outcome_summary: Preserve released DDDA 0.1.0 foundation truth and hand off only the finite approved 0.1.1 stabilization tail through #75.\n',
    'WP-08 state',
)
POLICY.write_text(policy, encoding='utf-8')

# ---------------------------------------------------------------------------
# Generic Project reconciler: configured planning item types + target correction
# ---------------------------------------------------------------------------
core = CORE.read_text(encoding='utf-8-sig')
core = replace_once(
    core,
    '''    expected = dict(hierarchy)\n    for n, meta in item_meta.items():\n        if meta.get("Item Type") == "Change Request" and meta.get("Work Package") == "Other":\n            expected[n] = "Other"\n''',
    '''    expected = dict(hierarchy)\n    planning_types = {"Change Request", "Defect", "Risk", "Enabler", "GAP"}\n    for n, meta in item_meta.items():\n        if meta.get("Item Type") in planning_types and meta.get("Work Package") == "Other":\n            expected[n] = "Other"\n''',
    'load_contract planning item types',
)
core = replace_once(
    core,
    '        item_type = "Work Package" if n in wp_parent.values() else "Change Request"\n',
    '        item_type = "Work Package" if n in wp_parent.values() else item_meta.get(n, {}).get("Item Type", "Change Request")\n',
    'reconcile item type',
)
core = replace_once(
    core,
    '        if item_type == "Change Request":\n',
    '        if item_type != "Work Package":\n',
    'terminal planning status applies to all planning item types',
)
core = replace_once(
    core,
    '''        milestone = (data.get("milestone") or {}).get("title")\n        meta = item_meta.get(n, {})\n        target = milestone or meta.get("Target Release")\n        if target and not current.get("Target Release"):\n            set_text(project_id, fields, item_id, "Target Release", target)\n            repairs.append({"issue": n, "action": "SET_TARGET_RELEASE", "value": target})\n''',
    '''        milestone = (data.get("milestone") or {}).get("title")\n        meta = item_meta.get(n, {})\n        target = milestone or meta.get("Target Release")\n        if target and current.get("Target Release") != target:\n            set_text(project_id, fields, item_id, "Target Release", target)\n            repairs.append({"issue": n, "action": "SET_TARGET_RELEASE", "value": target})\n''',
    'target release correction',
)
core = replace_once(
    core,
    '''        else:\n            v = values(item)\n            if v.get("Work Package") != wp:\n                rowprobs.append("WORK_PACKAGE_MISMATCH")\n            if v.get("Item Type") != "Change Request":\n                rowprobs.append("ITEM_TYPE_MISMATCH")\n        rows.append({"issue": n, "wp": wp, "parent": parent, "fields": v, "result": "PASS" if not rowprobs else "+".join(rowprobs)})\n''',
    '''        else:\n            v = values(item)\n            if v.get("Work Package") != wp:\n                rowprobs.append("WORK_PACKAGE_MISMATCH")\n            _, _, item_meta, _, _ = load_contract()\n            wanted_type = item_meta.get(n, {}).get("Item Type", "Change Request")\n            if v.get("Item Type") != wanted_type:\n                rowprobs.append("ITEM_TYPE_MISMATCH")\n            data = issue(n)\n            milestone = (data.get("milestone") or {}).get("title")\n            wanted_target = milestone or item_meta.get(n, {}).get("Target Release")\n            if wanted_target and v.get("Target Release") != wanted_target:\n                rowprobs.append("TARGET_RELEASE_MISMATCH")\n        rows.append({"issue": n, "wp": wp, "parent": parent, "fields": v, "result": "PASS" if not rowprobs else "+".join(rowprobs)})\n''',
    'verify planning type and target',
)
CORE.write_text(core, encoding='utf-8')

# ---------------------------------------------------------------------------
# Canonical release-scope milestone reconciler
# ---------------------------------------------------------------------------
release_planner = r'''import argparse
import json
import subprocess
from pathlib import Path

REPO = "romanhlavac/ddd-accelerator"
CFG_PATH = Path("config/governance/github-bootstrap.json")
REPORT_PATH = Path(".reports/cr-delivery-audit-v6/release-planning.json")


def cmd(*args, json_out=False, stdin=None):
    p = subprocess.run(list(args), input=stdin, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)} failed ({p.returncode}): {p.stderr or p.stdout}")
    if json_out:
        return json.loads(p.stdout) if p.stdout.strip() else None
    return p.stdout.strip()


def gh(*args, json_out=False):
    return cmd("gh", *args, json_out=json_out)


def gh_json(method, path, body):
    return cmd(
        "gh", "api", "--method", method, path, "--input", "-",
        json_out=True, stdin=json.dumps(body),
    )


def load_specs():
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
    specs = list(cfg.get("milestones") or [])
    if not specs:
        legacy = cfg.get("milestone")
        if legacy:
            specs = [legacy]
    if not specs:
        raise RuntimeError("No milestone contract configured")
    titles = [x["title"] for x in specs]
    if len(titles) != len(set(titles)):
        raise RuntimeError("Duplicate configured milestone title")
    assigned = {}
    for spec in specs:
        for raw in list(spec.get("issues") or []) + list(spec.get("pulls") or []):
            n = int(raw)
            if n in assigned:
                raise RuntimeError(f"#{n} appears in multiple configured milestones: {assigned[n]} and {spec['title']}")
            assigned[n] = spec["title"]
    return specs


def list_milestones():
    return gh("api", f"repos/{REPO}/milestones?state=all&per_page=100", json_out=True) or []


def milestone_items(number):
    pages = gh("api", "--paginate", "--slurp", f"repos/{REPO}/issues?state=all&milestone={number}&per_page=100", json_out=True) or []
    rows = []
    for page in pages:
        rows.extend(page)
    return {int(x["number"]): x for x in rows}


def desired_numbers(spec):
    return {int(x) for x in list(spec.get("issues") or []) + list(spec.get("pulls") or [])}


def ensure_milestone(spec, repairs):
    matches = [x for x in list_milestones() if x.get("title") == spec["title"]]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous milestone title: {spec['title']}")
    wanted_state = spec.get("state") or "open"
    wanted_description = spec.get("description") or ""
    if not matches:
        created = gh_json("POST", f"repos/{REPO}/milestones", {
            "title": spec["title"], "state": wanted_state, "description": wanted_description,
        })
        repairs.append({"milestone": spec["title"], "action": "CREATE_MILESTONE", "number": int(created["number"])})
        return created
    current = matches[0]
    patch = {}
    if current.get("state") != wanted_state:
        patch["state"] = wanted_state
    if (current.get("description") or "") != wanted_description:
        patch["description"] = wanted_description
    if patch:
        current = gh_json("PATCH", f"repos/{REPO}/milestones/{current['number']}", patch)
        repairs.append({"milestone": spec["title"], "action": "ALIGN_MILESTONE", "value": patch})
    return current


def reconcile(specs):
    repairs = []
    resolved = []
    for spec in specs:
        milestone = ensure_milestone(spec, repairs)
        number = int(milestone["number"])
        wanted = desired_numbers(spec)
        current = milestone_items(number)
        for extra in sorted(set(current) - wanted):
            gh_json("PATCH", f"repos/{REPO}/issues/{extra}", {"milestone": None})
            repairs.append({"issue": extra, "action": "REMOVE_FROM_MILESTONE", "milestone": spec["title"]})
        for missing in sorted(wanted - set(current)):
            gh_json("PATCH", f"repos/{REPO}/issues/{missing}", {"milestone": number})
            repairs.append({"issue": missing, "action": "ASSIGN_MILESTONE", "milestone": spec["title"]})
        resolved.append({"title": spec["title"], "number": number})
    return repairs, resolved


def verify(specs):
    problems = []
    rows = []
    live = list_milestones()
    by_title = {}
    for item in live:
        by_title.setdefault(item.get("title"), []).append(item)
    for spec in specs:
        matches = by_title.get(spec["title"], [])
        if len(matches) != 1:
            problems.append({"milestone": spec["title"], "result": "MILESTONE_IDENTITY_MISMATCH", "count": len(matches)})
            continue
        milestone = matches[0]
        wanted = desired_numbers(spec)
        actual = set(milestone_items(int(milestone["number"])))
        row = {
            "title": spec["title"],
            "number": int(milestone["number"]),
            "state": milestone.get("state"),
            "desired": sorted(wanted),
            "actual": sorted(actual),
            "result": "PASS",
        }
        if actual != wanted:
            row["result"] = "MILESTONE_MEMBERSHIP_MISMATCH"
            problems.append(dict(row))
        elif milestone.get("state") != (spec.get("state") or "open"):
            row["result"] = "MILESTONE_STATE_MISMATCH"
            problems.append(dict(row))
        elif (milestone.get("description") or "") != (spec.get("description") or ""):
            row["result"] = "MILESTONE_DESCRIPTION_MISMATCH"
            problems.append(dict(row))
        rows.append(row)
    return rows, problems


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reconcile", "verify"), default="verify")
    args = parser.parse_args(argv)
    specs = load_specs()
    repairs = []
    if args.mode == "reconcile":
        repairs, _ = reconcile(specs)
    rows, problems = verify(specs)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_sha = cmd("git", "rev-parse", "HEAD")
    report = {
        "schema_version": 1,
        "mode": args.mode,
        "source_sha": source_sha,
        "repair_count": len(repairs),
        "remaining_count": len(problems),
        "repairs": repairs,
        "milestones": rows,
        "problems": problems,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if problems:
        raise RuntimeError("Release planning mismatches: " + json.dumps(problems, ensure_ascii=False))
    print(json.dumps({"mode": args.mode, "repairs": len(repairs), "remaining": 0, "milestones": len(rows)}))


if __name__ == "__main__":
    main()
'''
RELEASE_PLANNER.write_text(release_planner, encoding='utf-8')

# ---------------------------------------------------------------------------
# Canonical workflow: milestones + Project are one privileged transaction
# ---------------------------------------------------------------------------
workflow = WORKFLOW.read_text(encoding='utf-8-sig')
workflow = replace_once(
    workflow,
    '          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklog.py\n          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklogCore.py\n          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py\n',
    '          python -m py_compile scripts/platform/Reconcile-DDDAReleasePlanning.py\n          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklog.py\n          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklogCore.py\n          python -m py_compile scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py\n',
    'workflow compile release planning',
)
workflow = replace_once(
    workflow,
    '          python scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py --mode reconcile\n          python scripts/platform/Reconcile-DDDAProjectBacklog.py\n          python scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py --mode verify\n',
    '          python scripts/platform/Reconcile-DDDAReleasePlanning.py --mode reconcile\n          python scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py --mode reconcile\n          python scripts/platform/Reconcile-DDDAProjectBacklog.py\n          python scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py --mode verify\n          python scripts/platform/Reconcile-DDDAReleasePlanning.py --mode verify\n',
    'workflow reconcile release planning',
)
workflow = replace_once(
    workflow,
    '            scripts/platform/Reconcile-DDDAProjectBacklog.py \\\n            scripts/platform/Reconcile-DDDAProjectBacklogCore.py \\\n',
    '            scripts/platform/Reconcile-DDDAReleasePlanning.py \\\n            scripts/platform/Reconcile-DDDAProjectBacklog.py \\\n            scripts/platform/Reconcile-DDDAProjectBacklogCore.py \\\n',
    'workflow diff guard release planning',
)
workflow = replace_once(
    workflow,
    "          presentation = json.loads(Path('.reports/cr-delivery-audit-v6/presentation.json').read_text(encoding='utf-8'))\n          assert audit['source_sha'] == os.environ['GITHUB_SHA']\n          assert audit['remaining_count'] == 0\n          assert presentation['remaining_count'] == 0\n",
    "          presentation = json.loads(Path('.reports/cr-delivery-audit-v6/presentation.json').read_text(encoding='utf-8'))\n          release_planning = json.loads(Path('.reports/cr-delivery-audit-v6/release-planning.json').read_text(encoding='utf-8'))\n          assert audit['source_sha'] == os.environ['GITHUB_SHA']\n          assert release_planning['source_sha'] == os.environ['GITHUB_SHA']\n          assert audit['remaining_count'] == 0\n          assert presentation['remaining_count'] == 0\n          assert release_planning['remaining_count'] == 0\n",
    'workflow release planning audit assertion',
)
WORKFLOW.write_text(workflow, encoding='utf-8')

# ---------------------------------------------------------------------------
# Older bootstrap admin path: consume plural milestones when present
# ---------------------------------------------------------------------------
init = INIT.read_text(encoding='utf-8-sig')
pattern = re.compile(r'function Ensure-Milestone \{.*?\n\}\n\nfunction Write-Report \{', re.S)
replacement = r'''function Ensure-Milestone {
    Write-Section "Milestones"

    $configured = @()
    if ($Config.PSObject.Properties.Name -contains "milestones" -and @($Config.milestones).Count -gt 0) {
        $configured = @($Config.milestones)
    }
    elseif ($Config.PSObject.Properties.Name -contains "milestone" -and $Config.milestone) {
        $configured = @($Config.milestone)
    }
    else {
        throw "No milestone contract is configured."
    }

    foreach ($spec in $configured) {
        $milestones = Invoke-GhJson -Arguments @(
            "api",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: $($Config.api_version)",
            "repos/$($Config.repository)/milestones?state=all&per_page=100"
        )
        $matches = @($milestones | Where-Object { $_.title -eq $spec.title })
        if ($matches.Count -gt 1) { throw "Ambiguous milestone title '$($spec.title)'." }
        $milestone = $matches | Select-Object -First 1
        if (-not $milestone) {
            Write-Action "Create Milestone '$($spec.title)'"
            if ($Apply) {
                Invoke-GhJsonInput -Endpoint "repos/$($Config.repository)/milestones" -Body @{
                    title = $spec.title
                    state = if ($spec.state) { $spec.state } else { "open" }
                    description = $spec.description
                } | Out-Null
                $Changes.Add("Created Milestone '$($spec.title)'.")
            }
        }
        Write-Action "Reconcile exact membership for Milestone '$($spec.title)' through canonical release-planning reconciler"
    }

    $ManualSteps.Add("Use Reconcile-DDDAReleasePlanning.py / the privileged backlog reconciliation workflow for exact milestone membership and stale-membership removal; do not treat this initializer as release approval.")
}

function Write-Report {'''
init, count = pattern.subn(replacement, init, count=1)
if count != 1:
    raise RuntimeError(f'initializer milestone function: expected one match, found {count}')
INIT.write_text(init, encoding='utf-8')

# ---------------------------------------------------------------------------
# Governance transaction contract: make the existing methodology impossible to
# misread as a two-step/optional Project update.
# ---------------------------------------------------------------------------
consistency = CONSISTENCY.read_text(encoding='utf-8-sig')
anchor = 'Post-change výsledek musí být:\n\n```text\nremaining_mismatches = 0\n```\n\n'
transaction = '''Post-change výsledek musí být:\n\n```text\nremaining_mismatches = 0\n```\n\n## Governance transakce: Issue/PR + Project projection je jeden celek\n\nVytvoření nebo změna governed CR/Defect/Enabler, jeho statusu, WP/dependency vztahu, implementation PR nebo primary `Implements/Closes` vazby **není dokončená GitHub governance operace**, dokud není v témže orchestration flow materializována odpovídající Project planning/delivery projection a repository-wide post-read-back neskončí `remaining_mismatches = 0`.\n\nConnector/API omezení není důvod přeskočit projekci. Pokud canonical privileged reconciler nelze spustit, operace zůstává explicitně `BLOCKED / GOVERNANCE_INCOMPLETE`; nesmí být označena `Ready`, `Done`, governance `PASS` ani doporučena k merge. Člověk nemá ručně hlídat, zda byl Project aktualizován.\n\n'''
consistency = replace_once(consistency, anchor, transaction, 'transactional consistency wording')
CONSISTENCY.write_text(consistency, encoding='utf-8')

skill = SKILL.read_text(encoding='utf-8-sig')
marker = '\n## Backlog / Project transactional completion\n'
if marker not in skill:
    skill += '''\n## Backlog / Project transactional completion\n\nPro DDDA platform backlog/delivery governance je GitHub Issue/PR mutation a její `DDDA Platform Backlog & Delivery` projection jedna fail-closed transakce. CR/Defect/Enabler/PR creation, state/relationship change nebo implementation authority change není `Ready`/`Done`/governance `PASS`, dokud canonical Project/Milestone reconciliation a repository-wide read-back nevrátí `remaining_mismatches = 0`. Nedostupná Project mutation surface je blocker k dokončení governance transakce, ne důvod projekci odložit nebo ji přenést na člověka k ruční kontrole.\n'''
SKILL.write_text(skill, encoding='utf-8')

# ---------------------------------------------------------------------------
# Roadmap current truth
# ---------------------------------------------------------------------------
ROADMAP.write_text('''# WP-08 — DDDA 0.1.0 platform foundation & finite stabilization handoff\n\nParent: #17. Historical foundation target: 0.1.0. Stabilization coordinator: #75. Priority: P0.\n\nDDDA 0.1.0 was released on 2026-08-17 from PR #8 and remains immutable historical baseline evidence. WP-08 is not a catch-all for future platform evolution.\n\nApproved DDDA 0.1.1 stabilization implementation scope is finite: `#9 + #12 + #67 + #68 + #70`; all five implementation items are integrated/terminal. #44 is a pre-release prerequisite, not additional product capability.\n\nCurrent critical path: `governance normalization + Project/Milestone read-back = 0 mismatches → #44 main protection evidence → release/0.1.1 candidate → exact-SHA validation → HRDR → Release Scope Gate → promotion dry-run → explicit Human Release Decision → separate release authorization → canonical release validation → v0.1.1`.\n\nDeferred/outside 0.1.1: #65, #66, #69, #73, #85 and PR #43 unless a later explicit human scope decision changes that boundary.\n\nMoved future work remains: #53–#57 to WP-12/#60; #45 to Other; multi-agent evolution to WP-13/#61.\n\nNo release, promotion or tag is authorized by completion of the stabilization implementation scope.\n''', encoding='utf-8')

# ---------------------------------------------------------------------------
# Regression / contract tests
# ---------------------------------------------------------------------------
tests = TESTS.read_text(encoding='utf-8-sig')
append = r'''


def test_0_1_1_governance_normalization_contract():
    cfg = json.loads((ROOT / "config/governance/github-bootstrap.json").read_text(encoding="utf-8-sig"))
    specs = {x["title"]: x for x in cfg["milestones"]}
    assert set(specs) == {"DDDA 0.1.0", "DDDA 0.1.1"}
    assert specs["DDDA 0.1.0"]["state"] == "closed"
    assert specs["DDDA 0.1.0"]["issues"] == [10, 11, 13, 14]
    assert specs["DDDA 0.1.0"]["pulls"] == [8]
    assert specs["DDDA 0.1.1"]["state"] == "open"
    assert specs["DDDA 0.1.1"]["issues"] == [9, 12, 67, 68, 70]
    assert specs["DDDA 0.1.1"]["pulls"] == []

    meta = {}
    for group in cfg["item_groups"]:
        if group.get("kind") != "issue":
            continue
        for number in group.get("numbers", []):
            meta[int(number)] = group.get("metadata", {})
    assert meta[44]["Item Type"] == "Defect"
    assert meta[44]["Status"] == "Ready"
    assert meta[67]["Item Type"] == "Defect" and meta[67]["Target Release"] == "0.1.1"
    assert meta[68]["Item Type"] == "Defect" and meta[68]["Target Release"] == "0.1.1"
    assert meta[70]["Item Type"] == "Change Request" and meta[70]["Target Release"] == "0.1.1"
    assert meta[75]["Item Type"] == "Enabler"
    assert meta[85]["Work Package"] == "Other"
    assert meta[85]["Target Release"] == "TBD"
    assert meta[85]["Status"] == "Backlog"


def test_governance_projection_is_transactional_and_fail_closed():
    consistency = (ROOT / "docs/governance/wp-backlog-consistency.md").read_text(encoding="utf-8")
    skill = (ROOT / "knowledge/ddda-platform-development-skill.md").read_text(encoding="utf-8-sig")
    assert "Issue/PR + Project projection je jeden celek" in consistency
    assert "BLOCKED / GOVERNANCE_INCOMPLETE" in consistency
    assert "remaining_mismatches = 0" in consistency
    assert "Backlog / Project transactional completion" in skill
    assert "remaining_mismatches = 0" in skill


def test_reconciler_supports_non_cr_planning_items_and_target_correction():
    core = (ROOT / "scripts/platform/Reconcile-DDDAProjectBacklogCore.py").read_text(encoding="utf-8-sig")
    release = (ROOT / "scripts/platform/Reconcile-DDDAReleasePlanning.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/reconcile-ddda-project-backlog.yml").read_text(encoding="utf-8-sig")
    assert '{"Change Request", "Defect", "Risk", "Enabler", "GAP"}' in core
    assert 'current.get("Target Release") != target' in core
    assert 'TARGET_RELEASE_MISMATCH' in core
    assert 'REMOVE_FROM_MILESTONE' in release
    assert 'MILESTONE_MEMBERSHIP_MISMATCH' in release
    assert 'Reconcile-DDDAReleasePlanning.py --mode reconcile' in workflow
    assert 'release_planning[\'remaining_count\'] == 0' in workflow
'''
if 'def test_0_1_1_governance_normalization_contract()' not in tests:
    tests += append
TESTS.write_text(tests, encoding='utf-8')

# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------
changelog = CHANGELOG.read_text(encoding='utf-8-sig')
changed_anchor = '### Changed\n\n'
entry = '- GitHub-native backlog governance nyní považuje Issue/PR mutation, Project planning/delivery projection a release Milestone projection za jednu fail-closed transakci; DDDA 0.1.0/0.1.1 scope je versioned a canonical reconciler opravuje Project/Milestone drift před Ready/merge/release doporučením.\n'
if entry not in changelog:
    changelog = replace_once(changelog, changed_anchor, changed_anchor + entry, 'changelog changed section')
CHANGELOG.write_text(changelog, encoding='utf-8')

# basic local structural checks
json.loads(CFG.read_text(encoding='utf-8'))
for py in [CORE, RELEASE_PLANNER]:
    compile(py.read_text(encoding='utf-8-sig'), str(py), 'exec')
'@

& python -c $py
if ($LASTEXITCODE -ne 0) { throw "Python normalization failed with exit $LASTEXITCODE" }

& python -m json.tool config/governance/github-bootstrap.json *> $null
if ($LASTEXITCODE -ne 0) { throw 'github-bootstrap.json validation failed.' }

& python -m py_compile scripts/platform/Reconcile-DDDAReleasePlanning.py scripts/platform/Reconcile-DDDAProjectBacklog.py scripts/platform/Reconcile-DDDAProjectBacklogCore.py scripts/platform/Reconcile-DDDAProjectBacklogPresentation.py
if ($LASTEXITCODE -ne 0) { throw 'Python compile validation failed.' }

& python -m pytest -q runtime/platform/tests/test_project_backlog_delivery_governance.py runtime/platform/tests/test_project_backlog_presentation_governance.py
if ($LASTEXITCODE -ne 0) { throw 'Governance regression tests failed.' }

$scriptPath = Join-Path $RepositoryRoot 'scripts/remediation/normalize-0.1.1-governance.ps1'
Remove-Item -LiteralPath $scriptPath -Force

& git add -A
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
$staged = (& git diff --cached --name-only)
if (-not $staged) { throw 'Remediation produced no staged changes.' }

& git commit -m 'fix(governance): normalize 0.1.1 backlog and projection contract'
if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }

if ((& git status --porcelain)) {
    throw 'Working tree is not clean after remediation commit.'
}

Write-Host 'DDDA 0.1.1 governance normalization remediation: PASS'
Write-Host "Commit: $((& git rev-parse HEAD).Trim())"
